from dataclasses import dataclass
from typing import Any

import pytest

from dynamic_pyi_generator.utils import (
    cache_returned_value,
    compare_str_via_ast,
    is_string_python_keyword_compatible,
)


class TestCompareAst:
    @dataclass(frozen=True)
    class ParamsTest:
        """
        A class representing the parameters for a test case.

        Attributes:
            string1 (str): The first string parameter.
            string2 (str): The second string parameter.
            ignore_imports (bool): Flag indicating whether to ignore imports.
            expected_output (bool): The expected output of the test case.
        """

        string1: str
        string2: str
        ignore_imports: bool
        expected_output: bool

    @pytest.mark.parametrize(
        "params_test",
        [
            ParamsTest(
                string1="""
# Header
from typing import Sequence

list = Sequence[str]
""",
                string2="""
# Header
from typing import Sequence

list = Sequence[str]
""",
                ignore_imports=False,
                expected_output=True,
            ),
            ParamsTest(
                string1="""
# Header

list = Sequence[str]
""",
                string2="""
# Header
from typing import Sequence

list = Sequence[str]
""",
                ignore_imports=False,
                expected_output=False,
            ),
            ParamsTest(
                string1="""
# Header
from typing import Sequence

list = Sequence[str]

class MyClass(TypedDict):
    my_value: str

    my_num: float
""",
                string2="""
# Header
from typing import Sequence

list = Sequence[str]

class MyClass(TypedDict):
    my_value: str
    my_num: float
""",
                ignore_imports=False,
                expected_output=True,
            ),
            ParamsTest(
                string1="""
# Header
from typing import Sequence

list = Sequence[str]

class MyClass(TypedDict):
    my_value: str
""",
                string2="""
# Header
from typing import Sequence

list = Sequence[str]

class MyClass(TypedDict):
    my_value: str
    my_num: float
""",
                expected_output=False,
                ignore_imports=False,
            ),
            ParamsTest(
                string1="""
# Header
from typing import Sequence

list = Sequence[str]
""",
                string2="""
# Header
from typing import Sequence

list = Sequence[str]
""",
                ignore_imports=True,
                expected_output=True,
            ),
            ParamsTest(
                string1="""
# Header

list = Sequence[str]
""",
                string2="""
# Header
from typing import Sequence

list = Sequence[str]
""",
                ignore_imports=True,
                expected_output=True,
            ),
            ParamsTest(
                string1="""
# Header
from typing import Sequence

list = Sequence[str]

class MyClass(TypedDict):
    my_value: str

    my_num: float
""",
                string2="""
# Header
from typing import Sequence

list = Sequence[str]

class MyClass(TypedDict):
    my_value: str
    my_num: float
""",
                ignore_imports=True,
                expected_output=True,
            ),
            ParamsTest(
                string1="""
# Header
from typing import Sequence

list = Sequence[str]

class MyClass(TypedDict):
    my_value: str
""",
                string2="""
# Header
from typing import Sequence

list = Sequence[str]

class MyClass(TypedDict):
    my_value: str
    my_num: float
""",
                expected_output=False,
                ignore_imports=True,
            ),
        ],
    )
    def test_compare_ast_test(self, params_test: ParamsTest) -> None:
        """
        Test method to compare two strings using AST comparison.

        Args:
            params_test (ParamsTest): An instance of ParamsTest containing
                the test parameters.
        """
        assert params_test.expected_output == compare_str_via_ast(
            params_test.string1,
            params_test.string2,
            ignore_imports=params_test.ignore_imports,
        ), f"{params_test.string1} \n--------\n {params_test.string2}"


@pytest.mark.parametrize(
    "string, expected_output",
    [
        ("build0", True),
        ("bu_ild", True),
        ("_build0", True),
        (".build", False),
        ("bu.ild", False),
        ("bu ild", False),
        ("0build", False),
    ],
)
def test_is_string_python_keyword_compatible(string: str, expected_output: bool) -> None:
    """
    Test function for checking if a string is compatible with Python keywords.

    Args:
        string (str): The string to be checked.
        expected_output (bool): The expected output of the function.

    Returns:
        None: This function does not return anything.

    Raises:
        AssertionError: If the expected output does not match the actual output.
    """
    assert expected_output == is_string_python_keyword_compatible(string)


class TestCacheReturnedValue:
    class DummyClass:
        """Class that will be used for testing purposes."""

        def __init__(self) -> None:
            self.cache_attr = None

        @cache_returned_value
        def dummy_method(self, arg: Any) -> Any:
            self.cache_attr = arg
            return arg

    def test_cache_returned_value(self) -> None:
        dummy_obj = self.DummyClass()

        # Test initial call
        result = dummy_obj.dummy_method(10)
        assert result == 10
        assert dummy_obj.cache_attr == 10

        # Test cached call
        result = dummy_obj.dummy_method(20)
        assert result == 10
        assert dummy_obj.cache_attr == 10
