from types import MappingProxyType
from typing import Any, Callable, Dict, Final, Iterable, Mapping, Optional, Sequence, Set, Union

import pytest

from dynamic_pyi_generator.data_type_tree.data_type_tree import DataTypeTree
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
        assert expected_output_info == SetAndSequenceOperations._get_key_info_from_its_typed_dict_childs(tree)


class TestTransferHiddenKeys:
    PREFFIX: Final = DictDataTypeTree.hidden_keys_preffix

    @pytest.mark.parametrize(
        "data1, data2, expected_dict",
        [
            (
                {"name": "Joan"},
                {"name": "Joan"},
                {"name": "Joan"},
            ),
            (
                {"name": "Joan"},
                {"name": "Joan", "age": 22},
                {"name": "Joan"},
            ),
            (
                {"name": "Joan", "age": 22},
                {"name": "Joan"},
                {"name": "Joan", "age": 22},
            ),
            (
                {"name": "Joan", f"{PREFFIX}name": "This is a docstring"},
                {"name": "Joan"},
                {"name": "Joan", f"{PREFFIX}name": "This is a docstring"},
            ),
            (
                {"name": "Joan"},
                {"name": "Joan", f"{PREFFIX}name": "This is a docstring"},
                {"name": "Joan"},
            ),
            (
                {"name": "Joan", f"{PREFFIX}name": "This is a docstring"},
                {"name": "Joan", "age": 22},
                {"name": "Joan", f"{PREFFIX}name": "This is a docstring"},
            ),
            (
                {"name": "Joan", "age": 22},
                {"name": "Joan", f"{PREFFIX}name": "This is a docstring"},
                {"name": "Joan", "age": 22},
            ),
        ],
    )
    def test_method(self, data1: Dict[str, object], data2: Dict[str, object], expected_dict: Dict[str, object]) -> None:
        tree1 = data_type_tree_factory(data1, name="A")
        tree2 = data_type_tree_factory(data1, name="B")
        SetAndSequenceOperations._transfer_hidden_keys(tree1, tree2)
        assert expected_dict == tree2.data

    @pytest.mark.parametrize(
        "tree, expected_dict",
        [
            (
                data_type_tree_factory([{"name": "Joan"}, {"name": "Joan"}], name="A"),
                {"name": "Joan"},
            ),
            (
                data_type_tree_factory([{"name": "Joan"}, {"name": "Joan", f"{PREFFIX}name": "doc"}], name="A"),
                {"name": "Joan", f"{PREFFIX}name": "doc"},
            ),
            (
                data_type_tree_factory([{"name": "Joan", f"{PREFFIX}name": "doc"}, {"name": "Joan"}], name="A"),
                {"name": "Joan", f"{PREFFIX}name": "doc"},
            ),
        ],
    )
    def test_integration(self, tree: DataTypeTree, expected_dict: object) -> None:
        assert len(tree) == 1
        assert expected_dict == next(iter(tree.childs)).data
