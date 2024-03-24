from contextlib import suppress
from pathlib import Path
from typing import Any, Final, Literal, Mapping, Optional, Sequence, Tuple, Union
from unittest.mock import patch

import pytest
import yaml
from yaml.parser import ParserError

from dynamic_pyi_generator.file_modifiers.yaml_file_modifier import (
    YAML_COMMENTS_POSITION,
    Comment,
    YamlFileModifier,
    YamlFileModifierError,
)
from dynamic_pyi_generator.utils import TAB

THIS_DIR: Final = Path(__file__).parent
TEST_FILES_DIR: Final = THIS_DIR / "test_files"


class TestExceptions:
    def test_wrong_inputs(self) -> None:
        with pytest.raises(YamlFileModifierError):
            YamlFileModifier("", comments_are=["above", "below"])

    def test_wrong_extension(self) -> None:
        with pytest.raises(YamlFileModifierError), suppress(FileNotFoundError):
            YamlFileModifier("file.py", comments_are="above")

    @pytest.mark.parametrize("extension", [".yaml", ".yml"])
    @pytest.mark.parametrize(
        "file_path",
        [
            "file{extension}",
            "/file{extension}",
            "folder/file{extension}",
            "/folder/file{extension}",
            "C:/folder/file{extension}",
        ],
    )
    def test_correct_extension(self, file_path: str, extension: str) -> None:
        with patch("pathlib.Path.read_text", autospec=True) as mock_read:

            def read_text_side_effect(self: Path, *args: Any, **kwargs: Any) -> str:  # noqa: ARG001
                return ""

            mock_read.side_effect = read_text_side_effect
            YamlFileModifier(file_path.format(extension=extension), comments_are="above")


class TestCapitalizeOnlyFirstLetter:
    @pytest.mark.parametrize(
        "string, expected_output",
        [
            ("", ""),
            (" ", " "),
            ("hey", "Hey"),
            ("Hey", "Hey"),
            ("Hey Joan", "Hey Joan"),
            ("Hey joan", "Hey joan"),
        ],
    )
    def test_wrong_inputs(self, string: str, expected_output: str) -> None:
        assert expected_output == YamlFileModifier._capitalize_only_first_letter(string)


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
        assert expected_output == YamlFileModifier._remove_spacing(line)


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
        assert expected_output == YamlFileModifier._find_first_occurence_that_is_not_between(
            line, occurence=occurence, not_between=frozenset({"'", '"'})
        )


class TestExtractKeyFromLine:
    @pytest.mark.parametrize("separator", (TAB, "\t", ""))
    @pytest.mark.parametrize(
        "line, expected_output",
        [
            ("{separator}key: text", "key"),
            ("{separator}- key: text", "key"),  # From list
            ("{separator}-key: text", "key"),  # From list
            ("{separator}-'key': text", "key"),  # From list
            ("{separator}- 'key': text", "key"),  # From list
            ('{separator}"key": text', "key"),
            ("{separator}key_1: text", "key_1"),
            ("{separator}key 1: text", "key 1"),
            ('{separator}"key:1": text', "key:1"),
            ('{separator}"key1" text', ""),
        ],
    )
    def test_method(self, line: str, expected_output: str, separator: str) -> None:
        assert expected_output == YamlFileModifier._extract_key_from_line(line.format(separator=separator))


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
        assert expected_output == YamlFileModifier._join_multi_line_comments(lines)


class TestCountSpacesOrTabs:
    @pytest.mark.parametrize(
        "line, indentation, expected_output",
        [
            ("key: text", "spaces", 0),
            (" key: text", "spaces", 1),
            ("  key: text", "spaces", 2),
            ("   key: text", "spaces", 3),
            ("\tkey: text", "tabs", 1),
            ("\t\tkey: text", "tabs", 2),
            ("\t\t\tkey: text", "tabs", 3),
            ("-key: text", "spaces", 1),  # From list
            ("- key: text", "spaces", 2),  # From list
            (" - key: text", "spaces", 3),  # From list
        ],
    )
    def test_method(self, line: str, expected_output: int, indentation: Literal["spaces", "tabs"]) -> None:
        assert expected_output == YamlFileModifier._count_spaces_or_tabs_at_start(line, indendation=indentation)


class TestExtractSideComment:
    @pytest.mark.parametrize(
        "line, expected_output",
        [
            ("key: text# comment", ""),
            ("key: text #", ""),
            ("key: text # ", ""),
            ("key: text #  ", ""),
            ("key: text # comment", "comment."),
            ("key: text # Comment", "Comment."),
            ("key: text #  Comment", "Comment."),
            ("key: text #Comment", "Comment."),
            ("key: text # comment\n", "comment."),
            ("key: '#' # comment", "comment."),
            ("""key: '#" # comment""", "comment."),
            ('key: "#" # comment', "comment."),
            ('key: "#"', ""),
            ("key: text", ""),
        ],
    )
    def test_method(self, line: str, expected_output: str) -> None:
        assert expected_output == YamlFileModifier._extract_side_comment(line)


class TestExtractSingleBlockComments:
    @pytest.fixture
    def data_file_modifier(self, content: str, comments_are: Literal["above", "below"]) -> YamlFileModifier:
        with patch("pathlib.Path.read_text", autospec=True) as mock_read:

            def read_text_side_effect(self: Path, *args: Any, **kwargs: Any) -> str:  # noqa: ARG001
                return content

            mock_read.side_effect = read_text_side_effect
            return YamlFileModifier(path="file.yaml", comments_are=comments_are)

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
                """'key': comment
# This is a comment""",
                "below",
                0,
                "This is a comment.",
            ),
            (
                """"key": comment
# This is a comment""",
                "below",
                0,
                "This is a comment.",
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
            (
                """- key: comment
  # This is a comment
""",
                "below",
                0,
                "This is a comment.",
            ),
            (
                """- key: comment
  key2: comment
  # This is a comment
""",
                "below",
                1,
                "This is a comment.",
            ),
            (
                """- key
  # This is a comment
""",
                "below",
                0,
                "",
            ),
            (
                """- 'key':
  # This is a comment
""",
                "below",
                0,
                "This is a comment.",
            ),
        ],
    )
    def test_method(
        self,
        line_idx: int,
        expected_output: str,
        data_file_modifier: YamlFileModifier,
        comments_are: Literal["above", "below"],
    ) -> None:
        assert expected_output == data_file_modifier._extract_single_block_comment(line_idx, comments_are=comments_are)


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
                        spacing_element=("spaces", 0),
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
                (
                    Comment(
                        full_string="Doc for level1.",
                        associated_with_key="level1",
                        key_line=1,
                        spacing_element=("spaces", 0),
                    ),
                    Comment(
                        full_string="Doc for key1.",
                        associated_with_key="key1",
                        key_line=3,
                        spacing_element=("spaces", 2),
                    ),
                    Comment(
                        full_string="Multi line comment for level2.",
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
            ),
            (
                "only_dicts_comments_side.yaml",
                "side",
                (
                    Comment(
                        full_string="doc for level1.",
                        associated_with_key="level1",
                        key_line=1,
                        spacing_element=("spaces", 0),
                    ),
                    Comment(
                        full_string="doc for key1.",
                        associated_with_key="key1",
                        key_line=2,
                        spacing_element=("spaces", 2),
                    ),
                    Comment(
                        full_string="comment for level2.",
                        associated_with_key="level2",
                        key_line=4,
                        spacing_element=("spaces", 2),
                    ),
                    Comment(
                        full_string="comment for key3.",
                        associated_with_key="key3",
                        key_line=5,
                        spacing_element=("spaces", 4),
                    ),
                ),
            ),
            (
                "full_yaml_comments_above_and_side.yaml",
                "above",
                (
                    (
                        Comment(
                            full_string="Comment for level1.",
                            associated_with_key="level1",
                            key_line=2,
                            spacing_element=("spaces", 0),
                        ),
                        Comment(
                            full_string="Comment for list1.",
                            associated_with_key="list1",
                            key_line=4,
                            spacing_element=("spaces", 2),
                        ),
                        Comment(
                            full_string="Comment for subkey1.",
                            associated_with_key="subkey1",
                            key_line=12,
                            spacing_element=("spaces", 8),
                        ),
                    )
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
        data_file_modifier = YamlFileModifier(TEST_FILES_DIR / file, comments_are=comments_are)
        assert expected_output == data_file_modifier._extract_comments()


class TestMergeComments:
    @pytest.mark.parametrize(
        "comments, expected_output",
        [
            [
                (
                    Comment(
                        full_string="Comment for key1.",
                        associated_with_key="key1",
                        key_line=2,
                        spacing_element=("spaces", 0),
                    ),
                    Comment(
                        full_string="Comment 2 for key1.",
                        associated_with_key="key1",
                        key_line=2,
                        spacing_element=("spaces", 0),
                    ),
                ),
                (
                    Comment(
                        full_string="Comment for key1.\n\nComment 2 for key1.",
                        associated_with_key="key1",
                        key_line=2,
                        spacing_element=("spaces", 0),
                    ),
                ),
            ],
            [
                (
                    Comment(
                        full_string="Comment for key1.",
                        associated_with_key="key1",
                        key_line=2,
                        spacing_element=("spaces", 0),
                    ),
                    Comment(
                        full_string="Comment 2 for key1.",
                        associated_with_key="key1",
                        key_line=2,
                        spacing_element=("spaces", 0),
                    ),
                    Comment(
                        full_string="Comment for key2.",
                        associated_with_key="key2",
                        key_line=3,
                        spacing_element=("spaces", 2),
                    ),
                ),
                (
                    Comment(
                        full_string="Comment for key1.\n\nComment 2 for key1.",
                        associated_with_key="key1",
                        key_line=2,
                        spacing_element=("spaces", 0),
                    ),
                    Comment(
                        full_string="Comment for key2.",
                        associated_with_key="key2",
                        key_line=3,
                        spacing_element=("spaces", 2),
                    ),
                ),
            ],
            [
                (
                    Comment(
                        full_string="Comment for key1.",
                        associated_with_key="key1",
                        key_line=2,
                        spacing_element=("spaces", 0),
                    ),
                    Comment(
                        full_string="Comment 2 for key1.",
                        associated_with_key="key1",
                        key_line=2,
                        spacing_element=("spaces", 0),
                    ),
                    Comment(
                        full_string="Comment for key2.",
                        associated_with_key="key2",
                        key_line=3,
                        spacing_element=("spaces", 2),
                    ),
                    Comment(
                        full_string="Comment 2 for key2.",
                        associated_with_key="key2",
                        key_line=3,
                        spacing_element=("spaces", 2),
                    ),
                ),
                (
                    Comment(
                        full_string="Comment for key1.\n\nComment 2 for key1.",
                        associated_with_key="key1",
                        key_line=2,
                        spacing_element=("spaces", 0),
                    ),
                    Comment(
                        full_string="Comment for key2.\n\nComment 2 for key2.",
                        associated_with_key="key2",
                        key_line=3,
                        spacing_element=("spaces", 2),
                    ),
                ),
            ],
        ],
    )
    def test_method(self, comments: Sequence[Comment], expected_output: Sequence[Comment]) -> None:
        assert expected_output == YamlFileModifier._merge_comments(comments)


class TestIntegration:
    TEST_FILE: Final = TEST_FILES_DIR / "example.yaml"
    PREFIX: Final = YamlFileModifier.preffix

    @pytest.mark.parametrize(
        "file, comments_are, dict_to_be_created",
        [
            (
                "only_dicts_comments_above.yaml",
                "above",
                {
                    f"{PREFIX}level1": "Doc for level1.\n",
                    "level1": {
                        f"{PREFIX}key1": "Doc for key1.\n",
                        f"{PREFIX}level2": "Multi line comment for level2.\n",
                        "key1": "value1",
                        "key2": "value2",
                        "level2": {
                            f"{PREFIX}key3": "This is key3\n\nIt is just an example.\n",
                            "key3": "value3",
                            "key4": "value4",
                            "level3": {"key5": "value5", "key6": "value6"},
                        },
                    },
                },
            ),
            (
                "only_dicts_comments_below.yaml",
                "below",
                {
                    f"{PREFIX}level1": "Doc for level1.\n",
                    "level1": {
                        f"{PREFIX}key1": "Doc for key1.\n",
                        f"{PREFIX}level2": "Multi line comment for level2.\n",
                        "key1": "value1",
                        "key2": "value2",
                        "level2": {
                            f"{PREFIX}key3": "This is key3\n\nIt is just an example.\n",
                            "key3": "value3",
                            "key4": "value4",
                            "level3": {"key5": "value5", "key6": "value6"},
                        },
                    },
                },
            ),
            (
                "full_yaml_comments_above_and_side.yaml",
                "above",
                {
                    f"{PREFIX}level1": "Comment for level1.\n",
                    "level1": {
                        f"{PREFIX}list1": "Comment for list1.\n",
                        "list1": ["item1", "item2", "item3"],
                        "list2": [
                            {
                                "subitem1": {
                                    f"{PREFIX}subkey1": "Comment for subkey1.\n",
                                    "subkey1": "subvalue1",
                                    "subkey2": "subvalue2#Not a comment",
                                },
                            },
                            {"subitem2": {"subkey3": "subvalue3", "subkey4": "subvalue4"}},
                        ],
                    },
                },
            ),
            (
                "full_yaml_comments_above_and_side.yaml",
                "side",
                {
                    "level1": {
                        "list1": ["item1", "item2", "item3"],
                        "list2": [
                            {
                                "subitem1": {
                                    f"{PREFIX}subkey1": "[mm].\n",
                                    "subkey1": "subvalue1",
                                    "subkey2": "subvalue2#Not a comment",
                                },
                            },
                            {"subitem2": {"subkey3": "subvalue3", "subkey4": "subvalue4"}},
                        ],
                    },
                },
            ),
            (
                "full_yaml_comments_above_and_side.yaml",
                ["above", "side"],
                {
                    f"{PREFIX}level1": "Comment for level1.\n",
                    "level1": {
                        f"{PREFIX}list1": "Comment for list1.\n",
                        "list1": ["item1", "item2", "item3"],
                        "list2": [
                            {
                                "subitem1": {
                                    f"{PREFIX}subkey1": "Comment for subkey1.\n\n[mm].\n",
                                    "subkey1": "subvalue1",
                                    "subkey2": "subvalue2#Not a comment",
                                },
                            },
                            {"subitem2": {"subkey3": "subvalue3", "subkey4": "subvalue4"}},
                        ],
                    },
                },
            ),
            (
                "full_yaml_comments_above_and_side.yaml",
                ["side", "above"],
                {
                    f"{PREFIX}level1": "Comment for level1.\n",
                    "level1": {
                        f"{PREFIX}list1": "Comment for list1.\n",
                        "list1": ["item1", "item2", "item3"],
                        "list2": [
                            {
                                "subitem1": {
                                    f"{PREFIX}subkey1": "[mm].\n\nComment for subkey1.\n",
                                    "subkey1": "subvalue1",
                                    "subkey2": "subvalue2#Not a comment",
                                },
                            },
                            {"subitem2": {"subkey3": "subvalue3", "subkey4": "subvalue4"}},
                        ],
                    },
                },
            ),
        ],
    )
    def test_method(
        self, file: str, comments_are: YAML_COMMENTS_POSITION, dict_to_be_created: Mapping[str, object]
    ) -> None:
        data_file_modifier = YamlFileModifier(TEST_FILES_DIR / file, comments_are=comments_are)
        path = data_file_modifier.create_temporary_file_with_comments_as_keys()
        assert dict_to_be_created == self.read_yaml(path)

    def read_yaml(self, path: Union[Path, str]) -> Mapping[str, object]:
        with open(path) as f:
            try:
                return dict(yaml.load(f, Loader=yaml.SafeLoader))
            except ParserError as error:
                pytest.fail(f"Generated yaml file cannot be read: {error}")
