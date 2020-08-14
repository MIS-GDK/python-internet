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
                qs = request.query_string
                if qs:
                    # Parse a query string given as a string argument.
                    # Data are returned as a dictionary.
                    # The dictionary keys are the unique query variable names and the values are lists of values for each name.
                    kw = dict()
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]
        if kw is None:
            kw = dict(**request.match_info)

