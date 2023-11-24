import asyncio
import json
import ssl
from asyncio import sleep
from dataclasses import dataclass, field

import websockets
from websockets.exceptions import ConnectionClosedOK
from websockets.legacy.client import WebSocketClientProtocol

from src.api.core import Command, Opcodes
from src.api.packable_dataclass import BaseEvent
from src.api.websocket_connection.messages import Greeting
from src.logger import logger

ws_logger = logger.getChild('wss_client')
ws_logger.propagate = False
ws_logger.setLevel(logger.level)
ws_logger.handlers = logger.handlers


@dataclass
class Client:
    host: str
    port: int
    uuid: str
    name: str = ""
    cert: str = None
    ssl_context: ssl.SSLContext = field(init=False)
    connection: WebSocketClientProtocol = field(init=False)

    def __post_init__(self):
        self.is_using_ssl = self.cert is not None
        if self.is_using_ssl:
            logger.info("Using secure sockets")
            self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            self.ssl_context.load_verify_locations(self.cert)
        else:
            logger.info("Using plain sockets")

    async def connect(self):
        if self.is_using_ssl:
            self.connection = await websockets.connect(  # pylint: disable=E1101
                f'wss://{self.host}:{self.port}', ssl=self.ssl_context)

        else:
            self.connection = await websockets.connect(  # pylint: disable=E1101
                f'ws://{self.host}:{self.port}')

        await self.connection.send(
            json.dumps(Greeting(name=self.name, uuid=self.uuid).pack())
        )

    async def send(self, cmd: BaseEvent):
        await self.connection.send(
            json.dumps(cmd.pack())
        )

    async def recv(self) -> BaseEvent:
        return BaseEvent.unpack(json.loads(await self.connection.recv()))

    async def close(self):
        await self.connection.close()


if __name__ == '__main__':
    a = Client(
        host='peacefulmatrix.site',
        port=9990,
        name='kek',
        uuid='1788',
        cert='../../../config/ca/ca_cert.pem'
    )


    async def src():
        await a.send(Command(
            opcode=Opcodes.noop,
            kwargs={'123': 345, '567': 1234}
        ))
        await sleep(30)
        await a.send(Command(
            opcode=Opcodes.noop
        ))
        await a.close()

    async def recv():
        while True:
            try:
                print(await a.recv())
            except ConnectionClosedOK:
                return
            await asyncio.sleep(0)

    async def main():
        await a.connect()
        await asyncio.gather(
            src(),
            recv()
        )


    asyncio.run(main())
