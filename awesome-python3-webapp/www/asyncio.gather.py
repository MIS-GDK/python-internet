import asyncio


async def a():
    print("Suspending a")
    await asyncio.sleep(3)
    print("Resuming a")
    return "A"


async def b():
    print("Suspending b")
    await asyncio.sleep(1)
    print("Resuming b")
    return "B"


async def main():
    # return_value_a, return_value_b = await asyncio.gather(a(), b())
    # print(return_value_a, return_value_b)
    done, pending = await asyncio.wait([a(), b()], return_when="FIRST_COMPLETED")
    print(done)
    print(pending)


# loop = asyncio.get_event_loop()
# loop.run_until_complete(main())
asyncio.run(main())