import asyncio
from typing import List, Type, Callable

from src.api.core import AbstractSimCore, Result, Pose, ModeEnum, Command
from src.communicators.base_communicator import BaseCommunicator
from src.logger import logger


def log_opcodes(fun: Callable[..., Result]) -> Callable[..., Result]:
    def wrapper(*args, **kwargs):
        logger.info(f'Opcode {fun.__name__} called with arguments: {args[1:]}, {kwargs}')
        return fun(*args, **kwargs)
    return wrapper


class SimCore(AbstractSimCore):
    communicator: BaseCommunicator

    def __init__(self, communicator: Type[BaseCommunicator], *args, **kwargs):
        self.communicator = communicator(
            dest=self.dispatch, *args, **kwargs)
        super().__init__()

    @log_opcodes
    def start_sim(self, mode: ModeEnum) -> Result:
        pass

    @log_opcodes
    def stop_sim(self) -> Result:
        pass

    @log_opcodes
    def load_scene(self, scene_name: str) -> Result:
        pass

    @log_opcodes
    def spawn_agent(self, agent_name: str, position: Pose) -> Result:
        pass

    @log_opcodes
    def remove_agent(self, agent_id: str) -> Result:
        pass

    @log_opcodes
    def configure_autopilot(self, firmware: str, config: List[str]) -> Result:
        pass

    @log_opcodes
    def upload_mission(self, mission: str) -> Result:
        pass

    @log_opcodes
    def reboot_autopilot(self) -> Result:
        pass

    @log_opcodes
    def start_mission(self) -> Result:
        pass

    @log_opcodes
    def abort_mission(self) -> Result:
        pass

    async def dispatch(self, cmd: Command) -> Result:
        return self[cmd.opcode](
            *cmd.args,
            **cmd.kwargs
        )

    def run(self) -> None:

        async def recv_commands():
            async for command in self.communicator.receive():
                await self.dispatch(command)

        async def main():
            await self.communicator.setup()

            await asyncio.gather(
                self.communicator.run(),
                recv_commands())

        asyncio.run(main())
