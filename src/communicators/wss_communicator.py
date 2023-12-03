import asyncio
from typing import Optional, AsyncIterable

from ..api.core import Result, Command
from ..api.websocket_connection.websocket_client import Client
from ..api.websocket_connection.websocket_server import Server
from ..communicators.base_communicator import BaseCommunicator
from ..logger import logger
from ..utils import exec_one_task

com_logger = logger.getChild('wss_com')
com_logger.setLevel(logger.level)
com_logger.handlers = []


class WssCommunicator(BaseCommunicator):
    """
    This class serves as a connector between the sim core and WSS communication channel
    Sim core is the actual thing that executes opcodes, like start sim, stop sim etc.
    WSS channel allows sending Commands across the WSS channel

    This communicator works as a client by default, but can also launch its own
    server if needed e.g. for CLI connections from the local network
    """
    wss_srv: Optional[Server]
    wss_client: Client

    def __init__(
            self, remote_host: str, remote_port: int,
            name: str, uuid: str, cert: str,
            is_local_wss_enabled: bool,
            *args, local_port: int = None, local_host: str = None, **kwargs):
        super().__init__(*args, **kwargs)

        if is_local_wss_enabled:
            com_logger.info('Running communicator with a local server')
            self.wss_srv = Server(
                host=local_host,
                port=local_port,
            )
        else:
            self.wss_srv = None
            com_logger.info('Running communicator without a local server')

        self.wss_client = Client(
            host=remote_host,
            port=remote_port,
            name=name,
            uuid=uuid,
            cert=cert
        )

    async def setup(self):
        await self.wss_client.connect()

    async def run(self):
        if self.wss_srv is not None:
            await self.wss_srv.run(blocking=False)

    async def receive(self) -> AsyncIterable[Command]:
        if self.wss_srv is None:
            while True:
                yield await self.wss_client.recv()
        else:
            while True:
                tasks = [
                    asyncio.create_task(self.wss_client.recv()),
                    asyncio.create_task(self.wss_srv.recv())
                ]
                yield await exec_one_task(tasks)

    async def send(self, msg: Result):
        if self.wss_client.connection is None:
            com_logger.warning(f'A message to server sent but there is no server: {msg}')
            return

        await self.wss_client.send(msg)
