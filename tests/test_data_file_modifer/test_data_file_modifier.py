from pathlib import Path
from typing import Any, Final, Literal, Optional, Sequence, Tuple
from unittest.mock import MagicMock, patch

import pytest

from dynamic_pyi_generator.data_file_modifier.data_file_modifier import Comment, DataFileModifier
from dynamic_pyi_generator.utils import TAB

THIS_DIR: Final = Path(__file__).parent
TEST_FILES_DIR: Final = THIS_DIR / "test_files"


class TestRemoveSpacing:
    @pytest.mark.parametrize(
        "line, expected_output",
        [
            (f"{TAB}This is a line", "This is a line"),
            (f"{TAB}{TAB}This is a line", "This is a line"),
            ("\tThis is a line", "This is a line"),
            ("\t\tThis is a line", "This is a line"),
        ],
    )
    def test_method(self, line: str, expected_output: str) -> None:
        assert expected_output == DataFileModifier._remove_spacing(line)


class TestFindFirstOccurenceThatIsNotBetween:
    @pytest.mark.parametrize(
        "line, occurence, expected_output",
        [
            ("key: text", "j", None),
            ("key: text", " ", 4),
            ("key: text:", ":", 3),
            ("key':' text:", ":", 11),
            ('key":" text:', ":", 11),
        ],
    )
    def test_method(self, line: str, occurence: str, expected_output: Optional[int]) -> None:
        assert expected_output == DataFileModifier._find_first_occurence_that_is_not_between(
            line, occurence=occurence, not_between={"'", '"'}
        )


class TestExtractKeyFromLine:
    @pytest.mark.parametrize("separator", (TAB, "\t", ""))
    @pytest.mark.parametrize(
        "line, expected_output",
        [
            ("{separator}key: text", "key"),
            ('{separator}"key": text', "key"),
            ("{separator}key_1: text", "key_1"),
            ("{separator}key 1: text", "key 1"),
            ('{separator}"key:1": text', "key:1"),
            ('{separator}"key1" text', ""),
        ],
    )
    def test_method(self, line: str, expected_output: str, separator: str) -> None:
        assert expected_output == DataFileModifier._extract_key_from_line(line.format(separator=separator))


class TestJoinMultiLineComments:
    @pytest.mark.parametrize(
        "lines, expected_output",
        [
            (["This is a", " comment"], "This is a comment."),
            (["This is a.", " comment"], "This is a. Comment."),
            (["This is a.", "comment"], "This is a. Comment."),
            (["This is a comment", "This is another"], "This is a comment. This is another."),
            (["This is a comment ", "This is another"], "This is a comment. This is another."),
            (["This is a comment.", "This is another"], "This is a comment. This is another."),
            (["", ""], ""),
            (["", "This is a comment"], "This is a comment."),
            (["This is a comment", ""], "This is a comment."),
            (["This is a comment.", "", "This is another"], "This is a comment.\n\nThis is another."),
            (["This is a comment.", "", "this is another"], "This is a comment.\n\nThis is another."),
            ([], ""),
        ],
    )
    def test_method(self, lines: Sequence[str], expected_output: str) -> None:
        assert expected_output == DataFileModifier._join_multi_line_comments(lines)


class TestCountSpacesOrTabs:
    @pytest.mark.parametrize(
        "line, expected_output",
        [
            ("key: text", ("none", 0)),
            (" key: text", ("spaces", 1)),
            ("  key: text", ("spaces", 2)),
            ("   key: text", ("spaces", 3)),
            ("\tkey: text", ("tabs", 1)),
            ("\t\tkey: text", ("tabs", 2)),
            ("\t\t\tkey: text", ("tabs", 3)),
        ],
    )
    def test_method(self, line: str, expected_output: Tuple[str, int]) -> None:
        assert expected_output == DataFileModifier._count_spaces_or_tabs_at_start(line)


class TestExtractSingleBlockComments:
    @pytest.fixture
    def data_file_modifier(self, content: str, comments_are: Literal["above", "below"]) -> DataFileModifier:
        with patch("pathlib.Path.read_text", autospec=True) as mock_read:

            def read_text_side_effect(self: Path, *args: Any, **kwargs: Any) -> str:
                return content

            mock_read.side_effect = read_text_side_effect
            return DataFileModifier(path="", comments_are=comments_are)

    @pytest.fixture
    def comments_are(self) -> Literal["above", "below"]:
        return "above"

    @pytest.mark.parametrize(
        "content, comments_are, line_idx, expected_output",
        [
            (
                """# This is a single comment
key: comment""",
                "above",
                1,
                "This is a single comment.",
            ),
            (
                """  # This is a single comment
  key: comment""",
                "above",
                1,
                "This is a single comment.",
            ),
            (
                """# This is another comment.
# This is a single comment.
key: comment""",
                "above",
                2,
                "This is another comment. This is a single comment.",
            ),
            (
                """key2: value
    # This is another comment.
# This is a single comment.
key: comment""",
                "above",
                3,
                "This is a single comment.",
            ),
            (
                """key2: value
# This is another comment.
 # This is a single comment.
key: comment""",
                "above",
                3,
                "",
            ),
            (
                """key2: comment
key: comment""",
                "above",
                1,
                "",
            ),
            (
                """key: comment
# My comment""",
                "below",
                0,
                "My comment.",
            ),
            (
                """key: comment
# This is a single comment
# This is another comment""",
                "below",
                0,
                "This is a single comment. This is another comment.",
            ),
            (
                """key: comment
# This is a comment
# that finishes in another line.""",
                "below",
                0,
                "This is a comment that finishes in another line.",
            ),
            (
                """key2: value
# This is another comment.
    # This is a single comment.
key: comment""",
                "below",
                0,
                "This is another comment.",
            ),
            (
                """key2: value
 # This is another comment.
# This is a single comment.
key: comment""",
                "below",
                0,
                "",
            ),
            (
                """key2: value
# This is another comment.
#
# This is a single comment.
key: comment""",
                "below",
                0,
                "This is another comment.\n\nThis is a single comment.",
            ),
            (
                """key2: value
# This is another comment.
# 
# This is a single comment.
key: comment""",
                "below",
                0,
                "This is another comment.\n\nThis is a single comment.",
            ),
            (
                """key2: comment
key: comment""",
                "below",
                0,
                "",
            ),
            (
                """key2: comment
key: comment""",
                "below",
                1,
                "",
            ),
            (
                """key2: comment
key: comment""",
                "below",
                2,
                "",
            ),
        ],
    )
    def test_method(
        self,
        line_idx: int,
        expected_output: str,
        data_file_modifier: DataFileModifier,
        comments_are: Literal["above", "below"],
    ) -> None:
        assert expected_output == data_file_modifier._extract_single_block_comment(line_idx)


class TestExtractComments:
    TEST_FILE: Final = TEST_FILES_DIR / "example.yaml"

    @pytest.mark.parametrize(
        "file, comments_are, expected_output",
        [
            (
                "only_dicts_comments_above.yaml",
                "above",
                (
                    Comment(
                        full_string="Doc for level1.",
                        associated_with_key="level1",
                        key_line=2,
                        spacing_element=("none", 0),
                    ),
                    Comment(
                        full_string="Doc for key1.",
                        associated_with_key="key1",
                        key_line=4,
                        spacing_element=("spaces", 2),
                    ),
                    Comment(
                        full_string="Multi line comment for level2.",
                        associated_with_key="level2",
                        key_line=9,
                        spacing_element=("spaces", 2),
                    ),
                    Comment(
                        full_string="This is key3\n\nIt is just an example.",
                        associated_with_key="key3",
                        key_line=13,
                        spacing_element=("spaces", 4),
                    ),
                ),
            ),
            (
                "only_dicts_comments_below.yaml",
                "below",
                Comment(
                    full_string="doc for level1.",
                    associated_with_key="level1",
                    key_line=2,
                    spacing_element=("none", 0),
                ),
                Comment(
                    full_string="doc for key1.",
                    associated_with_key="key1",
                    key_line=3,
                    spacing_element=("spaces", 2),
                ),
                Comment(
                    full_string="multi line comment for level2.",
                    associated_with_key="level2",
                    key_line=7,
                    spacing_element=("spaces", 2),
                ),
                Comment(
                    full_string="This is key3\n\nIt is just an example.",
                    associated_with_key="key3",
                    key_line=10,
                    spacing_element=("spaces", 4),
                ),
            ),
        ],
    )
    def test_method(
        self,
        file: str,
        comments_are: Literal["above", "below"],
        expected_output: Tuple[Comment, ...],
    ) -> None:
        data_file_modifier = DataFileModifier(TEST_FILES_DIR / file, comments_are=comments_are)
        assert expected_output == data_file_modifier._extract_comments()
