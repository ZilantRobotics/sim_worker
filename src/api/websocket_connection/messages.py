from dataclasses import dataclass

from ..packable_dataclass import BaseEvent


@dataclass
class Greeting(BaseEvent):
    name: str
    uuid: str
