# def MetaClass(name, bases, attrs):
#     attrs["Author"] = "Megvii"
#     return type(name, bases, attrs)


class MetaClass1(type):
    so = "aaa"

    def __new__(cls, name, bases, attrs):
        attrs["Author"] = "Megvii"
        print(cls)
        print(cls.so)
        return type.__new__(cls, name, bases, attrs)


class InsClass(object, metaclass=MetaClass1):
    so = "bbb"
    Imethod = "InsClass"

    def __init__(self, param):
        self.__param = param


obj6 = InsClass("test_instance")
print(obj6.Author)
print(dir(obj6))

from unicodedata import name


class A:
    def __init__(self, name, age) -> None:
        self.name = name
        self.age = age


a = A("马志强", 34)
print(type(a))
