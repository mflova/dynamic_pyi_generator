"""Tool that allows to read comments from yaml files and re-introduce them as part of the dictionary."""

import re
import tempfile
from collections import defaultdict
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Final,
    FrozenSet,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

YAML_COMMENTS_POSITION = Literal["above", "below", "side"]
"""Possible locations where comments can be written."""


@dataclass(frozen=True)
class Comment:
    """Characterization of a single multi-line comment."""

    full_string: str
    associated_with_key: str
    key_line: int
    spacing_element: Tuple[Literal["spaces", "tabs", "none"], int]


class YamlFileModifierError(Exception):
    ...


class YamlFileModifier:
    path: Path
    """Path where the file lies."""
    lines: Tuple[str, ...]
    """Content of the file parsed as multiple lines."""
    comments_are: Tuple[YAML_COMMENTS_POSITION, ...]
    """Potential location of the comments. Order matters."""
    preffix: Final = "___docstring_hidden_key_"
    """When reading the comments associated with a key, this preffix will be prepended to the key.
    
    This will allow to create a new dictionary mirroring the original one but with new hidden
    keys that capture the comments.
    """

    def __init__(
        self, path: Union[str, Path], *, comments_are: Union[YAML_COMMENTS_POSITION, Sequence[YAML_COMMENTS_POSITION]]
    ) -> None:
        """
        Initialize a YamlFileModifier object.

        Args:
            path (Union[str, Path]): The path to the YAML file.
            comments_are (Union[YAML_COMMENTS_POSITION, Sequence[YAML_COMMENTS_POSITION]]): The position(s) where
                comments are located. If multiple are provided, the order of the sequence will affect how the final
                docstring is built.
        """
        if "above" in comments_are and "below" in comments_are:
            raise YamlFileModifierError(
                f"When choosing where the comments are located, you can choose any combination that does not combine "
                f"`below` and `above` at the same time. Input given: {', '.join(comments_are)}"
            )
        self.path = Path(path)
        if not self.path.suffix.endswith((".yaml", ".yml")):
            raise YamlFileModifierError(f"Only `.yaml` or `.yml` are allowed. File given is: {self.path}")
        self.lines = tuple(Path(path).read_text().splitlines())
        comments_are = (comments_are,) if isinstance(comments_are, str) else tuple(comments_are)
        self.comments_are = comments_are

    @staticmethod
    def _capitalize_only_first_letter(string: str) -> str:
        try:
            return string[0].upper() + string[1:]
        except IndexError:
            return string

    @staticmethod
    def _remove_spacing(line: str) -> str:
        line.strip()
        lines = line.split("\t")
        lines = [line.lstrip() for line in lines]
        return "".join(lines)

    @staticmethod
    def _join_multi_line_comments(lines: Sequence[str]) -> str:
        """
        Joins multiple lines of comments into a single string.

        This one includes the use of `.` and capital letters when needed
        """
        result = ""
        # Remove null strings from both sides of the list until finding first valid string
        lines = list(lines)
        while lines and lines[0] == "":
            lines.pop(0)
        while lines and lines[-1] == "":
            lines.pop()

        if not lines:
            return ""
        for idx, single_line_comment in enumerate(lines):
            if not single_line_comment:
                result += "\n\n"
                continue
            if idx > 0:
                if (
                    single_line_comment and single_line_comment[0].isupper()
                ):  # Check if the string starts with an uppercase letter
                    if result.endswith("."):
                        result += " " + single_line_comment.strip()
                    else:
                        if result.endswith("\n"):
                            single_line_comment_ = single_line_comment.strip()
                            result += YamlFileModifier._capitalize_only_first_letter(single_line_comment_)
                        else:
                            result += ". " + single_line_comment.strip()
                else:
                    single_line_comment_ = single_line_comment.strip()
                    if result.endswith("."):
                        result += " " + YamlFileModifier._capitalize_only_first_letter(single_line_comment_)
                    else:
                        if result.endswith("\n"):
                            single_line_comment_ = single_line_comment.strip()
                            result += YamlFileModifier._capitalize_only_first_letter(single_line_comment_)
                        else:
                            result += " " + single_line_comment.strip()
            else:
                result += single_line_comment.strip()
        if not result:
            return result
        if result.endswith("."):
            return result
        return result + "."

    @staticmethod
    def _extract_side_comment(line: str) -> str:
        """
        Extracts the side comment from a given line of text.

        Example:
            yaml_key: value  # My comment
        """
        idx = YamlFileModifier._find_first_occurence_that_is_not_between(line, "#")
        if not idx:
            return ""
        try:
            if line[idx - 1] != " ":
                return ""
        except IndexError:
            return ""
        comment = line[idx + 1 :].strip().rstrip()
        if comment and not comment.endswith("."):
            return comment + "."
        return comment

    def _extract_single_block_comment(self, line_idx: int, *, comments_are: Literal["above", "below"]) -> str:
        """
        Extracts a single block comment from the specified line index.

        It is important that the comment is perfectly aligned with the key that is commenting.
        It also merges multiple lines.
        Only comments attached to dictionary keys will be returned.

        Example:
            # Comment above
            key: value
            # Comment below
            # that can be multiple lines

        Args:
            line_idx (int): The index of the line to extract the comment from.
            comments_are (Literal["above", "below"]): Specifies whether the comments are located above
                or below the line.
        """
        # Find first non space/tab character
        try:
            line = self.lines[line_idx]
        except IndexError:
            return ""
        if not self._find_first_occurence_that_is_not_between(line, ":"):
            return ""
        idx_first_char = line.find(line.strip().replace("-", "").strip()[0])

        step: Final = -1 if comments_are == "above" else 1
        increment = step
        multi_line_comments: List[str] = []
        with suppress(IndexError):
            while self.lines[line_idx + increment][idx_first_char] == "#":
                multi_line_comments.append(self.lines[line_idx + increment][idx_first_char + 1 :].strip())
                increment += step

        if not multi_line_comments:
            return ""

        if comments_are == "above":
            string = self._join_multi_line_comments(multi_line_comments[::-1])
        else:
            string = self._join_multi_line_comments(multi_line_comments)
        return string.replace("'''", "").replace('"""', "")

    @staticmethod
    def _find_first_occurence_that_is_not_between(
        line: str, occurence: str, not_between: FrozenSet[str] = frozenset({"'", '"'})
    ) -> Optional[int]:
        """
        Finds the first occurrence of a character that is not between the given characters.

        Args:
            line (str): The line to search for the occurrence.
            occurence (str): The character to search for.
            not_between (FrozenSet[str], optional): A set of characters that define the quotes.
                Defaults to frozenset({"'", '"'}).

        Returns:
            Optional[int]: The index of the first occurrence that is not between quotes, or None if not found.
        """
        between_quotes = False
        for i, char in enumerate(line):
            if char in not_between:
                between_quotes = not between_quotes
            elif char == occurence and not between_quotes:
                return i
        return None

    @staticmethod
    def _extract_key_from_line(line: str) -> str:
        """
        Extracts the key from a YAML line.

        Examples for `line`:
            - key: value
              key2: value
        """
        line = YamlFileModifier._remove_spacing(line)
        if line[0] == "-":  # Detect list cases
            line = " " + line[1:]

        idx_first_char = line.find(line.strip()[0])
        idx_last_char = YamlFileModifier._find_first_occurence_that_is_not_between(line=line, occurence=":")
        if not idx_last_char:
            return ""
        line = line[idx_first_char:idx_last_char]
        if line.startswith('"') and line.endswith('"'):
            return line.strip('"')
        elif line.startswith("'") and line.endswith("'"):
            return line.strip("'")
        else:
            return line

    @staticmethod
    def _detect_indentation(lines: Sequence[str]) -> Literal["spaces", "tabs", "??"]:
        """
        Detects the type of indentation used in the given lines.

        Args:
            lines (Sequence[str]): The lines of code to analyze.

        Returns:
            Literal["spaces", "tabs", "??"]: The type of indentation used. It can be "spaces" if spaces are
                used for indentation, "tabs" if tabs are used for indentation, or "??" if both spaces and
                tabs are used.

        """
        tabs_used = any("\t" in line for line in lines)
        spaces_used = any(" " in line for line in lines)
        if tabs_used and spaces_used:
            return "??"
        elif tabs_used:
            return "tabs"
        elif spaces_used:
            return "spaces"
        else:
            return "??"

    @staticmethod
    def _count_spaces_or_tabs_at_start(line: str, *, indendation: Literal["spaces", "tabs"]) -> Optional[int]:
        """
        Counts the number of spaces or tabs at the start of a line.

        Args:
            line (str): The line to count spaces or tabs from.
            indendation (Literal["spaces", "tabs"]): The type of indentation to count.

        Returns:
            Optional[int]: The number of spaces or tabs at the start of the line, or None if the line contains a
                hyphen and the indentation is set to "tabs".
        """
        if "-" in line and indendation == "tabs":
            return None
        line = line.replace("-", " ")
        pattern = re.compile(r"^[ \t]*")
        result = pattern.match(line)
        if result:
            spaces_tabs = result.group()
            return len(spaces_tabs)
        return 0

    def _extract_comments(self) -> Tuple[Comment, ...]:
        """
        Extracts comments associated with keys in the YAML file.

        This includes comments that can be located above, below or by the side.
        These comments can also be multi-line.

        Returns:
            A tuple of Comment objects representing the extracted comments.
        """
        comments: List[Comment] = []
        indentation = self._detect_indentation(self.lines)
        if indentation == "??":
            return ()

        for idx, line in enumerate(self.lines):
            line_with_no_spacing = self._remove_spacing(line)
            if line_with_no_spacing[0].isalpha():
                spaces_or_tabs = self._count_spaces_or_tabs_at_start(line, indendation=indentation)
                if spaces_or_tabs is None:
                    continue

                key = self._extract_key_from_line(line)
                if not key:
                    continue

                for comments_are in self.comments_are:
                    if comments_are == "above" or comments_are == "below":
                        comment = self._extract_single_block_comment(idx, comments_are=comments_are)
                        comment = self._capitalize_only_first_letter(comment)
                    elif comments_are == "side":
                        comment = self._extract_side_comment(line)

                    if not comment:
                        continue
                    # Comments that are either below or above the keyword
                    comments.append(
                        Comment(
                            full_string=comment,
                            key_line=idx,
                            spacing_element=(indentation, spaces_or_tabs),
                            associated_with_key=key,
                        )
                    )

        return self._merge_comments(comments)

    @staticmethod
    def _format_comment_as_multiline_yaml(comment: Comment) -> str:
        """
        Formats a comment as a multiline YAML string.

        Args:
            comment (Comment): The comment object to format.
        """
        lines = comment.full_string.splitlines()
        lines.insert(0, "")
        indentation = comment.spacing_element[0]
        indent = "\t" if indentation == "tabs" else " "
        multiple_indentation = indent * (comment.spacing_element[1] + 1)
        return f"\n{multiple_indentation}".join(lines)

    @staticmethod
    def _merge_comments(comments: Sequence[Comment]) -> Tuple[Comment, ...]:
        """
        Merge comments that are associated with the same key.

        This can heppen if the user requests to read from "below" and "side" for example.
        """
        comments_in_line: Mapping[int, List[Comment]] = defaultdict(list)
        for comment in comments:
            comments_in_line[comment.key_line].append(comment)

        merged_comments: List[Comment] = []
        for comments_lst in comments_in_line.values():
            string = "\n\n".join(comment.full_string for comment in comments_lst)
            merged_comments.append(
                Comment(
                    full_string=string,
                    key_line=comments_lst[0].key_line,
                    associated_with_key=comments_lst[0].associated_with_key,
                    spacing_element=comments_lst[0].spacing_element,
                )
            )
        return tuple(merged_comments)

    def _create_temporary_string_with_comments_as_keys(self) -> str:
        """Create the YAML-based string representation of the new dictionary containing new doc-based keys."""
        comments = self._extract_comments()
        reverse_order_comments = sorted(comments, key=lambda comment: comment.key_line, reverse=True)
        new_lines = list(self.lines).copy()
        for comment in reverse_order_comments:
            key = self.preffix + comment.associated_with_key
            indentation = "\t" if comment.spacing_element[0] == "tabs" else " "
            string = (
                f"{indentation*comment.spacing_element[1]}{key}: |{self._format_comment_as_multiline_yaml(comment)}"
            )
            new_lines.insert(comment.key_line, string)
        return "\n".join(new_lines)

    def create_temporary_file_with_comments_as_keys(self) -> Path:
        """Create a new YAML file with new keys containing the documentation.

        This method creates a new YAML file by converting the comments in the original file into keys in the new file.
        The comments are extracted from the original file and added as keys in the new file.

        Returns:
            Path: The path to the newly created YAML file.
        """
        string = self._create_temporary_string_with_comments_as_keys()
        path = Path(tempfile.gettempdir()) / f"_{self.path.name}"
        path.write_text(string)
        return path
