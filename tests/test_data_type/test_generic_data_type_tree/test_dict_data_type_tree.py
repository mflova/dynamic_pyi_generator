from typing import Any, Callable, Dict, Final, Iterable

import pytest

from dynamic_pyi_generator.data_type_tree import data_type_tree_factory
from dynamic_pyi_generator.data_type_tree.generic_type import DictDataTypeTree, MappingDataTypeTree
from dynamic_pyi_generator.file_modifiers.yaml_file_modifier import YamlFileModifier
from dynamic_pyi_generator.strategies import ParsingStrategies
from dynamic_pyi_generator.utils import TAB


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

    @pytest.mark.parametrize(
        "tree, expected_output, expected_n_childs",
        [
            (
                DictDataTypeTree(
                    {"name": "Joan"}, name=NAME, strategies=ParsingStrategies(min_height_to_define_type_alias=0)
                ),
                f"""class {NAME}(TypedDict):
{TAB}name: str""",
                1,
            ),
            (
                DictDataTypeTree(
                    {"age": 22}, name=NAME, strategies=ParsingStrategies(min_height_to_define_type_alias=0)
                ),
                f"""class {NAME}(TypedDict):
{TAB}age: int""",
                1,
            ),
            (
                DictDataTypeTree(
                    {"name": "Joan", "age": 21},
                    name=NAME,
                    strategies=ParsingStrategies(min_height_to_define_type_alias=0),
                ),
                f"""class {NAME}(TypedDict):
{TAB}name: str
{TAB}age: int""",
                2,
            ),
            (
                DictDataTypeTree(
                    {"name": "Joan", "kids": ["A", "B"]},
                    name=NAME,
                    strategies=ParsingStrategies(min_height_to_define_type_alias=0),
                ),
                f"""class {NAME}(TypedDict):
{TAB}name: str
{TAB}kids: {NAME}Kids""",
                2,
            ),
            (
                DictDataTypeTree(
                    {"name": "Joan", "kids": ["A", "B"], "parents": ["C", "D"]},
                    name=NAME,
                    strategies=ParsingStrategies(min_height_to_define_type_alias=0),
                ),
                f"""class {NAME}(TypedDict):
{TAB}name: str
{TAB}kids: {NAME}Kids
{TAB}parents: {NAME}Parents""",
                3,
            ),
        ],
    )
    def test_get_str_typed_dict_py(
        self,
        tree: DictDataTypeTree,
        expected_output: str,
        expected_n_childs: int,
        assert_imports: Callable[[DictDataTypeTree, Iterable[str]], None],
    ) -> None:
        """
        Test the `get_str_py` method of the `DictDataTypeTree` class.

        Args:
            tree (TupleDataTypeTree): An instance of the `TupleDataTypeTree` class.
            expected_output (str): The expected output string.
            expected_n_childs (int): The expected number of child nodes in the tree.
            assert_imports (Callable[[TupleDataTypeTree, Iterable[str]], None]): A callable that asserts the imports.
        """
        assert expected_n_childs == len(tree), "Not all childs were correctly parsed"
        assert expected_output == tree.get_str_top_node()
        assert_imports(tree, self.imports_to_check)

    @pytest.mark.parametrize(
        "tree, expected_output, expected_n_childs",
        [
            (
                DictDataTypeTree(
                    {"name and surname": "Joan B."},
                    name=NAME,
                    strategies=ParsingStrategies(min_height_to_define_type_alias=0),
                ),
                f"""{NAME} = TypedDict(
    "{NAME}",
    {{
        "name and surname": str,
    }},
)""",
                1,
            ),
            (
                DictDataTypeTree(
                    {"$": 22.0, "own_list": [1, 2, 3]},
                    name=NAME,
                    strategies=ParsingStrategies(min_height_to_define_type_alias=0),
                ),
                f"""{NAME} = TypedDict(
    "{NAME}",
    {{
        "$": float,
        "own_list": {NAME}OwnList,
    }},
)""",
                2,
            ),
            (
                DictDataTypeTree(
                    {"$": 22, "my_list": [1, 2, 3], "my_list2": [2, 3]},
                    name=NAME,
                    strategies=ParsingStrategies(min_height_to_define_type_alias=0),
                ),
                f"""{NAME} = TypedDict(
    "{NAME}",
    {{
        "$": int,
        "my_list": {NAME}MyList,
        "my_list2": {NAME}MyList2,
    }},
)""",
                3,
            ),
        ],
    )
    def test_get_str_typed_dict_functional_syntax_py(
        self,
        tree: DictDataTypeTree,
        expected_output: str,
        expected_n_childs: int,
        assert_imports: Callable[[DictDataTypeTree, Iterable[str]], None],
    ) -> None:
        """
        Test the `get_str_py` method of the `DictDataTypeTree` class.

        Args:
            tree (TupleDataTypeTree): An instance of the `TupleDataTypeTree` class.
            expected_output (str): The expected output string.
            expected_n_childs (int): The expected number of child nodes in the tree.
            assert_imports (Callable[[TupleDataTypeTree, Iterable[str]], None]): A callable that asserts the imports.
        """
        assert expected_n_childs == len(tree), "Not all childs were correctly parsed"
        assert expected_output == tree.get_str_top_node()
        assert_imports(tree, self.imports_to_check)


class TestGetStrHeight:
    NAME: Final = "Example"
    """Name that will be used to create the class."""
    imports_to_check: Final = ("Mapping", "Any", "dict", "TypedDict", "MappingProxyType")
    """Imports that will be checked in case they were needed."""

    @pytest.mark.parametrize(
        "tree, expected_output",
        [
            (
                DictDataTypeTree(
                    {"name": "Joan", "kids": ["A", "B"]},
                    name=NAME,
                    strategies=ParsingStrategies(min_height_to_define_type_alias=0),
                ),
                f"""class {NAME}(TypedDict):
{TAB}name: str
{TAB}kids: {NAME}Kids""",
            ),
            (
                DictDataTypeTree(
                    {"name": "Joan", "kids": ["A", "B"]},
                    name=NAME,
                    strategies=ParsingStrategies(min_height_to_define_type_alias=1),
                ),
                f"""class {NAME}(TypedDict):
{TAB}name: str
{TAB}kids: List[str]""",
            ),
        ],
    )
    def test_get_str_py_based_on_height(
        self,
        tree: DictDataTypeTree,
        expected_output: str,
    ) -> None:
        """
        Test the `get_str_py` method of the `DictDataTypeTree` class.

        Args:
            tree (TupleDataTypeTree): An instance of the `TupleDataTypeTree` class.
            expected_output (str): The expected output string.
            expected_n_childs (int): The expected number of child nodes in the tree.
            assert_imports (Callable[[TupleDataTypeTree, Iterable[str]], None]): A callable that asserts the imports.
        """
        assert expected_output == tree.get_str_top_node()

    @pytest.mark.parametrize(
        "data, min_height, expected_output",
        [
            ([2, {"name": "Joan", "kids": ["A", "B"]}], 0, f"{NAME} = List[Union[ExampleDict, int]]"),
            ([2, {"name": "Joan", "kids": ["A", "B"]}], 1, f"{NAME} = List[Union[ExampleDict, int]]"),
            ([2, {"name": "Joan", "kids": ["A", "B"]}], 2, f"{NAME} = List[Union[ExampleDict, int]]"),
        ],
    )
    def test_permissions(self, data: object, min_height: int, expected_output: str) -> None:
        error = "No matter the minimum height set up, `TypedDict` should always have preference"
        tree = data_type_tree_factory(
            data, name=self.NAME, strategies=ParsingStrategies(min_height_to_define_type_alias=min_height)
        )
        assert expected_output == tree.get_str_top_node(), error


class TestClassDocstringFromKey:
    NAME: Final = "Example"

    @pytest.mark.parametrize(
        "tree, expected_output",
        [
            (
                DictDataTypeTree(
                    data={"name": "Joan", "doc": "This is a docstring"},
                    name=NAME,
                    strategies=ParsingStrategies(dict_strategy="TypedDict", key_used_as_doc="doc"),
                ),
                f'''class {NAME}(TypedDict):
{TAB}"""This is a docstring."""

{TAB}name: str
{TAB}doc: str''',
            ),
            (
                DictDataTypeTree(
                    data={"name": "Joan", "doc": "This is a docstring"},
                    name=NAME,
                    strategies=ParsingStrategies(dict_strategy="TypedDict", key_used_as_doc="doc2"),
                ),
                f"""class {NAME}(TypedDict):
{TAB}name: str
{TAB}doc: str""",
            ),
        ],
    )
    def test_docstring_is_created(self, tree: DictDataTypeTree, expected_output: str) -> None:
        assert expected_output == tree.get_str_top_node()

    @pytest.mark.parametrize(
        "tree, expected_last_line",
        [
            (
                DictDataTypeTree(
                    data={"full name": "Joan", "doc": "This is a docstring"},
                    name=NAME,
                    strategies=ParsingStrategies(dict_strategy="TypedDict", key_used_as_doc="doc"),
                ),
                '''"""This is a docstring."""''',
            ),
            (
                DictDataTypeTree(
                    data={"full name": "Joan", "doc": "This is a docstring"},
                    name=NAME,
                    strategies=ParsingStrategies(dict_strategy="TypedDict", key_used_as_doc="doc2"),
                ),
                "",
            ),
        ],
    )
    def test_docstring_is_created_in_functional_syntax(self, tree: DictDataTypeTree, expected_last_line: str) -> None:
        if expected_last_line:
            assert expected_last_line == tree.get_str_top_node().splitlines()[-1]
        else:
            assert '""""' not in tree.get_str_top_node().splitlines()[-1]


class TestKeyDocstring:
    NAME: Final = "Example"
    PREFFIX: Final = YamlFileModifier.preffix

    @pytest.mark.parametrize(
        "tree, expected_output",
        [
            (
                DictDataTypeTree(
                    data={"name": "Joan", "age": 22, f"{PREFFIX}name": "This is name doc"},
                    name=NAME,
                    strategies=ParsingStrategies(dict_strategy="TypedDict", key_used_as_doc="doc"),
                ),
                f'''class {NAME}(TypedDict):
{TAB}name: str
{TAB}"""This is name doc."""
{TAB}age: int''',
            ),
            (
                DictDataTypeTree(
                    data={"name": "Joan", "age": 22, f"{PREFFIX}age": "This is age doc"},
                    name=NAME,
                    strategies=ParsingStrategies(dict_strategy="TypedDict", key_used_as_doc="doc"),
                ),
                f'''class {NAME}(TypedDict):
{TAB}name: str
{TAB}age: int
{TAB}"""This is age doc."""''',
            ),
            (
                DictDataTypeTree(
                    data={
                        "name": "Joan",
                        "age": 22,
                        f"{PREFFIX}age": "This is age doc",
                        f"{PREFFIX}name": "This is name doc",
                    },
                    name=NAME,
                    strategies=ParsingStrategies(dict_strategy="TypedDict", key_used_as_doc="doc"),
                ),
                f'''class {NAME}(TypedDict):
{TAB}name: str
{TAB}"""This is name doc."""
{TAB}age: int
{TAB}"""This is age doc."""''',
            ),
        ],
    )
    def test_key_docstring_is_created(self, tree: DictDataTypeTree, expected_output: str) -> None:
        assert expected_output == tree.get_str_top_node()

    def test_key_docstring_is_not_created_in_functional_syntax(self) -> None:
        key_docstring = "This is a key doc"
        tree = DictDataTypeTree(
            data={"full name": "Joan", "doc": "This is a docstring", f"{self.PREFFIX}full name": key_docstring},
            name=self.NAME,
            strategies=ParsingStrategies(dict_strategy="TypedDict", key_used_as_doc="doc"),
        )
        assert key_docstring not in tree.get_str_top_node().splitlines()

    @pytest.mark.parametrize(
        "data1, data2, expected_same_hash",
        [
            ({"name": "Joan", f"{PREFFIX}name": "This is a doc"}, {"name": "Joan"}, True),
            ({"age": 22, f"{PREFFIX}age": "This is a doc"}, {"age": 23}, True),
            ({"age": 22, f"{PREFFIX}age": "This is a doc"}, {"age": "22"}, False),
        ],
    )
    def test_hidden_key_docs_do_not_change_hash(
        self, data1: Dict[Any, Any], data2: Dict[Any, Any], expected_same_hash: bool
    ) -> None:
        tree1 = DictDataTypeTree(data1, name="Tree1")
        tree2 = DictDataTypeTree(data2, name="Tree2")
        assert expected_same_hash == (hash(tree1) == hash(tree2))
