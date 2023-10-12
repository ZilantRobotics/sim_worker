from dataclasses import dataclass

from src.api.packable_dataclass import BaseEvent


@dataclass
class Greeting(BaseEvent):
    name: str
    uuid: str
