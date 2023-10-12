from typing import cast, Optional, AsyncIterable

from websockets.legacy.server import WebSocketServerProtocol

from src.api.core import Command
from src.api.packable_dataclass import BaseEvent
from src.api.websocket_connection.websocket_client import Client
from src.api.websocket_connection.websocket_server import Server
from src.communicators.base_communicator import BaseCommunicator, DestFun
from src.logger import logger

com_logger = logger.getChild('wss_com')
com_logger.propagate = False
com_logger.setLevel(logger.level)
com_logger.handlers = logger.handlers


class WssCommunicator(BaseCommunicator):
    wss_srv: Optional[Server]
    wss_client: Client

    def __init__(
            self, dest: DestFun,
            remote_host: str, remote_port: int,
            name: str, uuid: str, cert: str,
            local_port: int, local_host: str,
            is_local_wss_enabled: bool,
            *args, **kwargs):
        super().__init__(dest, *args, **kwargs)

        if is_local_wss_enabled:
            com_logger.info('Running communicator with a local server')

            async def recv_fun(_: WebSocketServerProtocol, data: BaseEvent):
                await self.dest(cast(Command, data))

            self.wss_srv = Server(
                host=local_host,
                port=local_port,
                recv_callback=recv_fun
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
        while True:
            yield await self.wss_client.recv()
