from typing import Callable, AsyncIterable, Awaitable

from src.api.core import Command, Result, Opcodes

DestFun = Callable[[Command], Awaitable[Result]]


class BaseCommunicator:
    def __init__(self, *args, **kwargs):  # pylint: disable=unused-argument
        pass

    async def setup(self):
        pass

    async def run(self):
        pass

    async def receive(self) -> AsyncIterable[Command]:
        yield Command(opcode=Opcodes.noop)

    async def send(self, msg: Result):
        pass
