# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class GovspiderItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    title = scrapy.Field()  # 手机名称
    date = scrapy.Field()  # 参考价格
    author = scrapy.Field()  # 手机爬取链接
    # content = scrapy.Field()
    # img_url = scrapy.Field() # 上传到图片服务器
