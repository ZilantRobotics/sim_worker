import asyncio
import json
import ssl
from asyncio import Task
from dataclasses import dataclass, field
from typing import Dict, cast, Callable, Optional, Awaitable

import websockets
from websockets.legacy.server import WebSocketServerProtocol, WebSocketServer

from src.api.core import Command, Pose, Vector3, Opcodes, AgentName, Transform
from src.api.packable_dataclass import BaseEvent
from src.api.websocket_connection.messages import Greeting
from src.exceptions import DataclassJsonException
from src.logger import logger

ws_logger = logger.getChild('wss_srv')
ws_logger.propagate = False
ws_logger.setLevel(logger.level)
ws_logger.handlers = logger.handlers


@dataclass
class Worker:
    name: str
    uuid: str
    connection: WebSocketServerProtocol
    message_task: Task


@dataclass
class Server:
    host: str
    port: int
    recv_callback: Callable[[WebSocketServerProtocol, BaseEvent], Awaitable[None]]

    cert: str = None
    key: str = None
    ssl_context: ssl.SSLContext = field(init=False)
    workers: Dict[str, Worker] = field(init=False, default_factory=dict)
    is_using_ssl: bool = field(init=False)

    def __post_init__(self):
        self.is_using_ssl = self.cert is not None and self.key is not None
        if self.is_using_ssl:
            ws_logger.info("Using secure sockets")
            self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.ssl_context.load_cert_chain(certfile=self.cert, keyfile=self.key)
        else:
            ws_logger.info("Using plain sockets")

    async def send_message(self, worker_name: str, msg: BaseEvent):
        await self.workers[worker_name].connection.send(msg.pack())

    async def connected(self, websocket: WebSocketServerProtocol):
        try:
            greeting = cast(Greeting, BaseEvent.unpack(json.loads(await websocket.recv())))
        except DataclassJsonException:
            ws_logger.error('Malformed greeting. Terminating')
            return
        ws_logger.info(f'Worker {greeting.uuid}/{greeting.name} joined')

        async def recv_commands():
            while True:
                await self.recv_callback(
                    websocket,
                    BaseEvent.unpack(json.loads(await websocket.recv()))
                )
                await asyncio.sleep(0)

        self.workers[greeting.uuid] = Worker(
            name=greeting.name,
            uuid=greeting.uuid,
            connection=websocket,
            message_task=asyncio.create_task(recv_commands())
        )
        await websocket.wait_closed()
        worker = self.workers.pop(greeting.uuid)
        worker.message_task.cancel()
        ws_logger.info(f'Worker {greeting.uuid}/{greeting.name} left')
        ws_logger.debug(f'There are {len(self.workers)} workers left')

    async def run(self, blocking: bool = True) -> Optional[WebSocketServer]:
        if self.is_using_ssl:
            srv = websockets.serve( # pylint: disable=E1101
                    self.connected, self.host, self.port, ssl=self.ssl_context,
                    logger=ws_logger)
        else:
            srv = websockets.serve( # pylint: disable=E1101
                    self.connected, self.host, self.port, logger=ws_logger)
        if blocking:
            async with srv:
                await asyncio.Future()
        else:
            return await srv


async def echo(_: WebSocketServerProtocol, data: BaseEvent) -> None:
    print(data)

if __name__ == '__main__':
    a = Server(
        host='localhost',
        port=9999,
        cert='../../../sample_config/ca/ca_cert.pem',
        key='../../../sample_config/ca/ca.pem',
        recv_callback=echo
    )

    async def _srv():
        await a.run(blocking=False)

    p = Pose(
        velocity=Vector3(12, 3, 4),
        angular_velocity=Vector3(12, 3, 4),
        transform=Transform(
            position=Vector3(12, 3, 4),
            rotation=Vector3(12, 3, 4)
        )
    )

    cmd = Command(
        opcode=Opcodes.spawn_agent,
        args=[],
        kwargs={'agent_name': AgentName.octo_amazon, 'position': p}
    )

    async def _msg():
        while True:
            await asyncio.sleep(5)
            for worker in a.workers.values():
                await worker.connection.send(
                    json.dumps(cmd.pack())
                )

    async def main():
        await asyncio.gather(
            _srv(),
            _msg()
        )

    asyncio.run(main())
