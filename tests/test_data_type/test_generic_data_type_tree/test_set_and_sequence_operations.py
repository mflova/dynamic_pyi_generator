from types import MappingProxyType
from typing import Any, Callable, Dict, Final, Iterable, Mapping, Optional, Sequence, Set, Union

import pytest

from dynamic_pyi_generator.data_type_tree import data_type_tree_factory
from dynamic_pyi_generator.data_type_tree.factory import data_type_tree_factory
from dynamic_pyi_generator.data_type_tree.generic_type import DictDataTypeTree, MappingDataTypeTree
from dynamic_pyi_generator.data_type_tree.generic_type.set_and_sequence_operations import (
    MultipleTypedDictsInfo,
    SetAndSequenceOperations,
)
from dynamic_pyi_generator.file_modifiers.yaml_file_modifier import YamlFileModifier
from dynamic_pyi_generator.strategies import ParsingStrategies
from dynamic_pyi_generator.utils import TAB


class TestGetTypedDictInfoFromChilds:
    @pytest.mark.parametrize(
        "data, expected_output_info, strategies",
        [
            (
                [1, 2, 3],
                None,
                ParsingStrategies(dict_strategy="TypedDict"),
            ),
            (
                [1, 2, {"age": 22}],
                None,
                ParsingStrategies(dict_strategy="TypedDict"),
            ),
            (
                [1, MappingProxyType({"age": 22}), MappingProxyType({"age": 22})],
                None,
                ParsingStrategies(dict_strategy="TypedDict"),
            ),
            (
                [1, {"age": 22}, {"age": 22}],
                None,
                ParsingStrategies(dict_strategy="Mapping"),
            ),
            (
                [1, {"age": 22}, {"age": 22}],
                None,
                ParsingStrategies(dict_strategy="dict"),
            ),
            (
                [1, {"age2": 22}, {"age": 22}],
                MultipleTypedDictsInfo(common_keys=set(), non_common_keys={"age2", "age"}),
                ParsingStrategies(dict_strategy="TypedDict"),
            ),
            (
                [1, {"name": "Joan", "age2": 22}, {"name": "Peter", "age": 22}],
                MultipleTypedDictsInfo(common_keys={"name"}, non_common_keys={"age2", "age"}),
                ParsingStrategies(dict_strategy="TypedDict"),
            ),
        ],
    )
    def test_method(
        self,
        data: Sequence[object],
        expected_output_info: Optional[MultipleTypedDictsInfo],
        strategies: ParsingStrategies,
    ) -> None:
        tree = data_type_tree_factory(data, name="Example", strategies=strategies)
        assert expected_output_info == tree.operations._get_key_info_from_its_typed_dict_childs()
