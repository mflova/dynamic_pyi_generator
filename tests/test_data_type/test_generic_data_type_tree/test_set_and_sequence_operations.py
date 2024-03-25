from types import MappingProxyType
from typing import Any, Callable, Dict, Final, Iterable, Mapping, Optional, Sequence, Set, Union

import pytest

from dynamic_pyi_generator.data_type_tree.data_type_tree import DataTypeTree
from dynamic_pyi_generator.data_type_tree.factory import data_type_tree_factory
from dynamic_pyi_generator.data_type_tree.generic_type import DictDataTypeTree, MappingDataTypeTree
from dynamic_pyi_generator.data_type_tree.generic_type.set_and_sequence_operations import (
    SetAndSequenceOperations,
)
from dynamic_pyi_generator.file_modifiers.yaml_file_modifier import YamlFileModifier
from dynamic_pyi_generator.strategies import ParsingStrategies
from dynamic_pyi_generator.utils import TAB


class TestTransferHiddenKeys:
    PREFFIX: Final = DictDataTypeTree.hidden_keys_preffix

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
