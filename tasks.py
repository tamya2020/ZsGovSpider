# @Time    : 2023/4/17 0:20
# @Author  : tamya2020
# @File    : tasks.py
# @Description : 

from celery import Celery
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


app = Celery('tasks', broker='pyamqp://guest@localhost//')


@app.task
def run_spider():
    process = CrawlerProcess(get_project_settings())
    process.crawl(incgov)
    process.start()
