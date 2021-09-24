import inspect


def foo(a, *b, c, **d):
    pass


for name, parame in inspect.signature(foo).parameters.items():
    print(name, ": ", parame.kind)



data = {'a':7, 'b':8}
print(dict(**data))