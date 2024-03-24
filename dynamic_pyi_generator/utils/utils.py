import ast
import os
import re
import subprocess
from itertools import zip_longest
from typing import Any, Final, List, Protocol, TypeVar, Union, cast

TAB: Final = "    "


def is_string_python_keyword_compatible(string: str) -> bool:
    """
    Checks if a string is compatible with Python keywords.

    Args:
        string (str): The string to be checked.

    Returns:
        bool: True if the string is compatible with Python keywords, False otherwise.
    """
    if bool(re.compile(r"^[a-zA-Z0-9_]+$").match(string)):
        if not string[0].isnumeric():
            return True
    return False


def compare_ast(
    node1: Union[ast.expr, List[ast.expr], ast.Module],
    node2: Union[ast.expr, List[ast.expr], ast.Module],
    ignore_args: bool = False,
    ignore_imports: bool = False,
) -> bool:
    """Compare two AST nodes for equality."""
    if type(node1) is not type(node2):
        return False

    if isinstance(node1, ast.AST):
        for k, v in vars(node1).items():
            if k in {"lineno", "end_lineno", "col_offset", "end_col_offset", "ctx"}:
                continue
            if ignore_args and k == "args":
                continue
            if ignore_imports and k == "body" and isinstance(v, list):
                v = [n for n in v if not isinstance(n, (ast.Import, ast.ImportFrom))]
                v2 = getattr(node2, k)
                v2 = [n for n in v2 if not isinstance(n, (ast.Import, ast.ImportFrom))]
                setattr(node2, k, v2)
            if not compare_ast(
                v,
                getattr(node2, k),
                ignore_args=ignore_args,
                ignore_imports=ignore_imports,
            ):
                return False
        return True

    elif isinstance(node1, list) and isinstance(node2, list):
        return all(
            compare_ast(n1, n2, ignore_args=ignore_args, ignore_imports=ignore_imports)
            for n1, n2 in zip_longest(node1, node2)
        )
    else:
        return node1 == node2  # type: ignore


def compare_str_via_ast(string1: str, string2: str, /, *, ignore_imports: bool = False) -> bool:
    """
    Compare two strings using the AST (Abstract Syntax Tree) representation.

    Args:
        string1 (str): The first string to compare.
        string2 (str): The second string to compare.
        ignore_imports (bool): Whether to ignore import statements during comparison.

    Returns:
        bool: True if the AST representations of the strings are equal, False otherwise.
    """
    return compare_ast(ast.parse(string1), ast.parse(string2), ignore_imports=ignore_imports)


class _AnyMethodProtocol(Protocol):
    __name__: str

    def __call__(*args: Any, **kwargs: Any) -> Any:
        ...


_AnyMethodT = TypeVar("_AnyMethodT", bound=_AnyMethodProtocol)


def cache_returned_value(method: _AnyMethodT) -> _AnyMethodT:
    """
    A decorator that caches the returned value of a method.

    This decorator can be used to cache the returned value of a method
    to improve performance by avoiding redundant computations.

    Args:
        method: The method to be decorated.

    Returns:
        The decorated method.

    Usage:
        @cache_returned_value
        def my_method(self, args, **kwargs):
            # method implementation

    Example:
        class MyClass:
            @cache_returned_value
            def my_method(self, args, **kwargs):
                # method implementation
    """

    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        cache_attr = f"{method.__name__}____"
        if hasattr(self, cache_attr):
            return getattr(self, cache_attr)
        else:
            result = method(self, *args, **kwargs)
            setattr(self, cache_attr, result)
            return result

    return cast(_AnyMethodT, wrapper)


def check_if_command_available(tool: str) -> bool:
    """
    Check if a command is available.

    Args:
        tool (str): The name of the command to check.

    Returns:
        bool: True if the command is available, False otherwise.
    """
    result = subprocess.run(f"{tool} --help", stdout=open(os.devnull, "wb"), stderr=open(os.devnull, "wb"), shell=True)
    return bool(not result.returncode)
