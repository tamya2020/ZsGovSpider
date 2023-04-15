# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter


class GovspiderPipeline:
    def process_item(self, item, spider):
        print(item)
        return item


from redis import Redis


class IncrementproPipeline(object):
    conn = None

    def open_spider(self, spider):
        self.conn = Redis(host='127.0.0.1', port=6379)

    def process_item(self, item, spider):
        dic = {
            'name': item['name'],
            'kind': item['kind']
        }
        print(dic)
        self.conn.lpush('movieData', dic)
        return item
