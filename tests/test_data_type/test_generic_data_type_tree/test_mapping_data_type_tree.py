from types import MappingProxyType
from typing import Any, Callable, Final, Iterable, Mapping

import pytest

from dynamic_pyi_generator.data_type_tree.generic_type import DictDataTypeTree, MappingDataTypeTree
from dynamic_pyi_generator.strategies import Strategies


@pytest.mark.parametrize(
    "string, expected_out",
    (
        ["name_age", "NameAge"],
        ["a b", "AB"],
        ["Name$age", "NameAge"],
        ["2Name$age", "NameAge"],
    ),
)
def test_to_camel_case(string: str, expected_out: str) -> None:
    assert expected_out == MappingDataTypeTree._to_camel_case(string)


class TestGetStrPy:
    NAME: Final = "Example"
    """Name that will be used to create the class."""
    imports_to_check: Final = ("Mapping", "Any", "dict", "TypedDict", "MappingProxyType")
    """Imports that will be checked in case they were needed."""

    # fmt: off
    @pytest.mark.parametrize(
        "strategies",
        [
            (Strategies(dict_strategy="dict", min_height_to_define_type_alias=0)),
            (Strategies(dict_strategy="Mapping", min_height_to_define_type_alias=0)),
        ],
    )
    @pytest.mark.parametrize(
        "data, expected_output, expected_n_childs",
        [
            ({"name": "Joan"}, f"{NAME} = {{expected_container}}[str, str]", 1),
            ({"age": 22}, f"{NAME} = {{expected_container}}[str, int]", 1),
            ({"name": "Joan", "age": 22}, f"{NAME} = {{expected_container}}[str, Union[int, str]]", 2),
            ({"name": "Joan", 21: 22}, f"{NAME} = {{expected_container}}[Union[int, str], Union[int, str]]", 2),
            ({22: "Joan", 21.2: 22}, f"{NAME} = {{expected_container}}[float, Union[int, str]]", 2),
            ({22: "Joan", 21.2: "number"}, f"{NAME} = {{expected_container}}[float, str]", 2),
            ({}, f"{NAME} = {{expected_container}}[Any, Any]", 0),
            (MappingProxyType({"name": "Joan"}), f"{NAME} = MappingProxyType[str, str]", 1),
            (MappingProxyType({"age": 22}), f"{NAME} = MappingProxyType[str, int]", 1),
            (MappingProxyType({"name": "Joan", "age": 22}), f"{NAME} = MappingProxyType[str, Union[int, str]]", 2),
            (MappingProxyType({"name": "Joan", 21: 22}), f"{NAME} = MappingProxyType[Union[int, str], Union[int, str]]", 2),
            (MappingProxyType({22: "Joan", 21.2: 22}), f"{NAME} = MappingProxyType[float, Union[int, str]]", 2),
            (MappingProxyType({22: "Joan", 21.2: "number"}), f"{NAME} = MappingProxyType[float, str]", 2),
            (MappingProxyType({}), f"{NAME} = MappingProxyType[Any, Any]", 0),
        ],
    )
    # fmt: on
    def test_get_str_py(
        self,
        data: Mapping[Any, Any],
        expected_output: str,
        expected_n_childs: int,
        strategies: Strategies,
        assert_imports: Callable[[MappingDataTypeTree, Iterable[str]], None],
    ) -> None:
        """
        Test the `get_str_py` method of the `DictDataTypeTree` class.

        Args:
            data (Mapping[Any, Any]): The input data for the test.
            expected_output (str): The expected output string.
            expected_n_childs (int): The expected number of child nodes in the tree.
            strategies (Strategies): The strategies object.
            assert_imports (Callable[[DictDataTypeTree, Iterable[str]], None]): A callable that asserts the imports.
        """
        tree: MappingDataTypeTree
        if isinstance(data, dict):
            tree = DictDataTypeTree(data, name=self.NAME, strategies=strategies)
        else:
            tree = MappingDataTypeTree(data, name=self.NAME, strategies=strategies)

        expected_output = expected_output.format(expected_container=strategies.dict_strategy)
        assert expected_n_childs == len(tree), "Not all childs were correctly parsed"
        assert expected_output == tree.get_str_py()
        assert_imports(tree, self.imports_to_check)


class TestGetAliasHeight:
    NAME: Final = "Example"
    """Name that will be used to create the class."""

    # fmt: off
    @pytest.mark.parametrize(
        "data, min_height, expected_output",
        [
            ({"name": {"unit": "dolar"}}, 0, f"{NAME} = Dict[str, ExampleName]"),
            ({"name": {"unit": "dolar"}}, 1, f"{NAME} = Dict[str, Dict[str, str]]"),
            ({"name": {"unit": "dolar"}}, 2, f"{NAME} = Dict[str, Dict[str, str]]"),
        ],
    )
    # fmt: on
    def test_type_alias_based_on_height(self, data: Mapping[Any, Any], expected_output: str, min_height: int) -> None:
        """
        Test the `get_str_py` method of the `DictDataTypeTree` class.

        Args:
            data (Mapping[Any, Any]): The input data for the test.
            expected_output (str): The expected output string.
            min_height (int): The minimum height to define the type alias.
        """
        tree = DictDataTypeTree(
            data,
            name=self.NAME,
            strategies=Strategies(min_height_to_define_type_alias=min_height, dict_strategy="dict"),
        )
        assert expected_output == tree.get_str_py()
