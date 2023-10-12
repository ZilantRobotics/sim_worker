from typing import Callable, AsyncIterable, Awaitable

from src.api.core import Command, Result, Opcodes

DestFun = Callable[[Command], Awaitable[Result]]


class BaseCommunicator:
    dest: DestFun

    def __init__(self, dest: DestFun, *args, **kwargs): # pylint: disable=unused-argument
        self.dest = dest

    async def setup(self):
        pass

    async def run(self):
        pass

    async def receive(self) -> AsyncIterable[Command]:
        yield Command(opcode=Opcodes.noop)
