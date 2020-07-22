import asyncio
import logging
import aiomysql


async def create_pool(loop, **kw):
    logging.info("create database connection pool...")
    global __pool
    __pool = await aiomysql.create_pool(
        host=kw.get("host", "localhost"),
        port=kw.get("port", 3306),
        user=kw["user"],
        password=kw["password"],
        db=kw["db"],
        charset=kw.get("charset", "utf8"),
        autocommit=kw.get("autocommit", True),
        maxsize=kw.get("maxsize", 10),
        minsize=kw.get("minsize", 1),
        loop=loop,
    )


async def select(sql, size=None):
    global __pool
    async with __pool.get() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql.replace("?", "%s"))
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()

        logging.info("rows returned: %s" % len(rs))
        return rs


async def test(loop):
    await create_pool(
        loop,
        user="www-data",
        password="www-data",
        db="awesome",
        host="192.168.0.190",
        port=3306,
    )

    rs = await select("select * from users")
    print(rs)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test(loop))
