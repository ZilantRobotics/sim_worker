import asyncio
import json
import ssl
from dataclasses import dataclass, field
from typing import Dict, cast, Optional, Callable, Awaitable

import websockets
from websockets.legacy.server import WebSocketServerProtocol, WebSocketServer

from ...utils import exec_one_task
from ..core import Command, Pose, Vector3, Opcodes, AgentName, Transform
from ..packable_dataclass import BaseEvent
from ..websocket_connection.messages import Greeting
from ...exceptions import DataclassJsonException
from ...logger import logger

ws_logger = logger.getChild('wss_srv')
ws_logger.propagate = False
ws_logger.setLevel(ws_logger.level)
ws_logger.handlers = ws_logger.handlers


@dataclass
class Worker:
    name: str
    uuid: str
    connection: WebSocketServerProtocol


@dataclass
class Server:
    host: str
    port: int
    join_callback: Callable[[str, str], Awaitable[None]] = None
    leave_callback: Callable[[str, str], Awaitable[None]] = None

    cert: str = None
    key: str = None
    ssl_context: ssl.SSLContext = field(init=False)
    workers: Dict[str, Worker] = field(init=False, default_factory=dict)
    is_using_ssl: bool = field(init=False)

    def __post_init__(self):
        self.is_using_ssl = self.cert is not None and self.key is not None
        if self.is_using_ssl:
            logger.info("Using secure sockets")
            self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.ssl_context.load_cert_chain(certfile=self.cert, keyfile=self.key)
        else:
            logger.info("Using plain sockets")

    async def send_message(self, worker_name: str, msg: BaseEvent):
        await self.workers[worker_name].connection.send(msg.pack())

    async def connected(self, websocket: WebSocketServerProtocol):
        try:
            greeting = cast(Greeting, BaseEvent.unpack(json.loads(await websocket.recv())))
        except DataclassJsonException:
            logger.error('Malformed greeting. Terminating')
            return
        ws_logger.info(f'Worker {greeting.uuid}/{greeting.name} joined')
        if self.join_callback is not None:
            await self.join_callback(greeting.uuid, greeting.name)

        self.workers[greeting.uuid] = Worker(
            name=greeting.name,
            uuid=greeting.uuid,
            connection=websocket,
        )
        await websocket.wait_closed()
        if self.leave_callback is not None:
            await self.leave_callback(greeting.uuid, greeting.name)
        _ = self.workers.pop(greeting.uuid)
        ws_logger.info(f'Worker {greeting.uuid}/{greeting.name} left')
        ws_logger.debug(f'There are {len(self.workers)} workers left')

    async def run(self, blocking: bool = True) -> Optional[WebSocketServer]:
        if self.is_using_ssl:
            srv = websockets.serve(  # pylint: disable=E1101
                    self.connected, self.host, self.port, ssl=self.ssl_context,
                    logger=ws_logger)
        else:
            srv = websockets.serve(  # pylint: disable=E1101
                    self.connected, self.host, self.port, logger=ws_logger)
        if blocking:
            async with srv:
                await asyncio.Future()
        else:
            return await srv

    async def recv(self) -> Dict[str, Command]:

        async def worker_aware_recv(worker: Worker) -> Dict[str, Command]:
            return {
                worker.name: await worker.connection.recv()
            }
        tasks = [
            asyncio.create_task(worker_aware_recv(worker))
            for worker in self.workers.values()
        ]
        return await exec_one_task(tasks)


async def echo(_: WebSocketServerProtocol, data: BaseEvent) -> None:
    print(data)

if __name__ == '__main__':
    a = Server(
        host='localhost',
        port=9999,
        cert='../../../sample_config/ca/ca_cert.pem',
        key='../../../sample_config/ca/ca.pem',
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
