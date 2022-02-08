# def create_args_string(num):
#     L = []
#     for n in range(num):
#         L.append("?")
#     return ",".join(L)

# l = create_args_string(5)
# print(l)

from urllib.request import urlopen
import warnings
import os
import json

URL = "http://www.oreilly.com/pub/sc/osconfeed"
JSON = "C:/Users/Administrator/Desktop/osconfeed.json"

print(os.getcwd())


def load():
    if not os.path.exists(JSON):
        msg = "downloading {} to {}".format(URL, JSON)
        warnings.warn(msg)
        with urlopen(URL) as remote, open(JSON, "wb") as local:
            local.write(remote.read())
    with open(JSON) as fp:
        return json.load(fp)


feed = load()
print(feed)
