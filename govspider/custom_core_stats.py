"""
Extension for collecting core stats like items scraped and start/finish times
"""
# -*- coding: utf-8 -*-
# 重写信号收集器
import time
from scrapy.extensions.corestats import CoreStats


class MyCoreStats(CoreStats):

    def spider_opened(self, spider):
        """爬虫开始运行"""
        self.start_time = time.time()
        start_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time))  # 转化格式
        self.stats.set_value('爬虫开始时间: ', start_time_str, spider=spider)

    def spider_closed(self, spider, reason):
        """爬虫结束运行"""
        # 爬虫结束时间
        finish_time = time.time()
        # 转化时间格式
        finish_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(finish_time))
        # 计算爬虫运行总耗时
        elapsed_time = finish_time - self.start_time
        m, s = divmod(elapsed_time, 60)
        h, m = divmod(m, 60)
        self.stats.set_value('爬虫结束时间: ', finish_time_str, spider=spider)
        self.stats.set_value('爬虫运行总耗时: ', '%d时:%02d分:%02d秒' % (h, m, s), spider=spider)
        self.stats.set_value('爬虫结束原因: ', reason, spider=spider)
