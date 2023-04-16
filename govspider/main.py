# @Time    : 2023/3/30 22:01
# @Author  : tamya2020
# @File    : main.py
# @Description : 

from scrapy import cmdline

if __name__ == '__main__':
    cmdline.execute('scrapy crawl incgov'.split())
    #  scrapy crawl meishi -a deltafetch_reset=1
