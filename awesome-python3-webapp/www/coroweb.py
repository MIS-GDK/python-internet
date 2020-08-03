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
