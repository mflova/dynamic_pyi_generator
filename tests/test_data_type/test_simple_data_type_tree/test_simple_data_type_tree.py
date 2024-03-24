from typing import Final

import pytest

from dynamic_pyi_generator.data_type_tree.simple_data_type_tree import SimpleDataTypeTree


class TestGetStrPy:
    NAME: Final = "Example"

    @pytest.mark.parametrize(
        "data, expected_str",
        [
            [range(1, 2), f"{NAME} = range"],
            [slice(1, 2), f"{NAME} = slice"],
            [True, f"{NAME} = bool"],
            [False, f"{NAME} = bool"],
            ["random_string", f"{NAME} = str"],
            [5, f"{NAME} = int"],
            [6.7, f"{NAME} = float"],
        ],
    )
    def test_get_str_py(self, data: object, expected_str: str) -> None:
        data_type_tree = SimpleDataTypeTree(data, self.NAME)
        assert expected_str == data_type_tree.get_str_top_node()

    def test_none(self) -> None:
        data_type_tree = SimpleDataTypeTree(None, self.NAME)
        assert f"{self.NAME} = Optional[object]" == data_type_tree.get_str_top_node()
        assert "Optional" in data_type_tree.imports._set


class TestHash:
    NAME: Final = "Example"

    @pytest.mark.parametrize(
        "tree1, tree2, expected_output",
        [
            [SimpleDataTypeTree(range(3, 4), name="Data1"), SimpleDataTypeTree(range(1, 2), name="Data2"), True],
            [SimpleDataTypeTree(slice(3, 4), name="Data1"), SimpleDataTypeTree(slice(1, 2), name="Data2"), True],
            [SimpleDataTypeTree(True, name="Data1"), SimpleDataTypeTree(True, name="Data2"), True],
            [SimpleDataTypeTree(False, name="Data1"), SimpleDataTypeTree(True, name="Data2"), True],
            [SimpleDataTypeTree(False, name="Data1"), SimpleDataTypeTree(False, name="Data2"), True],
            [SimpleDataTypeTree("string1", name="Data1"), SimpleDataTypeTree("string2", name="Data2"), True],
            [SimpleDataTypeTree(5, name="Data1"), SimpleDataTypeTree(7, name="Data2"), True],
            [SimpleDataTypeTree(5.2, name="Data1"), SimpleDataTypeTree(7.1, name="Data2"), True],
            [SimpleDataTypeTree(range(1, 2), name="Data1"), SimpleDataTypeTree(7, name="Data1"), False],
            [SimpleDataTypeTree(range(1, 2), name="Data1"), SimpleDataTypeTree(slice(2.7), name="Data1"), False],
            [SimpleDataTypeTree(5.2, name="Data1"), SimpleDataTypeTree("str", name="Data2"), False],
        ],
    )
    def test_get_str_py(self, tree1: SimpleDataTypeTree, tree2: SimpleDataTypeTree, expected_output: bool) -> None:
        assert expected_output == (hash(tree1) == hash(tree2))
