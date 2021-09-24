import asyncio
import orm
from aiohttp import web
import logging

logging.basicConfig(level=logging.INFO)


def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    app.router.add_static("/static/", path)
    logging.info("add static %s => %s" % ("/static/", path))


# 编写一个add_route函数，用来注册一个视图函数
def add_route(app, fn):
    method = getattr(fn, "__method__", None)
    path = getattr(fn, "__route__", None)
    if path is None or method is None:
        raise ValueError("@get or @post not defined in %s." % str(fn))
    # 判断URL处理函数是否协程并且是生成器
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        # 将fn转变成协程
        fn = asyncio.coroutine(fn)
    logging.info(
        "add route %s %s => %s(%s)"
        % (
            method,
            path,
            fn.__name__,
            ", ".join(inspect.signature(fn).parameters.keys()),
        )
    )
    # 在app中注册经RequestHandler类封装的视图函数
    app.router.add_route(method, path, RequestHandler(app, fn))


def add_routes(app, module_name):
    # 从右侧检索，返回索引。若无，返回-1。
    n = module_name.rfind(".")
    # 导入整个模块
    if n == (-1):
        # __import__ 作用同import语句，但__import__是一个函数，并且只接收字符串作为参数
        # __import__('os',globals(),locals(),['path','pip'], 0) ,等价于from os import path, pip
        mod = __import__(module_name, globals(), locals())
    else:
        name = module_name[n + 1 :]
        # 只获取最终导入的模块，为后续调用dir()
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
    # dir()迭代出mod模块中所有的类，实例及函数等对象,str形式
    for attr in dir(mod):
        # 忽略'_'开头的对象，直接继续for循环
        if attr.startswith("_"):
            continue
        fn = getattr(mod, attr)
        # 确保是函数
        if callable(fn):
            method = getattr(fn, "__method__", None)
            path = getattr(fn, "__route__", None)
            if method and path:
                add_route(app, fn)


async def init(loop):
    await orm.create_pool(
        loop,
        user="www-data",
        password="www-data",
        db="awesome",
        host="192.168.0.190",
        port=3306,
    )
    app = web.Application(loop=loop)
    # app = web.Application(loop=loop, middlewares=[logger_factory, response_factory])
    # init_jinja2(app, filters=dict(datetime=datetime_filter))
    add_routes(app, "handlers")
    # add_static(app)
    srv = await loop.create_server(app.make_handler(), "127.0.0.1", 9000)
    logging.info("server started at http://127.0.0.1:9000...")
    return srv


loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()