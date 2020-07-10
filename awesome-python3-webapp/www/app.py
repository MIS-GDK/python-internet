__author__ = 'MIS_GDK'

'''
async web application.
'''

import logging
import asyncio
import os
import json
import time
from datetime import datetime
from aiohttp import web

logging.basicConfig(level=logging.INFO)

# 1、参数request，即为aiohttp.web.request实例，包含了所有浏览器发送过来的 HTTP 协议里面的信息，一般不用自己构造
# 2、返回值，aiohttp.web.response实例，由web.Response(body='')构造，继承自StreamResponse，功能为构造一个HTTP响应
# 3、类声明 class aiohttp.web.Response(*, status=200, headers=None, content_type=None, body=None, text=None)
# 4、HTTP 协议格式为： POST /PATH /1.1 /r/n Header1:Value  /r/n .. /r/n HenderN:Valule /r/n Body:Data
def index(request):
    return web.Response(body='<h1>Awesome</h1>')


async def init(loop):
    # 创建Web服务器，并将处理函数注册进其应用路径(Application.router)
    # 1、创建Web服务器实例app，也就是aiohttp.web.Application类的实例，该实例的作用是处理URL、HTTP协议
    #   1.2使用app时，首先要将URLs注册进router，再用aiohttp.RequestHandlerFactory 作为协议簇创建套接字 
    # 　1.3 aiohttp.RequestHandlerFactory 可以用 make_handle() 创建，用来处理 HTTP 协议，接下来将会看到
    app = web.Application(loop=loop)
    # 2.将处理函数注册到创建app.router中
    #   2.1 router，默认为UrlDispatcher实例，UrlDispatcher类中有方法add_route(method, path, handler, *, name=None, expect_handler=None)，
    #       该方法将处理函数（其参数名为handler）与对应的URL（HTTP方法method，URL路径path）绑定，浏览器敲击URL时返回处理函数的内容
    app.router.add_route('GET', '/', index)
    # 3、用协程创建监听服务，并使用aiohttp中的HTTP协议簇(protocol_factory)
    #   1.用协程创建监听服务，其中loop为传入函数的协程，调用其类方法创建一个监听服务，声明如下
    # 　　coroutine BaseEventLoop.create_server(protocol_factory, host=None, port=None, *, family=socket.AF_UNSPEC, flags=socket.AI_PASSIVE, sock=None, backlog=100, ssl=None, reuse_address=None, reuse_port=None)
    #   2.awiat 返回一个创建好的，绑定IP、端口、HTTP协议簇的监听服务的协程。awiat的作用是使srv的行为模式和 loop.create_server()一致
    srv = await loop.create_server(app.make_handler(),'127.0.0.1',9000)
    logging.info('server started at http://127.0.0.1:9000...')
    return srv
# 创建协程，初始化协程，返回监听服务，进入协程执行
# 1、创建协程，loop = asyncio.get_event_loop()，为asyncio.BaseEventLoop的对象，协程的基本单位。
loop = asyncio.get_event_loop()
# 2、运行协程，直到完成，BaseEventLoop.run_until_complete(future)
loop.run_until_complete(init(loop))
# 3、3.运行协程，直到调用 stop()，BaseEventLoop.run_forever()
loop.run_forever()
