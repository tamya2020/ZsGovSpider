# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import random
import time

from scrapy import signals
from scrapy.http import HtmlResponse

# useful for handling different item types with a single interface
from itemadapter import is_item, ItemAdapter
from selenium.common import TimeoutException
import random
import time
# import redom_proxy  # 随机获取一个代理的方法
from twisted.internet.error import TimeoutError, DNSLookupError, \
    ConnectionRefusedError, ConnectionDone, ConnectError, \
    ConnectionLost, TCPTimedOutError
from scrapy.core.downloader.handlers.http11 import TunnelError
from twisted.internet import defer
from twisted.web.client import ResponseFailed


class GovspiderSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class GovspiderDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class SeleniumMiddleware(object):

    def process_request(self, request, spider):
        if request.meta.get("is_selenium") == 1:
            try:
                spider.browser.get(request.url)
                time.sleep(2)
                body = spider.browser.page_source
                return HtmlResponse(spider.browser.current_url,
                                    body=body,
                                    encoding='utf-8',
                                    request=request)
            except TimeoutException:
                return HtmlResponse(url=request.url, status=500, request=request)


class UaMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # 随机添加请求头  choice意思是从列表中随机选取一个元素
        ua = random.choice(spider.settings['USER_AGENT_LIST'])
        request.headers['User-Agent'] = ua

    def process_response(self, request, response, spider):
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


def redom_proxy():
    """
    随机获取一个代理的方法
    :return:
    """
    return


class ProxiesMiddleware:
    ALL_EXCEPTIONS = (defer.TimeoutError, TimeoutError, DNSLookupError,
                      ConnectionRefusedError, ConnectionDone, ConnectError,
                      ConnectionLost, TCPTimedOutError, ResponseFailed,
                      IOError, TunnelError)

    def __init__(self):
        self.proxy = redom_proxy()
        self.count = 0
        self.information = self.information_func()

    def information_func(self):
        """设定过期时间 逻辑 当前时间+7000秒+随机一个50到200秒，因为我用的redis存储的代理，
             有代理失效逻辑，同时大量代理一起失效会存在问题"""
        return time.time() + 7000 + random.randint(50, 200)

    def agentExecutable(self, name):
        if time.time() > self.information:
            self.proxy = redom_proxy(spiderhost=name)
            self.information = self.information_func()

    def process_request(self, request, spider):
        """
        source:判定是哪个网站，进而获取这个网站的专用代理
        """
        source = request.meta.get("source", "xxx")
        if self.count % 10000 == 0 and self.count != 0:
            """另一种换代理逻辑，没有走到过这"""
            spider.logger.info("[一万个请求啦换代理了]")
            self.proxy = redom_proxy(spiderhost=source)
        self.count += 1
        # 下面是用来判断是否到时间该换代理
        self.agentExecutable(source)
        spider.logger.info("[request url]   {}".format(request.url))
        spider.logger.info("[proxy]   {}".format(self.proxy))
        request.meta["proxy"] = self.proxy

    def process_response(self, request, response, spider):
        if len(response.text) < 3000 or response.status in [403, 400, 405, 301, 302]:
            source = request.meta.get("source", "xxx")
            spider.logger.info("[此代理报错]   {}".format(self.proxy))
            new_proxy = redom_proxy(spiderhost=source)
            self.proxy = new_proxy
            spider.logger.info("[更的的新代理为]   {}".format(self.proxy))
            new_request = request.copy()
            new_request_l = new_request.replace(url=request.url)
            return new_request_l
        return response

    def process_exception(self, request, exception, spider):
        # 捕获几乎所有的异常
        if isinstance(exception, self.ALL_EXCEPTIONS):
            # 在日志中打印异常类型
            source = request.meta.get("source", "xxx")
            spider.logger.info("[Got exception]   {}".format(exception))
            spider.logger.info("[需要更换代理重试]   {}".format(self.proxy))
            new_proxy = redom_proxy(spiderhost=source)
            self.proxy = new_proxy
            spider.logger.info("[更换后的代理为]   {}".format(self.proxy))
            new_request = request.copy()
            new_request_l = new_request.replace(url=request.url)
            return new_request_l
        # 打印出未捕获到的异常
        spider.logger.info("[not contained exception]   {}".format(exception))
