import math
from dataclasses import dataclass
from math import pi, e, tau
from typing import List, Dict

from src.api.packable_dataclass import BaseEvent


@dataclass
class A(BaseEvent):
    int_field: int
    float_field: float


@dataclass
class AContainer(A):
    list_field: List[int]
    dict_field: Dict[str, int]


@dataclass
class ARecursive(BaseEvent):
    a_field: A


@dataclass
class AContainerDataclass(AContainer):
    dataclass_dict: Dict[str, A]
    dataclass_list: List[A]


@dataclass
class AContainerRecurseDataclass(BaseEvent):
    dataclass_dict_recursive: Dict[str, AContainerDataclass]
    dataclass_list_recursive: List[AContainerDataclass]


phi = (1 + math.sqrt(5)) / 2


class TestPackable:

    @staticmethod
    def assert_pack_unpack(a: BaseEvent):
        return str(a) == str(BaseEvent.unpack(a.pack()))

    def test_very_simple(self):
        a = A(
            int_field=1,
            float_field=pi)
        assert TestPackable.assert_pack_unpack(a)

    def test_recursive_data(self):
        a = A(
            int_field=1,
            float_field=pi)
        a_recurse = ARecursive(a)
        assert TestPackable.assert_pack_unpack(a_recurse)

    def test_native_containers(self):
        a_containers = AContainer(
            int_field=1,
            float_field=pi,
            list_field=[1, 2, 3, 4],
            dict_field={'ultimate_answer': 42, 'funny_number': 69}
        )
        assert TestPackable.assert_pack_unpack(a_containers)

    def test_native_containers_of_dataclasses(self):
        a1 = A(
            int_field=1,
            float_field=pi)
        a2 = A(
            int_field=2,
            float_field=e)
        a_containers_of_dataclasses = AContainerDataclass(
            int_field=1,
            float_field=pi,
            list_field=[1, 2, 3, 4],
            dict_field={'ultimate_answer': 42, 'funny_number': 69},
            dataclass_list=[a1, a2],
            dataclass_dict={'pi': a1, 'e': a2}
        )
        TestPackable.assert_pack_unpack(a_containers_of_dataclasses)

    def test_native_containers_of_dataclasses_recursive(self):
        a1 = A(
            int_field=1,
            float_field=pi)
        a2 = A(
            int_field=2,
            float_field=e)
        a3 = A(
            int_field=3,
            float_field=tau)
        a4 = A(
            int_field=4,
            float_field=phi)
        a_containers_of_dataclasses1 = AContainerDataclass(
            int_field=1,
            float_field=pi,
            list_field=[1, 2, 3, 4],
            dict_field={'ultimate_answer': 42, 'funny_number': 69},
            dataclass_list=[a1, a2],
            dataclass_dict={'pi': a1, 'e': a2}
        )

        a_containers_of_dataclasses2 = AContainerDataclass(
            int_field=1,
            float_field=pi,
            list_field=[5, 6, 7, 8],
            dict_field={'oceans_friends': 13, 'inches_in_feet': 12},
            dataclass_list=[a3, a4],
            dataclass_dict={'tau': a3, 'phi': a4}
        )

        a = AContainerRecurseDataclass(
            dataclass_dict_recursive={
                'first': a_containers_of_dataclasses1,
                'second': a_containers_of_dataclasses2
            },
            dataclass_list_recursive=[
                a_containers_of_dataclasses1,
                a_containers_of_dataclasses2
            ]
        )
        assert TestPackable.assert_pack_unpack(a)
