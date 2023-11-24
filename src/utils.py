import asyncio
from typing import List, TypeVar, Awaitable

T = TypeVar('T')


async def exec_one_task(
        tasks: List[Awaitable[T]]) -> T:
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    for task in pending:
        task.cancel()

    for task in done:
        return task.result()
