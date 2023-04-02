from copy import deepcopy

import scrapy
from scrapy import Selector
from scrapy.spidermiddlewares.httperror import HttpError
from selenium import webdriver
from gne import GeneralNewsExtractor

from govspider.items import GovspiderItem


class GovSpider(scrapy.Spider):
    name = 'gov'
    allowed_domains = ['www.zhoushan.gov.cn']

    # start_urls = []

    # 构造函数，初始化chrome webdirver
    def __init__(self, *arg, **args):
        options = webdriver.ChromeOptions()
        # 无头浏览器
        # options.add_argument('--headless')
        # 不使用沙箱
        options.add_argument('--no-sandbox')
        options.add_argument('--start-maximized')
        self.browser = webdriver.Chrome(options=options, executable_path='chromedriver.exe')
        self.extractor = GeneralNewsExtractor()
        super(GovSpider, self).__init__()

    def start_requests(self):
        for i in range(1, 3):
            start_url = 'https://www.zhoushan.gov.cn/col/col1276171/index.html?pageNum={}&uid=7284066'.format(i)
            yield scrapy.Request(start_url, callback=self.parse, errback=self.errback,
                                 meta={'is_selenium': 1})

    def parse(self, response):
        article_lists = response.xpath('//table[@class="lm_tabe"]//tr')
        article_lists_len = len(article_lists)
        if article_lists_len == 0:
            self.crawler.engine.close_spider(self, "列表页失效")
        item = GovspiderItem()
        for article_item in article_lists:
            item['title'] = article_item.xpath("./td[1]/a/text()").extract_first().strip()
            item['date'] = article_item.xpath("./td[2]/text()").extract_first().strip()
            detail_url = response.urljoin(article_item.xpath("./td[1]/a/@href").extract_first())
            request = scrapy.Request(detail_url, callback=self.parse_detail, meta={'item': deepcopy(item)})
            yield request

    def parse_detail(self, response: scrapy.http.Response):
        item = response.meta['item']
        result = self.extractor.extract(html=response.text)
        item["author"] = result.get("author")
        yield item

    # 爬虫关闭时，会自动调用closed函数
    def closed(self, reason):
        self.browser.quit()

    def errback(self, failure):
        self.logger.error(repr(failure))
        if failure.check(HttpError):
            response = failure.value.response
            self.logger.error('HttpError on %s', response.url)
