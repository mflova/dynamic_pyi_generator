import itertools
import subprocess
from collections import defaultdict
from dataclasses import dataclass, fields
from pathlib import Path
from typing import (
    Callable,
    Final,
    Iterable,
    List,
    Mapping,
    Set,
    get_args,
    get_type_hints,
)

import pytest

from dynamic_pyi_generator.data_type_tree import DataTypeTree, data_type_tree_factory
from dynamic_pyi_generator.strategies import ParsingStrategies
from dynamic_pyi_generator.utils import TAB, check_if_command_available


@dataclass(frozen=True)
class StrategiesTesting(ParsingStrategies):
    @classmethod
    def generate_all(cls) -> Iterable[ParsingStrategies]:
        type_hints = get_type_hints(cls)
        input_dict: Mapping[str, List[str]] = defaultdict(list)
        for field in fields(cls):
            for arg in get_args(type_hints[field.name]):
                input_dict[field.name].append(arg)

        # Generate all combinations of values
        for combination in itertools.product(*input_dict.values()):
            for height in range(0, 5):
                yield cls(*combination, min_height_to_define_type_alias=height)  # type: ignore


@pytest.mark.parametrize("strategies", StrategiesTesting.generate_all())
@pytest.mark.parametrize("to_check", ("imports", "strategies"))
def test_all_childs_share(create_sample: Callable[[str], str], strategies: ParsingStrategies, to_check: str) -> None:
    data = create_sample("dictionary")
    tree = data_type_tree_factory(data, strategies=strategies, name="Example")

    parent_object = getattr(tree, to_check)

    def check_objects_are_shared(tree: DataTypeTree) -> None:
        for child in tree:
            assert id(parent_object) == id(getattr(child, to_check)), f"Not all childs are sharing same {to_check}"
            check_objects_are_shared(child)

    check_objects_are_shared(tree)


class TestIntegration:
    test_files: Final = ("dictionary.py", "list.py", "set.py")
    test_files_dir: Final = Path(__file__).parent / "test_files"

    @pytest.mark.skipif(
        not check_if_command_available("python"), reason="Python must be available within the terminal."
    )
    @pytest.mark.parametrize("strategies", StrategiesTesting.generate_all())
    @pytest.mark.parametrize("data_type", ["frozenset", "set", "list", "tuple", "dictionary", "mapping"])
    def test_integration(
        self, strategies: ParsingStrategies, create_sample: Callable[[str], str], data_type: str, tmp_path: str
    ) -> None:
        data = create_sample(data_type)
        string = str(
            data_type_tree_factory(data, name="Example", strategies=strategies)._get_strs_all_nodes_unformatted(
                include_imports=True
            )
        )

        self.assert_no_unused_classes(string)
        self.assert_no_redefined_classes(string)
        self.assert_no_double_whitespace(string)
        self.assert_basic_format(string)
        self.assert_no_broken_string_representation(string, tmp_path=tmp_path)
        self.assert_python_38_compatible(string)

    @staticmethod
    def assert_python_38_compatible(string: str) -> None:
        """
        Asserts that the given string is compatible with Python 3.8.

        Args:
            string (str): The string to check for compatibility.
        """
        to_check = ["dict", "list", "set", "tuple"]
        for line in string.splitlines():
            assert all(f"{check}[" not in line for check in to_check)

    @staticmethod
    def assert_no_broken_string_representation(string: str, tmp_path: str) -> None:
        """Compile and call corresponding string representation.

        Not done via `exec()` as this one was presenting an inconsistent behaviour.
        """
        file = "tmp.py"
        full_path_file = Path(tmp_path) / file
        full_path_file.write_text(data=string)
        result = subprocess.run(f"python {full_path_file}", capture_output=True, text=True)

        assert not result.stdout
        assert not result.stderr

    def assert_no_unused_classes(self, string: str) -> None:
        types_defined: Set[str] = set()
        for line in string.splitlines():
            for type_defined in types_defined.copy():
                if type_defined in line:
                    types_defined.remove(type_defined)
            name = self._get_name_type_alias(line)
            if name:
                types_defined.add(name)
        assert len(types_defined) == 1, f"Some classes were created but they are not in use: {', '.join(types_defined)}"

    def assert_no_redefined_classes(self, string: str) -> None:
        all_types_defined: Set[str] = set()
        for line in string.splitlines():
            name = self._get_name_type_alias(line)
            if name:
                if name in all_types_defined:
                    pytest.fail(f"A class/type alias was detected to be redefined: {name}")
                all_types_defined.add(name)

    def assert_no_double_whitespace(self, string: str) -> None:
        for idx, line in enumerate(string.splitlines()):
            if TAB not in line and "  " in line:
                pytest.fail(f"Double whitespaces were detected in line {idx}: {line}")

    def assert_basic_format(self, string: str) -> None:
        strings = string.splitlines()
        for idx, line in enumerate(strings):
            if line.startswith("class"):
                error = "There has to eb exaxctly two empty lines before defining a class."
                assert strings[idx - 1] == "", error
                assert strings[idx - 2] == "", error
                assert strings[idx - 3] != "", error

    @staticmethod
    def _get_name_type_alias(line: str) -> str:
        if "=" in line:
            return line.split("=")[0].strip().rstrip()
        if "(TypedDict)" in line:
            return line.split("(TypedDict)")[0].split(" ")[-1].strip().rstrip()
        return ""


class TestHash:
    # fmt: off
    @pytest.mark.parametrize(
        "data1, data2, strategies, should_be_equal",
        [
            ([1, 2, 3], [4, 5, 6], ParsingStrategies(), True),
            ([1, "str", 3], [4, 5, 6], ParsingStrategies(), False),
            ([1, "str", 3], ["a", 5, 6], ParsingStrategies(), True),
            ([1, {1,2}, 3], [{4,5}, 5, 6], ParsingStrategies(), True),
            ([1, {1,2}, 3], [{4,"a"}, 5, 6], ParsingStrategies(), False),
            ([1, "str", (1, 2)], ["a", 5, (1,)], ParsingStrategies(), False),
            ([1, "str", (1, 2)], ["a", 5, (1,)], ParsingStrategies(tuple_size_strategy="any size"), True),
            ([1, "str", (1, "b")], ["a", 5, (1,)], ParsingStrategies(), False),
            ([1, "str", (1, "b")], ["a", 5, ("c", 1,)], ParsingStrategies(), False),
            ([1, "str", (1, "b")], ["a", 5, ("c", 1,)], ParsingStrategies(tuple_size_strategy="any size"), True),
            ([1, "str", (1, {1,2})], ["a", 5, (1,)], ParsingStrategies(), False),
            # Dicts
            ({"name": "Patrick"}, {"age": "22"}, ParsingStrategies(dict_strategy="dict"), True),
            ({"name": "Patrick"}, {"age": 22}, ParsingStrategies(dict_strategy="dict"), False),
            ({22: 21}, {"age2": 22}, ParsingStrategies(dict_strategy="dict"), False),
            ({22: 21}, {"age2": "name"}, ParsingStrategies(dict_strategy="dict"), False),
            ({22: 21}, {"age2": 22, "age3": "name"}, ParsingStrategies(dict_strategy="dict"), False),
            ({22: 21}, {"age2": 22, "age3": 21}, ParsingStrategies(dict_strategy="dict"), False),
            ({"age1": 21}, {"age2": 22, "age3": 21}, ParsingStrategies(dict_strategy="dict"), True),
            ({"age1": 21, "age4": 16}, {"age2": 22, "age3": 21}, ParsingStrategies(dict_strategy="dict"), True),
            ({"age1": 21, 37: 16}, {"age2": 22, 22: 21}, ParsingStrategies(dict_strategy="TypedDict"), True),
            # TypedDict
            ({"age1": 21, "age2": 16}, {"age2": 22, "age3": 21}, ParsingStrategies(dict_strategy="TypedDict"), False),
            ({"age1": 21, "age2": 16}, {"age1": 22, "age2": 21}, ParsingStrategies(dict_strategy="TypedDict"), True),
            ({"age1": 21, "age2": 16}, {"age1": 22, "age2": "a"}, ParsingStrategies(dict_strategy="TypedDict"), False),
        ],
    )
    # fmt: on
    def test_hash(self, data1: object, data2: object, should_be_equal: bool, strategies: ParsingStrategies) -> None:
        tree1 = data_type_tree_factory(data1, name="Name1", strategies=strategies)
        tree2 = data_type_tree_factory(data2, name="Name2", strategies=strategies)

        assert should_be_equal == (tree1._get_hash() == tree2._get_hash())
        assert should_be_equal == (hash(tree1) == hash(tree2))
