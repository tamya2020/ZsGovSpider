## scrapy 爬虫案例
### scrapy 架构图
![](https://cdn.jsdelivr.net/gh/tamya2020/Free-Picture/202301/jiagou.png)

### 自定义Downloader Middleware中间件
我们可以通过项目的DOWNLOADER_MIDDLEWARES变量设置来添加自己定义的Downloader Middleware。
其中Downloader Middleware有三个核心方法：
- process_request(request,spider)
- process_response(request,response，spider)
- process_exception(request,exception，spider)

① process_request(request,spider)
- 当每个request通过下载中间件时，该方法被调用，这里有一个要求，该方法必须返回以下三种中的任意一种：None,返回一个Response对象、返回一个Request对象或raise IgnoreRequest。三种返回值的作用是不同的。
- None:Scrapy将继续处理该request，执行其他的中间件的相应方法，直到合适的下载器处理函数(download handler)被调用,该request被执行(其response被下载)。
- Response对象：Scrapy将不会调用任何其他的process_request()或process_exception() 方法，或相应地下载函数；其将返回该response。已安装的中间件的 process_response() 方法则会在每个response返回时被调用。
- Request对象：Scrapy则停止调用 process_request方法并重新调度返回的request。当新返回的request被执行后， 相应地中间件链将会根据下载的response被调用。
- raise一个IgnoreRequest异常：则安装的下载中间件的 process_exception() 方法会被调用。如果没有任何一个方法处理该异常， 则request的errback(Request.errback)方法会被调用。如果没有代码处理抛出的异常，则该异常被忽略且不记录。

② process_response(request, response, spider)
- process_response的返回值也是有三种：response对象，request对象，或者raise一个IgnoreRequest异常
- 如果其返回一个Response(可以与传入的response相同，也可以是全新的对象)， 该response会被在链中的其他中间件的 process_response() 方法处理。
- 如果其返回一个 Request 对象，则中间件链停止， 返回的request会被重新调度下载。处理类似于 process_request() 返回request所做的那样。
- 如果其抛出一个 IgnoreRequest 异常，则调用request的errback(Request.errback)。
- 如果没有代码处理抛出的异常，则该异常被忽略且不记录(不同于其他异常那样)。

这里我们写一个简单的例子还是上面的项目，我们在中间件中继续添加如下代码：
```
def process_response(self, request, response, spider):
    response.status = 201
    return response
```
③ process_exception(request, exception, spider)
- 当下载处理器(download handler)或 process_request() (下载中间件)抛出异常(包括 IgnoreRequest 异常)时，Scrapy调用 process_exception()。
- process_exception() 也是返回三者中的一个: 返回 None 、 一个 Response 对象、或者一个 Request 对象。
- 如果其返回 None ，Scrapy将会继续处理该异常，接着调用已安装的其他中间件的 process_exception() 方法，直到所有中间件都被调用完毕，则调用默认的异常处理。
- 如果其返回一个 Response 对象，则已安装的中间件链的 process_response() 方法被调用。Scrapy将不会调用任何其他中间件的 process_exception() 方法。


