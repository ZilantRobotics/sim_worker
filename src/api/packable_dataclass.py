from __future__ import annotations
from dataclasses import dataclass, fields, is_dataclass
from functools import lru_cache
from typing import Dict, Union, get_type_hints, TypeVar, List, get_origin, Type

from src.exceptions import MalformedDataclassJson, UnknownMessage

SimpleTypes = Union[str, dict, int, float]
DataDict = Dict[str, SimpleTypes]
DataContainer = Union[DataDict, List[SimpleTypes]]


@dataclass
class BaseEvent:
    """
    This is a base class for dataclasses that can be packed to and unpacked from json
    to transfer across the network. It uses special json format to uniquely recreate
    the dataclass on the other end of the network.

    This class uses type annotations a LOT, so it is an imperative to annotate fields

    For now all fields are included in the packed json (and used to recreate a dataclass back)
    """
    def pack(self) -> DataDict:
        res = {
            'type': str(type(self)),
            'data': {}
        }
        BaseEvent._to_dict_recurse(res['data'], self)
        return res

    @staticmethod
    def _to_dict_recurse(res: DataDict, part: BaseEvent) -> DataDict:
        # Pull out types and arg names
        types_involved = get_type_hints(type(part))
        for type_, name in [(types_involved[n.name], n.name) for n in fields(part)]:
            res[name] = BaseEvent._parse_field(type_, part, name)
        return res

    @staticmethod
    def _parse_field(
            type_: Type[DataDict],
            part: Union[BaseEvent, List, Dict],
            name: str = None) -> DataContainer:

        source = part if name is None else getattr(part, name)

        if is_dataclass(type_):
            return {
                'type': str(type_),
                'data': BaseEvent._to_dict_recurse({}, source)
            }
        if get_origin(type_) == get_origin(Dict):
            return {
                k: BaseEvent._parse_field(type(v), v, None)
                for k, v in source.items()
            }
        if get_origin(type_) == get_origin(List):
            return [
                BaseEvent._parse_field(type(v), v, None)
                for v in source
            ]
        return source

    @classmethod
    def unpack(cls, dictionary: DataDict) -> BaseEvent:
        if 'type' not in dictionary or 'data' not in dictionary:
            raise MalformedDataclassJson(dictionary)
        return BaseEvent._from_dict_recurse(dictionary)

    @staticmethod
    def _from_dict_recurse(src: DataContainer) -> Union[BaseEvent, List, Dict]:
        # Pull type from the corresponding field, create a new object from the type_table
        # And populate it with data, for dataclas-field recurse onwards until there are only simple
        # args
        obj = None
        if isinstance(src, dict):
            if 'type' in src and 'data' in src:
                # This is a dataclass dict
                try:
                    cls_ = BaseEvent.type_table()[src['type']]
                except KeyError as exc:
                    raise UnknownMessage(src['type']) from exc
                obj = cls_(
                    **{
                        k: BaseEvent._from_dict_recurse(v)
                        for k, v in src['data'].items()
                    }
                )
            else:
                obj = {
                    k: BaseEvent._from_dict_recurse(v)
                    for k, v in src.items()
                }
        elif isinstance(src, list):
            obj = [BaseEvent._from_dict_recurse(v) for v in src]
        else:
            obj = src

        if obj is None:
            raise MalformedDataclassJson(src)

        return obj

    @classmethod
    @lru_cache
    def type_table(cls):
        subclasses = cls.__subclasses__()
        res = cls.__subclasses__()
        while subclasses:
            subclass = subclasses.pop()
            subclasses += subclass.__subclasses__()
            res += subclass.__subclasses__()

        return {
            str(t): t for t in res
        }

    T = TypeVar('T')
