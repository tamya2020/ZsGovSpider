# @Time    : 2023/4/15 21:49
# @Author  : tamya2020
# @File    : custom_retry.py
# @Description :
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message


class LocalRetryMiddleware(RetryMiddleware):

    # 当遇到以下Exception时进行重试
    # EXCEPTIONS_TO_RETRY = (defer.TimeoutError, TimeoutError, DNSLookupError, ConnectionRefusedError,
    # ConnectionDone, ConnectError, ConnectionLost, TCPTimedOutError, ResponseFailed, IOError, TunnelError)
    #
    # def __init__(self, settings):
    #     '''
    #     这里涉及到了settings.py文件中的几个量
    #     RETRY_ENABLED: 用于开启中间件，默认为TRUE
    #     RETRY_TIMES: 重试次数, 默认为2
    #     RETRY_HTTP_CODES: 遇到哪些返回状态码需要重试, 一个列表，默认为[500, 503, 504, 400, 408]
    #     RETRY_PRIORITY_ADJUST：调整相对于原始请求的重试请求优先级，默认为-1
    #     '''
    #     if not settings.getbool('RETRY_ENABLED'):
    #         raise NotConfigured
    #     self.max_retry_times = settings.getint('RETRY_TIMES')
    #     self.retry_http_codes = set(int(x) for x in settings.getlist('RETRY_HTTP_CODES'))
    #     self.priority_adjust = settings.getint('RETRY_PRIORITY_ADJUST')

    def process_response(self, request, response, spider):
        # 在之前构造的request中可以加入meta信息dont_retry来决定是否重试
        if request.meta.get('dont_retry', False):
            return response

        # 检查状态码是否在列表中，在的话就调用_retry方法进行重试
        if response.status in self.retry_http_codes:
            reason = response_status_message(response.status)
            # 在此处进行自己的操作，如删除不可用代理，打日志等
            # request.meta.get('proxy', False)
            # interval, redirect_url = get_meta_refresh(response)
            # # test for captcha page
            return self._retry(request, reason, spider) or response
        return response

    def process_exception(self, request, exception, spider):
        # 如果发生了Exception列表中的错误，进行重试
        if isinstance(exception, self.EXCEPTIONS_TO_RETRY) \
                and not request.meta.get('dont_retry', False):
            # 在此处进行自己的操作，如删除不可用代理，打日志等
            return self._retry(request, exception, spider)
