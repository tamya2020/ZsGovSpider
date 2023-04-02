# @Time    : 2023/4/2 22:44
# @Author  : tamya2020
# @File    : custom_logstats.py
# @Description :
import logging

from twisted.internet import task

from scrapy.exceptions import NotConfigured
from scrapy import signals

logger = logging.getLogger(__name__)


class LogStats:
    """Log basic scraping stats periodically"""

    def __init__(self, stats, interval=60.0):
        self.stats = stats  # MemoryStatsCollector模块的实例对象
        self.interval = interval  # 时间间隔，默认60秒
        self.multiplier = 60.0 / self.interval  # 频率
        self.task = None

    @classmethod
    def from_crawler(cls, crawler):
        # 读取settings.py中默认配置，如果没有值，就抛出经过处理的异常，扩展会被禁用
        interval = crawler.settings.getfloat('LOGSTATS_INTERVAL')
        if not interval:
            raise NotConfigured
        # 创建当前对象,传递stats对象，默认时间间隔
        o = cls(crawler.stats, interval)
        # 当spider开始爬取时发送该信号。该信号一般用来分配spider的资源，不过其也能做任何事
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        # 当某个spider被关闭时，该信号被发送。该信号可以用来释放每个spider在 spider_opened 时占用的资源
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        return o

    def spider_opened(self, spider):
        """
        启动爬虫
        """
        self.pagesprev = 0  # pages计数器
        self.itemsprev = 0  # items计数器

        # 使用twisted.internet,task来做定时器循环
        self.task = task.LoopingCall(self.log, spider)
        self.task.start(self.interval)

    def log(self, spider):
        """
        统计抓取的items、pages数据量
        """
        items = self.stats.get_value('item_scraped_count', 0)
        pages = self.stats.get_value('response_received_count', 0)
        # 计算pages、items的每分钟数量
        irate = (items - self.itemsprev) * self.multiplier
        prate = (pages - self.pagesprev) * self.multiplier
        # 修改计数器的值
        self.pagesprev, self.itemsprev = pages, items

        # 日志输出信息
        msg = ("Crawled %(pages)d pages (at %(pagerate)d pages/min), "
               "scraped %(items)d items (at %(itemrate)d items/min)")
        log_args = {'pages': pages, 'pagerate': prate,
                    'items': items, 'itemrate': irate}
        logger.info(msg, log_args, extra={'spider': spider})

    def spider_closed(self, spider, reason):
        """关闭爬虫的操作"""
        if self.task and self.task.running:
            self.task.stop()
