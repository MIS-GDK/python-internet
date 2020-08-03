import orm
from models import User, Blog, Comment
import asyncio


async def gdk_test(loop):
    await orm.create_pool(
        loop,
        user="www-data",
        password="www-data",
        db="awesome",
        host="192.168.0.190",
        port=3306,
    )

    u = User(
        name="Test", email="test4@example.com", passwd="1234567890", image="about:blank"
    )
    await u.save()


def add(x):
    return x + x


# 要运行协程，需要使用事件循环
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(gdk_test(loop))
    print("Test finished.")
