import json
from dataclasses import is_dataclass, fields, MISSING, Field
from itertools import chain
from typing import List, get_type_hints, Type, Dict, TypeVar, get_origin, Union

from src.api.core import Command, AbstractSimCore, INCLUDE_FILE_OPCODE, Opcodes, StatusCode
from src.api.packable_dataclass import BaseEvent, DataDict, DataContainer
from src.communicators.base_communicator import BaseCommunicator, DestFun


class CliCommunicator(BaseCommunicator):
    opcodes: List[str]

    def __init__(self, dest: DestFun, opcode_list: List[str], *args, **kwargs):
        super().__init__(dest, *args, **kwargs)
        self.opcodes = opcode_list

    async def setup(self):
        result = []
        for opcode in chain(*self.opcodes):
            result += self.parse_opcodes(json.loads(opcode))

        for opcode in result:
            result = await self.dest(opcode)
            print(result)
            if result.status != StatusCode.ok:
                break

    def parse_opcodes(self, opcode: DataDict) -> List[Command]:
        opcode_name, opcode_args = list(opcode.items())[0]

        if opcode_name == INCLUDE_FILE_OPCODE:
            with open(opcode_args, 'r', encoding='utf-8') as f:
                return list(chain(*[
                    self.parse_opcodes(opcode)
                    for opcode in json.loads('\n'.join([
                        x for x in f.readlines()
                        if not x.lstrip().startswith("//")
                    ]))
                ]))

        sig = get_type_hints(AbstractSimCore.opcode_table()[opcode_name])
        sig.pop('return')
        fun_args = sig

        kw_args = {}

        for k, v in fun_args.items():
            if is_dataclass(v) and issubclass(v, BaseEvent):
                kw_args[k] = CliCommunicator._recreate_dataclass_from_json(v, opcode_args[k])
            else:
                kw_args[k] = opcode_args[k]

        return [Command(
            opcode=Opcodes(opcode_name),
            args=[],
            kwargs=kw_args
        )]

    T = TypeVar('T')

    @staticmethod
    def _recreate_dataclass_from_json(_class: Type[T], dictionary: DataDict) -> T:
        obj = _class.__new__(_class)
        hints = get_type_hints(_class)
        for field in fields(obj):
            value = CliCommunicator._recreate_field_from_json(field, hints[field.name], dictionary)
            setattr(obj, field.name, value)
        return obj

    @staticmethod
    def _recreate_field_from_json(
            field: Field, type_: Type[T], data: DataContainer) -> Union[T, Dict, List]:
        if field.default != MISSING:
            value = field.default
        elif field.default_factory != MISSING:
            value = field.default_factory()
        elif is_dataclass(type_):
            value = CliCommunicator._recreate_dataclass_from_json(
                type_, data.get(field.name)
            )
        elif get_origin(type_) == List:
            # We don't support mixed Lists with Dataclasses in them
            # That is, containing dataclasses of different types,
            # dataclasses and non-dataclasses, etc
            # Mixing vanilla types is ok though
            is_dataclass_used = any(map(
                is_dataclass, CliCommunicator._typehint_types_involved(type_)
            ))
            value = [
                v if not is_dataclass_used
                else CliCommunicator._recreate_dataclass_from_json(type_.__args__[0], v)
                for v in data
            ]
        elif get_origin(type_) == Dict:
            # We don't support mixed Dict with Dataclasses in them
            # That is, containing dataclasses of different types,
            # dataclasses and non-dataclasses, etc
            # Mixing vanilla types is ok though
            is_dataclass_used = any(map(
                is_dataclass,
                CliCommunicator._typehint_types_involved(type_.__args__[1])
            ))
            value = {
                k: v if not is_dataclass_used else
                CliCommunicator._recreate_dataclass_from_json(type_.__args__[0], v)
                for k, v in data.items()
            }
        else:
            value = data[field.name]

        return value

    @staticmethod
    def _typehint_types_involved(hint) -> List[Type]:
        hints = hint.__args__

        res = hint.__args__

        while hints:
            hint = hints.pop()
            if getattr(hint, '__args__', None) is not None:
                hints += hint.__args__
            else:
                res += hint

        return hints
