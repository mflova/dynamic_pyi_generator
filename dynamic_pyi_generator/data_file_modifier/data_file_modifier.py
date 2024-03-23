# TODO:
# Also parse the comments at right if found.
# Once I do it, I can append them to the full comment found either up or below
import re
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final, Iterable, List, Literal, Optional, Sequence, Set, Tuple, Union, cast


@dataclass(frozen=True)
class Comment:
    full_string: str
    associated_with_key: str
    key_line: int
    spacing_element: Tuple[Literal["spaces", "tabs", "none"], int]


class DataFileModifier:
    path: Path
    lines: Tuple[str, ...]
    comments_are: Literal["above", "below"]

    def __init__(self, path: Union[str, Path], *, comments_are: Literal["above", "below"]) -> None:
        self.path = Path(path)
        self.lines = tuple(Path(path).read_text().splitlines())
        self.comments_are = comments_are

    @staticmethod
    def _remove_spacing(line: str) -> str:
        line.strip()
        lines = line.split("\t")
        lines = [line.lstrip() for line in lines]
        return "".join(lines)

    @staticmethod
    def _join_multi_line_comments(lines: Sequence[str]) -> str:
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
                            result += single_line_comment_[0].upper() + single_line_comment_[1:]
                        else:
                            result += ". " + single_line_comment.strip()
                else:
                    single_line_comment_ = single_line_comment.strip()
                    if result.endswith("."):
                        result += " " + single_line_comment_[0].upper() + single_line_comment_[1:]
                    else:
                        if result.endswith("\n"):
                            single_line_comment_ = single_line_comment.strip()
                            result += single_line_comment_[0].upper() + single_line_comment_[1:]
                        else:
                            result += " " + single_line_comment.strip()
            else:
                result += single_line_comment.strip()
        if not result:
            return result
        if result.endswith("."):
            return result
        return result + "."

    def _extract_single_block_comment(self, line_idx: int) -> str:
        # Find first non space/tab character
        try:
            line = self.lines[line_idx]
        except IndexError:
            return ""
        idx_first_char = line.find(line.strip()[0])

        step: Final = -1 if self.comments_are == "above" else 1
        increment = step
        multi_line_comments: List[str] = []
        with suppress(IndexError):
            while self.lines[line_idx + increment][idx_first_char] == "#":
                multi_line_comments.append(self.lines[line_idx + increment][idx_first_char + 1 :].strip())
                increment += step

        if not multi_line_comments:
            return ""

        if self.comments_are == "above":
            string = self._join_multi_line_comments(multi_line_comments[::-1])
        else:
            string = self._join_multi_line_comments(multi_line_comments)
        return string.replace("'''", "").replace('"""', "")

    @staticmethod
    def _find_first_occurence_that_is_not_between(
        line: str, occurence: str, not_between: Set[str] = {"'", '"'}
    ) -> Optional[int]:
        between_quotes = False
        for i, char in enumerate(line):
            if char in not_between:
                between_quotes = not between_quotes
            elif char == occurence and not between_quotes:
                return i
        return None

    @staticmethod
    def _extract_key_from_line(line: str) -> str:
        idx_first_char = line.find(line.strip()[0])
        idx_last_char = DataFileModifier._find_first_occurence_that_is_not_between(line=line, occurence=":")
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
    def _count_spaces_or_tabs_at_start(line: str) -> Tuple[Literal["spaces", "tabs", "none"], int]:
        pattern = re.compile(r"^[ \t]*")
        result = pattern.match(line)
        if result:
            spaces_tabs = result.group()
            num_spaces_tabs = len(spaces_tabs)
            if " " in spaces_tabs:
                return "spaces", num_spaces_tabs
            elif "\t" in spaces_tabs:
                return "tabs", num_spaces_tabs
            return "none", 0
        else:
            return "none", 0

    def _extract_comments(self) -> Tuple[Comment, ...]:
        comments: List[Comment] = []
        for idx, line in enumerate(self.lines):
            line_with_no_spacing = self._remove_spacing(line)
            if line_with_no_spacing[0].isalpha():
                spaces_or_tabs = self._count_spaces_or_tabs_at_start(line)
                if spaces_or_tabs[0] == "none" and spaces_or_tabs[1] != 0:
                    continue

                key = self._extract_key_from_line(line)
                if not key:
                    continue

                single_block_comment = self._extract_single_block_comment(idx)
                if not single_block_comment:
                    continue

                spaces_or_tabs = cast(Tuple[Literal["spaces", "tabs"], int], spaces_or_tabs)
                comments.append(
                    Comment(
                        full_string=single_block_comment,
                        key_line=idx,
                        spacing_element=spaces_or_tabs,
                        associated_with_key=key,
                    )
                )
        return tuple(comments)

    def create_temporary_file_with_comments_as_keys(self, comments: Tuple[Comment, ...]) -> None:
        pass
