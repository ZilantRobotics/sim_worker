from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import auto
from functools import partial
from typing import Union, List, Protocol, Dict

from strenum import StrEnum

from src.api.packable_dataclass import BaseEvent
from src.logger import logger


# You can send a message with one of those opcodes
# When adding new opcodes, don't forget to update the
# opcode table down below
class Opcodes(StrEnum):
    start_sim = auto()
    stop_sim = auto()
    load_scene = auto()
    spawn_agent = auto()
    remove_agent = auto()
    configure_autopilot = auto()
    upload_mission = auto()
    reboot_autopilot = auto()
    start_mission = auto()
    abort_mission = auto()
    noop = auto()


INCLUDE_FILE_OPCODE = 'include_file'

# Here are the messages that can be sent or received across the network


@dataclass
class Vector3(BaseEvent):
    x: Union[int, float]
    y: Union[int, float]
    z: Union[int, float]


@dataclass
class Pose(BaseEvent):
    transform: Vector3
    velocity: Vector3
    angular_velocity: Vector3


@dataclass
class Command(BaseEvent):
    opcode: Opcodes
    args: List[Union[str, int, float, BaseEvent]] = field(default_factory=list)
    kwargs: Dict[str, Union[str, int, float, BaseEvent]] = field(default_factory=dict)


@dataclass
class Result(BaseEvent):
    status: StatusCode
    message: dict


class AbstractSimCore(ABC):
    def __init__(self):
        for opcode in Opcodes:
            if opcode not in self.opcode_table():
                logger.warning(f"Opcode {opcode} not found in the opcodes table. "
                               f"Did you forget to update it?")

    @abstractmethod
    def start_sim(self, mode: ModeEnum) -> Result:
        pass

    @abstractmethod
    def stop_sim(self) -> Result:
        pass

    @abstractmethod
    def load_scene(self, scene_name: str) -> Result:
        pass

    @abstractmethod
    def spawn_agent(self, agent_name: str, position: Pose) -> Result:
        pass

    @abstractmethod
    def remove_agent(self, agent_id: str) -> Result:
        pass

    @abstractmethod
    def configure_autopilot(self, firmware: str, config: List[str]) -> Result:
        pass

    @abstractmethod
    def upload_mission(self, mission: str) -> Result:
        pass

    @abstractmethod
    def reboot_autopilot(self) -> Result:
        pass

    @abstractmethod
    def start_mission(self) -> Result:
        pass

    @abstractmethod
    def abort_mission(self) -> Result:
        pass

    def __getitem__(self, item: Opcodes) -> OpcodeMethod:
        return partial(self.opcode_table()[item], self)

    @classmethod
    def opcode_table(cls):
        return {
            Opcodes.start_sim: cls.start_sim,
            Opcodes.stop_sim: cls.stop_sim,
            Opcodes.load_scene: cls.load_scene,
            Opcodes.spawn_agent: cls.spawn_agent,
            Opcodes.remove_agent: cls.remove_agent,
            Opcodes.configure_autopilot: cls.configure_autopilot,
            Opcodes.upload_mission: cls.upload_mission,
            Opcodes.reboot_autopilot: cls.reboot_autopilot,
            Opcodes.start_mission: cls.start_mission,
            Opcodes.abort_mission: cls.abort_mission,
            Opcodes.noop: lambda *args, **kwargs: None
        }


class ModeEnum(StrEnum):
    HITL_with_innosim = "hitl_innosim"
    SITL_with_innosim = "sitl_innosim"


class SceneName(StrEnum):
    innopolis = "MainScene"
    construction = "ConstructionScene"


class StatusCode(StrEnum):
    ok = "ok"
    error = "error"
    permission_denied = "permission_denied"


class AgentName(StrEnum):
    octo_amazon = "Octocopter-Amazon"
    vtol_seeker = "Vtol-Seeker"
    octo_amazon01 = "Octocopter-Amazon01"
    vtol_t300 = "Vtol-T300"
    quad_m690 = "Quadcopter-M690"
    vtol_tfm15 = "Vtol-TFM15"


class OpcodeMethod(Protocol):
    def __call__(self, *args: List, **kwargs: Dict) -> Result:
        pass


if __name__ == '__main__':
    p = Pose(
        velocity=Vector3(12, 3, 4),
        angular_velocity=Vector3(12, 3, 4),
        transform=Vector3(12, 3, 4)
    )

    cmd = Command(
        opcode=Opcodes.spawn_agent,
        args=[AgentName.octo_amazon, p],
        kwargs={'agent_name': AgentName.octo_amazon, 'position': p}
    )
    print(p)
    f = cmd.pack()
    print(f)
    k = BaseEvent.unpack(f)
    print(k)