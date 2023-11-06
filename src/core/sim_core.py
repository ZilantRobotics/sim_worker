# pylint: disable=no-member
# because grpc
from __future__ import annotations
import asyncio
import os.path
import subprocess
import tempfile
from asyncio.subprocess import Process
from shlex import quote
from subprocess import PIPE
from typing import List, Type, Callable, Set, Coroutine, Any, Optional, Union

from collections import deque
import grpc
from autopilot_tools.enums import Devices
from autopilot_tools.px4.px_uploader import px_uploader
from autopilot_tools.utilities.autopilot_configurator import SERIAL_PORTS
from autopilot_tools.vehicle import Vehicle
from src.api.core import AbstractSimCore, Result, Pose, ModeEnum, Command, StatusCode
from src.communicators.base_communicator import BaseCommunicator
from src.logger import logger
from simulator3d.API.zlrsimapi import api_pb2, api_pb2_grpc

MAX_LEN = 10000

SIM_3D_HOST = '172.23.48.1'
SIM_3D_PORT = 3258


def log_opcodes(
        fun: Callable[..., Coroutine[Any, Any, Result]]
        ) -> Callable[..., Coroutine[Any, Any, Result]]:
    async def wrapper(*args, **kwargs):
        logger.info(f'Opcode {fun.__name__} called with arguments: {args[1:]}, {kwargs}')
        return await fun(*args, **kwargs)
    return wrapper


def catch_errors_to_result(
        fun: Callable[..., Coroutine[Any, Any, Result]]
        ) -> Callable[..., Coroutine[Any, Any, Result]]:
    async def wrapper(*args, **kwargs):
        try:
            return await fun(*args, **kwargs)
        except Exception as exc: # pylint: disable=broad-exception-caught
            return Result(
                status=StatusCode.error,
                message={'exception': f'{type(exc)}: {str(exc)}'}
            )
    return wrapper


def requires_autopilot_connection(
        fun: Callable[..., Coroutine[Any, Any, Result]]
        ) -> Callable[..., Coroutine[Any, Any, Result]]:
    async def wrapper(instance: SimCore, *args, **kwargs):
        if instance.vehicle_instance is None:
            instance.vehicle_instance = Vehicle()
            instance.vehicle_instance.connect(device=instance.connection_device)
        return await fun(instance, *args, **kwargs)

    return wrapper


def requires_sim3d_connection(
        fun: Callable[..., Coroutine[Any, Any, Result]]
        ) -> Callable[..., Coroutine[Any, Any, Result]]:
    async def wrapper(instance: SimCore, *args, **kwargs):
        if instance.sim3d_connection is None:
            channel = grpc.insecure_channel(f'{SIM_3D_HOST}:{SIM_3D_PORT}')
            instance.sim3d_connection = api_pb2_grpc.APIStub(channel)
        return await fun(instance, *args, **kwargs)

    return wrapper


class SimCore(AbstractSimCore):
    communicator: BaseCommunicator
    sim_3d_path: str
    hitl_sim_path: str

    sim_3d_process: Process = None
    hitl_sim_process: Process = None

    sim_3d_log: deque
    hitl_sim_log: deque

    _monitor_tasks: Set[asyncio.Task]
    _with_3d_sim: bool = True

    connection_device: Devices
    vehicle_instance: Optional[Vehicle] = None

    sim3d_connection: api_pb2_grpc.APIStub = None

    def __init__(self, communicator: Type[BaseCommunicator],
                 sim_3d_path: str, hitl_sim_path: str, *args, **kwargs):
        self.sim_3d_path = sim_3d_path
        self.hitl_sim_path = hitl_sim_path
        self.communicator = communicator(
            dest=self.dispatch, *args, **kwargs)
        self.sim_3d_log = deque([], maxlen=MAX_LEN)
        self.hitl_sim_log = deque([], maxlen=MAX_LEN)
        self._monitor_tasks = set()
        super().__init__()

    def run(self) -> None:

        async def recv_commands():
            async for command in self.communicator.receive():
                await self.dispatch(command)

        async def main():
            await self.communicator.setup()

            await asyncio.gather(
                self.communicator.run(),
                recv_commands())
            await self.cleanup()

        asyncio.run(main())

    async def cleanup(self):
        print(await self.stop_sim())

    async def dispatch(self, cmd: Command) -> Result:
        return await self[cmd.opcode](
            *cmd.args,
            **cmd.kwargs
        )

    @catch_errors_to_result
    @log_opcodes
    async def start_sim(self, mode: ModeEnum, start_3d_sim: bool = True) -> Result:
        self._with_3d_sim = start_3d_sim
        self.connection_device = Devices.serial if mode == ModeEnum.HITL else Devices.udp
        self.hitl_sim_process = await asyncio.create_subprocess_shell(
            f'{self.hitl_sim_path} {quote(mode)}',
            stdout=PIPE,
            stderr=PIPE,
            shell=True,
            executable='/bin/bash'
        )
        if start_3d_sim:
            self.sim_3d_process = await asyncio.create_subprocess_shell(
                self.sim_3d_path,
                stdout=PIPE,
                stderr=PIPE,
                shell=True,
                executable='/bin/bash'
            )

        async def monitor_process(proc: Process, log: deque):
            line = await asyncio.gather(
                proc.stdout.readline(), proc.stderr.readline()
            )
            line = list(filter(lambda x: x, map(lambda x: x.decode().strip(), line)))

            while line:
                log += line
                line = await asyncio.gather(
                    proc.stdout.readline(), proc.stderr.readline()
                )
                line = list(filter(lambda x: x, map(lambda x: x.decode().strip(), line)))

        hitl_monitor_task = asyncio.create_task(
            monitor_process(self.hitl_sim_process, self.hitl_sim_log))
        hitl_monitor_task.add_done_callback(self._monitor_tasks.discard)

        if start_3d_sim:
            monitor_3d_task = asyncio.create_task(
                monitor_process(self.sim_3d_process, self.sim_3d_log))
            monitor_3d_task.add_done_callback(self._monitor_tasks.discard)

            self._monitor_tasks = {
                hitl_monitor_task,
                monitor_3d_task
            }
        else:
            self._monitor_tasks = {
                hitl_monitor_task
            }
        await asyncio.sleep(1)

        if all([
            self.sim_3d_process.returncode is None,
                self.hitl_sim_process.returncode is None]):
            return Result(
                status=StatusCode.ok,
            )
        return Result(
            status=StatusCode.error,
            message={
                '3d_sim_log': list(self.sim_3d_log),
                'hitl_sim_log': list(self.hitl_sim_log)
            }
        )

    @catch_errors_to_result
    @log_opcodes
    async def stop_sim(self) -> Result:
        res = subprocess.Popen(f'{self.hitl_sim_path} kill', shell=True).wait()
        if self._with_3d_sim:
            try:
                self.sim_3d_process.kill()
            except ProcessLookupError:
                pass

        try:
            self.hitl_sim_process.kill()
        except ProcessLookupError:
            pass
        self.disconnect_autopilot()

        while (self.hitl_sim_process.returncode is None
                or self.sim_3d_process.returncode is None):
            await asyncio.sleep(1)

        if res == 0:
            return Result(
                status=StatusCode.ok,
            )
        return Result(
            status=StatusCode.error,
            message={'error': 'failed to kill hitl sim'}
        )

    @log_opcodes
    @requires_sim3d_connection
    async def load_scene(self, scene_name: str) -> Result:
        if self.sim3d_connection.GetCurrentScene(
                api_pb2.GetCurrentSceneRequest()).scene == scene_name:
            self.sim3d_connection.Reset(api_pb2.ResetRequest())
        else:
            self.sim3d_connection.LoadScene(api_pb2.LoadSceneRequest(scene=scene_name))
        self.sim3d_connection.Run(api_pb2.RunRequest(timeLimit=0))
        return Result(
            status=StatusCode.ok,
        )

    @log_opcodes
    @requires_sim3d_connection
    async def spawn_agent(self, agent_name: str, position: Pose) -> Result:
        _ = self.sim3d_connection.GetSpawn(api_pb2.GetSpawnRequest())
        agent_uid = self.sim3d_connection.SpawnAgent(api_pb2.SpawnAgentRequest(state=api_pb2.State(
            transform=api_pb2.Transform(
                position=api_pb2.Vector3(x=(v := position.transform.position).x, y=v.y, z=v.z),
                rotation=api_pb2.Vector3(x=(v := position.transform.rotation).x, y=v.y, z=v.z),
            ),
            velocity=api_pb2.Vector3(x=(v := position.velocity).x, y=v.y, z=v.z),
            angularVelocity=api_pb2.Vector3(x=(v := position.angular_velocity).x, y=v.y, z=v.z)),
            type=1,
            name='Quadcopter-M690')).uid
        self.sim3d_connection.Run(api_pb2.RunRequest(timeLimit=0))


        return Result(
            status=StatusCode.ok,
            message={'uid': agent_uid}
        )

    @log_opcodes
    @requires_sim3d_connection
    async def remove_agent(self, agent_id: str) -> Result:
        remove_agent_request = api_pb2.RemoveAgentRequest(uid=self.uid)
        remove_agent_response = self.sim3d_connection.RemoveAgent(remove_agent_request)
        return Result(
            status=StatusCode.ok,
            message={'message': remove_agent_response}
        )

    @log_opcodes
    @catch_errors_to_result
    @requires_autopilot_connection
    async def configure_autopilot(
            self, firmware: Union[str, os.PathLike],
            config: List[Union[str, os.PathLike]]) -> Result:

        if os.path.exists(firmware):
            px_uploader([firmware], SERIAL_PORTS)
        else:
            # this should be dealt with without os.path.exists hackery
            # If user indeed specifies a path but makes a typo, the control will go here
            # And the uploader will try to parse that path as a valid content of a firmware file
            # That will fail. Spectacularly. Obviously

            # Use PathLike typehint as a clue?
            temp_file = tempfile.NamedTemporaryFile('w', delete=False)
            with open(temp_file.name, 'w', encoding='utf-8') as f:
                f.write(firmware)
            px_uploader(  # if you provided a path and stuck here, check your path
                [temp_file.name], SERIAL_PORTS
            )
            os.remove(temp_file.name)

        self.vehicle_instance.reset_params_to_default()
        for config_file in config:
            # Same hackery here
            if os.path.exists(config_file):
                self.vehicle_instance.configure(config_file)
            else:
                self.vehicle_instance.configures(  # if stuck here, check your path
                    config_file
                )
        self.vehicle_instance.reboot()
        return Result(
            status=StatusCode.ok
        )

    @log_opcodes
    @catch_errors_to_result
    @requires_autopilot_connection
    async def upload_mission(self, mission: Union[str, os.PathLike]) -> Result:
        if os.path.exists(mission):
            self.vehicle_instance.load_mission(mission)
        else:
            self.vehicle_instance.loads_mission(  # if stuck here, check your path
                mission
            )
        return Result(
            status=StatusCode.ok
        )

    @log_opcodes
    @catch_errors_to_result
    @requires_autopilot_connection
    async def reboot_autopilot(self) -> Result:
        self.vehicle_instance.reboot()
        return Result(
            status=StatusCode.ok
        )

    @log_opcodes
    @catch_errors_to_result
    @requires_autopilot_connection
    async def start_mission(self) -> Result:
        await asyncio.sleep(3)
        res = self.vehicle_instance.run_mission(timeout=20)
        return Result(
            status=res.status,
            message={'result': res}
        )

    @log_opcodes
    async def abort_mission(self) -> Result:
        pass

    def disconnect_autopilot(self):
        if self.vehicle_instance is not None:
            self.vehicle_instance.master.close()
        self.vehicle_instance = None
