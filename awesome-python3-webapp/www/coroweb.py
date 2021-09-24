__author__ = "MIS-GDK"

import asyncio, os, inspect, logging, functools
from urllib import parse
from aiohttp import web
from apis import APIError


def get(path):
    """
    Define decoator @get('/path')
    """

    def decoator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)

        wrapper.__method__ = "GET"
        wrapper.__route__ = path
        return wrapper

    return decoator


def post(path):
    """
    Define decoator @post('/path')
    """

    def decoator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)

        wrapper.__method__ = "POST"
        wrapper.__route__ = path
        return wrapper

    return decoator


# 使用inspect模块，检查视图函数的参数

# inspect.Parameter.kind 类型：
# POSITIONAL_ONLY          位置参数
# KEYWORD_ONLY             命名关键词参数
# VAR_POSITIONAL           可选参数 *args
# VAR_KEYWORD              关键词参数 **kw
# POSITIONAL_OR_KEYWORD    位置或必选参数

# 运用inspect模块，创建几个函数用以获取URL处理函数与request参数之间的关系
# 收集没有默认值的命名关键字参数
def get_required_kw_args(fn):
    args = []
    """ 
    def foo(a, b = 10, *c, d,**kw): pass 
    sig = inspect.signature(foo) ==> <Signature (a, b=10, *c, d, **kw)> 
    sig.parameters ==>  mappingproxy(OrderedDict([('a', <Parameter "a">), ...])) 
    sig.parameters.items() ==> odict_items([('a', <Parameter "a">), ...)]) 
    sig.parameters.values() ==>  odict_values([<Parameter "a">, ...]) 
    sig.parameters.keys() ==>  odict_keys(['a', 'b', 'c', 'd', 'kw']) 
    """
    params = inspect.signature(fn).parameters  # inspect模块是用来分析模块，函数
    for name, param in params.items():
        # 如果视图函数存在命名关键字参数，且默认值为空，获取它的key（参数名）
        if (
            param.kind == inspect.Parameter.KEYWORD_ONLY
            and param.default == inspect.Parameter.empty
        ):
            args.append(name)
    return tuple(args)


# 获取命名关键字参数
def get_named_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)


# 判断有没有命名关键字参数
def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True


# 判断有没有关键字参数
def has_var_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True


# 判断是否含有名叫'request'参数，且该参数是否为最后一个参数
def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == "request":
            found = True
            continue
        if found and (
            param.kind != inspect.Parameter.VAR_POSITIONAL
            and param.kind != inspect.Parameter.KEYWORD_ONLY
            and param.kind != inspect.Parameter.VAR_KEYWORD
        ):
            # 若判断为True，表明param只能是位置参数。且该参数位于request之后，故不满足条件，报错。
            raise ValueError(
                "request parameter must be the last named parameter in function: %s%s"
                % (fn.__name__, str(sig))
            )
    return found


# 定义RequestHandler,正式向request参数获取URL处理函数所需的参数
# 调用URL函数，然后把结果转换为web.Response对象，这样，就完全符合aiohttp框架的要求
class RequestHandler(object):
    # 接受app参数
    def __init__(self, app, fn):
        self._app = app
        self._func = fn
        self._required_kw_args = get_required_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._has_named_kw_arg = has_named_kw_args(fn)
        self._has_var_kw_arg = has_var_kw_args(fn)
        self._has_request_arg = has_request_arg(fn)

    # __call__这里要构造协程
    # 1.定义kw，用于保存参数
    # 2.判断视图函数是否存在关键词参数，如果存在根据POST或者GET方法将request请求内容保存到kw
    # 3.如果kw为空（说明request无请求内容），则将match_info列表里的资源映射给kw；若不为空，把命名关键词参数内容给kw
    # 4.完善_has_request_arg和_required_kw_args属性
    async def __call__(self, request):
        # 定义kw，用于保存request中参数
        kw = None
        # 若视图函数有命名关键词或关键词参数
        if self._has_var_kw_arg or self._has_named_kw_arg or self._required_kw_args:
            # 判断客户端发来的方法是否为POST
            if request.metmod == "POST":
                # 查询有无提交数据的格式（EncType）
                if not request.content_type:
                    return web.HTTPBadRequest(text="Missing Content_Type.")
                ct = request.content_type.lower()
                if ct.startswith("application/json"):
                    # Read request body decoded as json.
                    params = await request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest(text="JSON body must be object.")
                    kw = params
                elif ct.startswith(
                    "application/x-www-form-urlencoded"
                ) or ct.startswith("multipart/form-data"):
                    # reads POST parameters from request body.
                    # If method is not POST, PUT, PATCH, TRACE or DELETE
                    # or content_type is not empty
                    # or application/x-www-form-urlencoded
                    # or multipart/form-data returns empty multidict.

                    # 返回post的内容中解析后的数据。dict-like对象。
                    params = await request.post()
                    # 组成dict，统一kw格式
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest(
                        text="Unsupported Content_Tpye: %s" % (request.content_type)
                    )
            if request.method == "GET":
                # The query string in the URL
                # 返回URL查询语句，?后的键值。string形式
                qs = request.query_string
                if qs:
                    # Parse a query string given as a string argument.
                    # Data are returned as a dictionary.
                    # The dictionary keys are the unique query variable names and the values are lists of values for each name.

                    """
                    解析url中?后面的键值对的内容
                    qs = 'first=f,s&second=s'
                    parse.parse_qs(qs, True).items()
                    >>> dict([('first', ['f,s']), ('second', ['s'])])
                    """
                    kw = dict()
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]
        # 若request中无参数
        if kw is None:
            # request.match_info返回dict对象。可变路由中的可变字段{variable}为参数名，传入request请求的path为值
            # 若存在可变路由：/a/{name}/c，可匹配path为：/a/jack/c的request
            # 则reqwuest.match_info返回{name = jack}
            print(
                "in call__() request.match_info ,**request.match_info:  ",
                request.match_info,
                " ,,,,,,,,,  ",
                **request.match_info
            )
            kw = dict(**request.match_info)
        else:
            # 若视图函数只有命名关键词参数没有关键词参数
            if self._has_named_kw_arg and (not self._has_var_kw_arg):
                copy = dict()
                # 只保留命名关键词参数
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                # kw中只存在命名关键词参数
                kw = copy
            # 将request.match_info中的参数传入kw
            for k, v in request.match_info.item():
                print("in getpost k:  ", k, "  v:  ", v)
                # 检查kw中的参数是否和match_info中的重复
                if k in kw:
                    logging.warning(
                        "Duplicate arg name in named arg and kw args: %s" % k
                    )
                kw[k] = v
            # 视图函数存在request参数
            if self._has_request_arg:
                kw["request"] = request
            # 视图函数存在无默认值的命名关键词参数
            if self._required_kw_args:
                for name in self._required_kw_args:
                    if not name in kw:  # 若未传入必须参数值，报错。
                        return web.HTTPBadRequest("Missing argument: %s" % name)
            # 至此，kw为视图函数fn真正能调用的参数
            # request请求中的参数，终于传递给了视图函数
            print("call with args: %s" % str(kw))
        # try:
        # print('in call__() **kw:  ' ,**kw)
        try:
            r = await self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)


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