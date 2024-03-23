from typing import List, Tuple, Union

import pytest

from dynamic_pyi_generator.file_handler import FileHandler


class TestFileHandler:
    """Test class for the FileHandler class."""

    @pytest.fixture
    def file_handler(self) -> FileHandler:
        representation = """class PyiGenerator:
loader_pyi: str
classes_created: "TypeAlias" = Any
custom_class_dir: Final = "build"
number: Final = 2
tab: Final = "    "

@final
def __init__(self) -> None:
    self.loader_pyi_path = Path(__file__).with_suffix(".pyi")
    if not self.loader_pyi_path.exists():
        self.loaded_pyi_content = self.generate_loader_pyi()
    else:
        self.loaded_pyi_content = self.loader_pyi_path.read_text(encoding="utf-8")

def get_classes_added(self) -> Set[str]:
    to_find = "classes_created"
    for line in self.loaded_pyi_content.split("\n"):
        if "classes_created" in line:
            break
    else:
        raise PyiGeneratorError(f"No `{to_find}` was found in this file.")

    value = line.split("=")[-1].strip()
    if value == "Any":
        return set()
    pattern = r'"(.*?)"'
    matches = re.findall(pattern, value)
    return set(matches)

@staticmethod
def test(self) -> None:
    ...

@staticmethod
def _find_line_idx(string: str, *, keyword: str) -> int:
    for idx, line in enumerate(string.split("\n")):
        if keyword in line and "test" not in line and "@overload" not in line:
            return idx
    raise PyiGeneratorError(
        f"It was not possible to find {keyword} among the lines of the given string."
    )
    
@overload
def run():
    pass

@overload
def run():
    pass"""

        return FileHandler(representation)

    @pytest.mark.parametrize(
        "decorator_name, method_name, expected_idx",
        [
            ("staticmethod", "test", [31]),
            ("overload", "run", [45, 49]),
            ("new_decorator", "run", []),
            ("final", "__init__", [7]),
            ("final", "new_method", []),
        ],
    )
    def test_search_decorator(
        self,
        decorator_name: str,
        expected_idx: List[int],
        file_handler: FileHandler,
        method_name: str,
    ) -> None:
        assert file_handler.search_decorator(decorator_name=decorator_name, method_name=method_name) == expected_idx

    @pytest.mark.parametrize(
        "method_name, return_index_above_decorator, expected_idx",
        [
            ("__init__", False, [8]),
            ("__init__", True, [7]),
            ("test", False, [32]),
            ("test", True, [31]),
            ("_find_line_idx", False, [36]),
            ("_find_line_idx", True, [35]),
            ("run", False, [46, 50]),
            ("run", True, [45, 49]),
        ],
    )
    def test_search_method(
        self,
        file_handler: FileHandler,
        method_name: str,
        return_index_above_decorator: bool,
        expected_idx: List[int],
    ) -> None:
        assert (
            file_handler.search_method(method_name, return_index_above_decorator=return_index_above_decorator)
            == expected_idx
        )

    @pytest.mark.parametrize(
        "string, keyword_of_interest, expected_result",
        (
            ["def test()", "test", False],
            ["'def' test()", "test", True],
        ),
    )
    def test_it_is_string(
        self,
        file_handler: FileHandler,
        string: str,
        expected_result: bool,
        keyword_of_interest: str,
    ) -> None:
        assert file_handler.it_is_string(string, keyword_of_interest) == expected_result

    @pytest.mark.parametrize(
        "line, idx",
        (
            ["def test()", 30],
            ["@overload", 40],
        ),
    )
    def test_add_line(self, file_handler: FileHandler, line: str, idx: int) -> None:
        len_before = len(file_handler.lines)
        file_handler.add_line(idx, line)
        assert file_handler.lines[idx] == line
        assert len_before + 1 == len(file_handler.lines)

    @pytest.mark.parametrize(
        "variable, expected_output",
        (
            ["custom_class_dir", [(3, "build")]],
            ["classes_created", [(2, "Any")]],
            ["number", [(4, "2")]],
            ["tab", [(5, "    ")]],
            ["new", []],
        ),
    )
    def test_search_assignement(
        self,
        file_handler: FileHandler,
        variable: str,
        expected_output: List[Tuple[int, str]],
    ) -> None:
        assert file_handler.search_assignment(variable) == expected_output

    @pytest.mark.parametrize(
        "keyword, expected_idx",
        (
            ["number", 4],
            ["def", 8],
        ),
    )
    def test_search_line(
        self,
        file_handler: FileHandler,
        keyword: str,
        expected_idx: int,
    ) -> None:
        assert file_handler.search_line(keyword) == expected_idx

    @pytest.mark.parametrize(
        "idx, line",
        (
            [10, "new line"],
            [20, "edited"],
        ),
    )
    def test_replace_line(
        self,
        file_handler: FileHandler,
        idx: int,
        line: str,
    ) -> None:
        assert file_handler.lines[idx] != line
        file_handler.replace_line(idx, line)
        assert file_handler.lines[idx] == line

    @pytest.mark.parametrize(
        "imports, in_type_checking_block, expected_string",
        (
            [
                ["from A import B", "from B import C"],
                False,
                """from A import B
from B import C
import C

if TYPE_CHECKING:
    import D""",
            ],
            [
                ["from A import B", "from B import C"],
                True,
                """import C

if TYPE_CHECKING:
    from A import B
    from B import C
    import D""",
            ],
        ),
    )
    def test_add_imports(
        self,
        imports: str,
        in_type_checking_block: bool,
        expected_string: str,
    ) -> None:
        file_handler = FileHandler(
            """import C

if TYPE_CHECKING:
    import D"""
        )
        file_handler.add_imports(imports, in_type_checking_block=in_type_checking_block)
        assert str(file_handler) == expected_string

    @pytest.mark.parametrize(
        "label, value",
        (
            ["classes_created", "float"],
            ["tab", "2"],
            [2, "int"],
        ),
    )
    def test_replace_assignment(
        self,
        file_handler: FileHandler,
        label: Union[int, str],
        value: str,
    ) -> None:
        file_handler.replace_assignement(label, value)

        if isinstance(label, str):
            assignments = file_handler.search_assignment(label)
            if not assignments:
                raise ValueError("No assignments were found")
            idx = assignments[0][0]
        else:
            idx = label
        assert file_handler.lines[idx].split("=")[-1].strip() == value

    @pytest.mark.parametrize(
        "method_name, expected_output",
        (
            ["__init__", ("@final\ndef __init__(self) -> None:", slice(7, 9))],
            [
                "get_classes_added",
                ("def get_classes_added(self) -> Set[str]:", slice(15, 16)),
            ],
        ),
    )
    def test_get_signature(
        self,
        file_handler: FileHandler,
        method_name: str,
        expected_output: Tuple[str, slice],
    ) -> None:
        assert expected_output == file_handler.get_signature(method_name)


class TestFileHandlerRemoval:
    """Test those remove-based methods from FileHandler."""

    @pytest.fixture
    def file_handler(self) -> FileHandler:
        representation = """

def method1():
    pass

def method2(value: int):
    return 2+2

def _method2(value: int):...

class PyiGenerator:

    @overload
    def _method3(self, a: int) -> None: 
        pass

    @overload
    def _method4(self, a: int): 
        pass

    def _method5(self,
        a: int,
    ): 
        pass

    @overload
    def method3(self):
        pass"""
        return FileHandler(representation)

    def test_remove_method_bodies(
        self,
        file_handler: FileHandler,
    ) -> None:
        file_handler.remove_all_method_bodies()
        expected_string = """def method1():...

def method2(value: int):...

def _method2(value: int):...

class PyiGenerator:

    @overload
    def _method3(self, a: int) -> None:...

    @overload
    def _method4(self, a: int):...

    def _method5(self, a: int):...

    @overload
    def method3(self):..."""
        assert str(file_handler) == expected_string

    def test_remove_private_methods(
        self,
        file_handler: FileHandler,
    ) -> None:
        file_handler.remove_all_private_methods()
        expected_string = """

def method1():
    pass

def method2(value: int):
    return 2+2

class PyiGenerator:

    @overload
    def method3(self):
        pass"""
        assert str(file_handler) == expected_string
