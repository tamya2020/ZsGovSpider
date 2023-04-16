from __future__ import absolute_import
import math
import hashlib
import copy
from pybloom_live.utils import range_fn, is_string_io, running_python_3
from struct import unpack, pack, calcsize


MAX_PER_SLICE_SIZE = 4294967295
try:
    import bitarray
except ImportError:
    raise ImportError('pybloom_live requires bitarray >= 0.3.4')


def make_hashfuncs(num_slices, num_bits):
    if num_bits >= (1 << 31):
        fmt_code, chunk_size = 'Q', 8
    elif num_bits >= (1 << 15):
        fmt_code, chunk_size = 'I', 4
    else:
        fmt_code, chunk_size = 'H', 2
    total_hash_bits = 8 * num_slices * chunk_size
    if total_hash_bits > 384:
        hashfn = hashlib.sha512
    elif total_hash_bits > 256:
        hashfn = hashlib.sha384
    elif total_hash_bits > 160:
        hashfn = hashlib.sha256
    elif total_hash_bits > 128:
        hashfn = hashlib.sha1
    else:
        hashfn = hashlib.md5

    fmt = fmt_code * (hashfn().digest_size // chunk_size)
    num_salts, extra = divmod(num_slices, len(fmt))
    if extra:
        num_salts += 1
    salts = tuple(hashfn(hashfn(pack('I', i)).digest()) for i in range_fn(0, num_salts))

    def _hash_maker(key):
        if running_python_3:
            if isinstance(key, str):
                key = key.encode('utf-8')
            else:
                key = str(key).encode('utf-8')
        else:
            if isinstance(key, unicode):
                key = key.encode('utf-8')
            else:
                key = str(key)
        i = 0
        for salt in salts:
            h = salt.copy()
            h.update(key)
            for uint in unpack(fmt, h.digest()):
                yield uint % num_bits
                i += 1
                if i >= num_slices:
                    return

    return _hash_maker, hashfn


class RedisBloomFilter:
    REDIS_BF_SLICE_KEY_FMT = "%s:bf:s:%s"
    REDIS_BF_META_HASH_KEY = "%s:bf:meta"
    REDIS_BF_HASH_FIELD_CONF = "conf"
    REDIS_BF_HASH_FIELD_COUNT = "count"
    REDIS_CNF_FMT = b'<dQQQ'

    def __init__(self, server, bfkeypreffix, capacity, error_rate=0.001):
        if not (0 < error_rate < 1):
            raise ValueError("Error_Rate must be between 0 and 1.")
        if not capacity > 0:
            raise ValueError("Capacity must be > 0")

        num_slices = int(math.ceil(math.log(1.0 / error_rate, 2)))

        bits_per_slice = int(math.ceil(
            (capacity * abs(math.log(error_rate))) /
            (num_slices * (math.log(2) ** 2))))

        if bits_per_slice > MAX_PER_SLICE_SIZE:
            raise ValueError("Capacity[%s] and error_rate[%s] make per slice size extended, MAX_PER_SLICE_SIZE is %s, now is %s" % (capacity, error_rate, MAX_PER_SLICE_SIZE, bits_per_slice))
        
        self._setup(error_rate, num_slices, bits_per_slice, capacity, server, bfkeypreffix)

    def _setup(self, error_rate, num_slices, bits_per_slice, capacity, server, bfkeypreffix):
        self.error_rate = error_rate
        self.num_slices = num_slices
        self.bits_per_slice = bits_per_slice
        self.capacity = capacity
        self.num_bits = num_slices * bits_per_slice
        self.make_hashes,self.hashfn = make_hashfuncs(self.num_slices, self.bits_per_slice)

        self.bfkeypreffix = bfkeypreffix
        self.server = server
        self.sliceKeys = tuple(self.REDIS_BF_SLICE_KEY_FMT % (self.bfkeypreffix, i) for i in range(num_slices))
        self.bfMetaKey = self.REDIS_BF_META_HASH_KEY % self.bfkeypreffix
        self._checkExists()    

    def _checkExists(self):
        existsCnf = self.server.hget(self.bfMetaKey, self.REDIS_BF_HASH_FIELD_CONF)
        if not existsCnf:
            self.server.hset(self.bfMetaKey, self.REDIS_BF_HASH_FIELD_CONF, pack(self.REDIS_CNF_FMT, self.error_rate, self.num_slices,
                     self.bits_per_slice, self.capacity))
            pipe = self.server.pipeline(transaction=True)
            for key in self.sliceKeys:
                pipe.delete(key)
            pipe.hset(self.bfMetaKey, self.REDIS_BF_HASH_FIELD_COUNT, 0)
            pipe.execute()
        else:
            error_rate, num_slices, bits_per_slice, capacity = unpack(self.REDIS_CNF_FMT, existsCnf)
            if self.error_rate != error_rate or self.num_slices != num_slices or self.bits_per_slice != bits_per_slice or self.capacity != capacity:
                raise ValueError("setup configure not match exists")

    def __contains__(self, key):
        """Tests a key's membership in this bloom filter.
        >>> b = RedisBloomFilter(server=server, bfkeypreffix="atest:bf", capacity=100000, error_rate=0.001)
        >>> b.add("hello")
        False
        >>> "hello" in b
        True
        """
        hashes = self.make_hashes(key)
        pipe = self.server.pipeline(transaction=False) 
        sliceIdx = 0
        for k in hashes:
            sliceKey = self.REDIS_BF_SLICE_KEY_FMT % (self.bfkeypreffix, sliceIdx)
            pipe.getbit(sliceKey, k)
            sliceIdx += 1
        getbits = pipe.execute()  
        for bit in getbits:
            if not bit:
                return False
        return True

    def __len__(self):
        """Return the number of keys stored by this bloom filter."""
        count = self.server.hget(self.bfMetaKey, self.REDIS_BF_HASH_FIELD_COUNT)
        if count:
            return int(count)
        return 0

    @property
    def count(self):
        return len(self)

    def add(self, key, skip_check=False):
        """ Adds a key to this bloom filter. If the key already exists in this
        filter it will return True. Otherwise False.
        >>> b = RedisBloomFilter(server=server, bfkeypreffix="atest:bf", capacity=100000, error_rate=0.001)
        >>> b.add("hello")
        False
        >>> b.add("hello")
        True
        >>> len(b)
        1
        """
        hashes = self.make_hashes(key)

        found_all_bits = True
        if len(self) >= self.capacity:
            raise IndexError("RedisBloomFilter is at capacity")
        # TODO, check and increase not async
        pipe = self.server.pipeline(transaction=False) 
        sliceIdx = 0
        for k in hashes:
            sliceKey = self.REDIS_BF_SLICE_KEY_FMT % (self.bfkeypreffix, sliceIdx)
            pipe.setbit(sliceKey, k, 1)
            sliceIdx += 1
        pipeResults = pipe.execute()
        if not skip_check:
            for pipeResult in pipeResults:
                if not pipeResult:
                    found_all_bits = False
                    break
        if skip_check:
            self.server.hincrby(self.bfMetaKey, self.REDIS_BF_HASH_FIELD_COUNT, 1)
            return False
        elif not found_all_bits:
            self.server.hincrby(self.bfMetaKey, self.REDIS_BF_HASH_FIELD_COUNT, 1)
            return False
        else:
            return True


    def clear(self):
        pipe = self.server.pipeline(transaction=True)
        pipe.delete(self.bfMetaKey)
        for key in self.sliceKeys:
            pipe.delete(key)
        pipe.execute()
        del self.sliceKeys[:]

    def copy(self):
        """Return a copy of this bloom filter.
        """
        raise NotImplementedError("RedisBloomFilter not support copy")

    def union(self, other):
        """ Calculates the union of the two underlying bitarrays and returns
        a new bloom filter object."""
        if self.capacity != other.capacity or self.error_rate != other.error_rate:
            raise ValueError("Unioning filters requires both filters to have \
both the same capacity and error rate")
        raise NotImplementedError("RedisBloomFilter not support union")

    def __or__(self, other):
        raise NotImplementedError("RedisBloomFilter not support or")

    def intersection(self, other):
        """ Calculates the intersection of the two underlying bitarrays and returns
        a new bloom filter object."""
        if self.capacity != other.capacity or self.error_rate != other.error_rate:
            raise ValueError("Intersecting filters requires both filters to \
have equal capacity and error rate")
        raise NotImplementedError("RedisBloomFilter not support intersection")

    def __and__(self, other):
        raise NotImplementedError("RedisBloomFilter not support and")

    def tofile(self, f):
        """Write the bloom filter to file object `f'. Underlying bits
        are written as machine values. This is much more space
        efficient than pickling the object."""
        raise NotImplementedError("RedisBloomFilter not support tofile")

    @classmethod
    def fromfile(cls, f, n=-1):
        """Read a bloom filter from file-object `f' serialized with
        ``BloomFilter.tofile''. If `n' > 0 read only so many bytes."""
        raise NotImplementedError("RedisBloomFilter not support fromfile")

    def __getstate__(self):
        d = self.__dict__.copy()
        del d['make_hashes']
        return d

    def __setstate__(self, d):
        self.__dict__.update(d)
        self.make_hashes = make_hashfuncs(self.num_slices, self.bits_per_slice)























