import inspect

from functools import wraps


def coroutinue(func):
    """
    装饰器： 向前执行到第一个`yield`表达式，预激`func`
    :param func: func name
    :return: primer
    """

    @wraps(func)
    def primer(*args, **kwargs):
        # 把装饰器生成器函数替换成这里的primer函数；调用primer函数时，返回预激后的生成器。
        gen = func(*args, **kwargs)  # 调用被被装饰函数，获取生成器对象
        next(gen)  # 预激生成器
        return gen  # 返回生成器

    return primer


class DemoException(Exception):
    pass


@coroutinue
def exc_handling():
    print("-> coroutine started")
    while True:
        try:
            x = yield
        except DemoException:
            print("*** DemoException handled. Conginuing...")
        else:  # 如果没有异常显示接收到的值
            print("--> coroutine received: {!r}".format(x))
    raise RuntimeError("This line should never run.")  # 这一行永远不会执行


exc_coro = exc_handling()

exc_coro.send(11)
exc_coro.send(12)
exc_coro.send('222')
exc_coro.throw(DemoException)
print(inspect.getgeneratorstate(exc_coro))
exc_coro.close()
print(inspect.getgeneratorstate(exc_coro))
