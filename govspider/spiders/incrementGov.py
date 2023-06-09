# @Time    : 2023/3/31 21:48
# @Author  : tamya2020
# @File    : incrementGov.py
# @Description : 

from copy import deepcopy

import scrapy
from redis import StrictRedis
from scrapy_redis_bloomfilter.bloomfilter import BloomFilter
from selenium import webdriver
from gne import GeneralNewsExtractor

from govspider.items import GovspiderItem


class GovSpider(scrapy.Spider):
    name = 'incgov'
    allowed_domains = ['www.zhoushan.gov.cn']
    custom_settings = {
        'ITEM_PIPELINES': {
            'govspider.pipelines.IncrementproPipeline': 300
        },
        # deltafetch是一个spider中间件，根据架构图，spider只有yield item到pipeline的时候才会触发，即yield item才能让deltafetch生效。
        'SPIDER_MIDDLEWARES': {
            'scrapy_deltafetch.DeltaFetch': 100
        },
        'DELTAFETCH_ENABLED': True
    }

    # 构造函数，初始化chrome webdirver
    def __init__(self, *arg, **args):
        options = webdriver.ChromeOptions()
        # 无头浏览器
        options.add_argument('--headless')
        # 不使用沙箱
        options.add_argument('--no-sandbox')
        self.browser = webdriver.Chrome(options=options, executable_path='chromedriver.exe')
        self.extractor = GeneralNewsExtractor()
        # 初始化bloomFilter
        conn = StrictRedis(host='localhost', port=6379)
        self.bf = BloomFilter(conn, 'govbf', 5, 6)
        super(GovSpider, self).__init__()

    def start_requests(self):
        start_url = 'https://www.zhoushan.gov.cn/col/col1276171/index.html?pageNum=1'
        yield scrapy.Request(start_url, callback=self.parse, meta={'is_selenium': 1})

    def parse(self, response):
        article_lists = response.xpath('//table[@class="lm_tabe"]//tr')
        article_lists_len = len(article_lists)
        if article_lists_len == 0:
            self.crawler.engine.close_spider(self, "列表页失效")
        item = GovspiderItem()
        for article_item in article_lists:
            detail_url = response.urljoin(article_item.xpath("./td[1]/a/@href").extract_first())
            if self.bf.exists(detail_url):
                print('该条数据已经爬取过了，不需要再次爬取了!!!')
                self.bf.insert(detail_url)
            else:
                print('该条数据没有爬取过，可以爬取......')
                item['title'] = article_item.xpath("./td[1]/a/text()").extract_first().strip()
                item['date'] = article_item.xpath("./td[2]/text()").extract_first().strip()
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
