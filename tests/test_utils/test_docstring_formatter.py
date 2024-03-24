from typing import Tuple

import pytest

from dynamic_pyi_generator.utils.docstring_formatter import _split_string, format_string_as_docstring


@pytest.mark.parametrize(
    "string, max_line_length, expected_result",
    [
        ("This is a test", 90, ("This is a test",)),
        ("This is a test", 10, ("This is a", "test")),
        ("", 90, ("",)),
        ("Thisisatest", 2, ("Thisisatest",)),
        ("Hello\nworld", 90, ("Hello", "world")),
        ("Hello\n\nworld", 90, ("Hello", "", "world")),
        ("This Thisisatest", 6, ("This", "Thisisatest")),
    ],
)
def test_split_string(string: str, expected_result: Tuple[str, ...], max_line_length: int) -> None:
    assert expected_result == _split_string(string, max_line_length=max_line_length)


@pytest.mark.parametrize(
    "string, max_line_length, indentation, expected_result",
    [
        ("This is a test", 21, "", '"""This is a test."""'),
        (
            "This is a test",
            10,
            "",
            '''"""
This is a
test.
"""''',
        ),
        (
            "Thisisatest",
            10,
            "",
            '''"""Thisisatest."""''',
        ),
        (
            "Thisisatest with mix words",
            10,
            "",
            '''"""
Thisisatest
with mix
words.
"""''',
        ),
        (
            "Thisisatest\n",
            10,
            "",
            '''"""Thisisatest."""''',
        ),
        (
            "Hello\nworld\n",
            90,
            "",
            '''"""
Hello
world.
"""''',
        ),
        (
            "Thisisatest with mix words\n",
            10,
            "",
            '''"""
Thisisatest
with mix
words.
"""''',
        ),
        ("This is a test", 21, " ", ' """This is a test."""'),
        (
            "This is a test",
            10,
            " ",
            ''' """
 This is a
 test.
 """''',
        ),
        (
            "Thisisatest",
            10,
            " ",
            ''' """Thisisatest."""''',
        ),
        (
            "Thisisatest with mix words",
            10,
            " ",
            ''' """
 Thisisatest
 with mix
 words.
 """''',
        ),
        (
            "Thisisatest\n",
            10,
            " ",
            ''' """Thisisatest."""''',
        ),
        (
            "Hello\nworld\n",
            90,
            " ",
            ''' """
 Hello
 world.
 """''',
        ),
        (
            "Thisisatest with mix words\n",
            10,
            " ",
            ''' """
 Thisisatest
 with mix
 words.
 """''',
        ),
    ],
)
def test_format_string_as_docstring(string: str, expected_result: str, max_line_length: int, indentation: str) -> None:
    assert expected_result == format_string_as_docstring(
        string, max_line_length=max_line_length, indentation=indentation
    )
