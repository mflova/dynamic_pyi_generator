import ast
from collections.abc import Sequence
from typing import Any, List, Literal, Tuple, Union, overload

from dynamic_pyi_generator.utils import TAB


class PyFileModifier:
    lines: List[str]

    def __init__(self, representation: str) -> None:
        self.lines = representation.splitlines()

    def __str__(self) -> str:
        return "\n".join(self.lines)

    def __repr__(self) -> str:
        return "\n".join(self.lines)

    @overload
    def search_assignment(self, variable: str, only_values: Literal[False] = False) -> List[Tuple[int, str]]:
        ...

    @overload
    def search_assignment(self, variable: str, only_values: Literal[True]) -> List[str]:
        ...

    def search_assignment(self, variable: str, only_values: bool = False) -> Union[List[Tuple[int, str]], List[str]]:
        """
        Searches for assignments of a given variable in the lines of the file.

        Args:
            variable (str): The variable to search for assignments.
            only_values (bool): Only return the values being assigned to that variable.

        Returns:
            List[Tuple[int, str]]: A list of tuples containing the line index and the
                assigned value.
        """
        lst: List[Any] = []
        for idx, line in enumerate(self.lines):
            if variable in line and "=" in line and not self.it_is_string(line, variable):
                value = line.split("=")[-1].strip()
                if isinstance(value, str) and value[0] in ("'", '"'):
                    value = value[1:-1]
                if only_values:
                    lst.append(value)
                else:
                    lst.append((idx, value))
        return lst

    def search_decorator(self, *, decorator_name: str, method_name: str) -> List[int]:
        """
        Searches for a specific decorator in the lines of code preceding a method.

        Args:
            decorator_name (str): The name of the decorator to search for.
            method_name (str): The name of the method to search for.

        Returns:
            List[int]: A list of line numbers where the decorator is found.
        """
        lst = self.search_method(method_name=method_name, return_index_above_decorator=False)
        output: List[int] = []
        for idx in lst:
            while "@" in self.lines[idx - 1]:
                if f"@{decorator_name}" in self.lines[idx - 1]:
                    output.append(idx - 1)
                    break
                break
        return output

    def search_method(self, method_name: str, *, return_index_above_decorator: bool = True) -> List[int]:
        """
        Search for a method in the lines of the file and return its location (indices).

        Args:
            method_name (str): The name of the method to search for.
            return_index_above_decorator (bool, optional): Whether to return the index
                above the decorator if found. Defaults to True.

        Returns:
            List[int]: A list of indices where the method is found.
        """
        lst: List[int] = []
        for idx, line in enumerate(self.lines):
            if line.strip().startswith(f"def {method_name}") and not self.it_is_string(line, method_name):
                if return_index_above_decorator:
                    while "@" in self.lines[idx - 1]:
                        idx = idx - 1
                lst.append(idx)
        return lst

    def it_is_string(self, line: str, keyword_of_interest: str) -> bool:
        for string_symbol in ('"', "'"):  # noqa: SIM110
            if string_symbol in line.split(keyword_of_interest)[0]:
                return True
        return False

    def add_line(self, idx: int, line: Union[str, Sequence[str]]) -> None:
        """
        Add a line or multiple lines at the specified index.

        Args:
            idx (int): The index at which to insert the line(s).
            line (Union[str, Sequence[str]]): The line(s) to be added. It can be a
                single string or a sequence of strings.
        """
        if not isinstance(line, str):
            line = "\n".join(line)
        self.lines.insert(idx, line)

    def search_line(self, keyword: str) -> int:
        """
        Searches for a line containing the specified keyword within the file.

        Args:
            keyword (str): The keyword to search for.

        Returns:
            int: The index of the line containing the keyword.
        """
        for idx, line in enumerate(self.lines):
            if keyword in line:
                return idx
        raise ValueError(f"Line with `{keyword}` could not be found within the file.")

    def replace_line(self, idx: int, line: str) -> None:
        """
        Replaces the line at the specified index with the given line.

        Args:
            idx (int): The index of the line to be replaced.
            line (str): The new line to replace the existing line.
        """
        self.lines[idx] = line

    def replace_assignement(self, label: Union[int, str], value: str) -> None:
        """
        Replaces the value of an assignment line identified by the given label or index.

        Args:
            label (Union[int, str]): The label or index of the assignment line to be
                replaced.
            value (str): The new value to be assigned.
        """
        if not isinstance(label, int):
            assignment_idx = self.search_assignment(label)
            if not assignment_idx:
                raise ValueError(f"The given label ({label}) is not being assigned.")
            if len(assignment_idx) > 1:
                raise ValueError(
                    f"The given label ({label}) is assigned multiple times. Not clear which one should be replaced."
                )
            idx = assignment_idx[0][0]
        else:
            idx = label

        line = self.lines[idx]
        if "=" not in line:
            raise ValueError(f"The given line ({idx}) is not an assignment one.")
        symbols = line.split("=")
        symbols[-1] = value
        self.lines[idx] = "=".join(symbols)

    def remove_all_method_bodies(self) -> None:
        """
        Removes the bodies of all methods in the file.

        This method parses the file's contents using the `ast` module and walks through
        the abstract syntax tree (AST) to find all function definitions. For each function
        definition found, the body of the function is replaced with an `Ellipsis` object,
        effectively removing the method body.

        After modifying the AST, the updated code is converted back to a string and split
        into lines, which are then stored in the `lines` attribute of the object.

        Note: This method modifies the object in-place.
        """
        tree = ast.parse(str(self))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                node.body = [ast.Ellipsis()]  # type: ignore
        self.lines = ast.unparse(tree).strip().splitlines()  # type: ignore

    def remove_all_private_methods(self) -> None:
        """
        Removes all private methods from the file.

        This method iterates through the lines of the file and removes any lines
        that define a private method. A private method is defined as a method that
        starts with an underscore (_) character.

        Note: This method modifies the object in-place.
        """
        lines_to_remove: List[int] = []
        for idx, line in enumerate(self.lines):
            line_ = line.strip()
            if line_.startswith("def _") and not line_.startswith("def __"):
                idx_ = idx - 1
                # Remove all decorators
                if "@" in self.lines[idx_]:
                    while "@" in self.lines[idx_]:
                        lines_to_remove.append(idx_)
                        idx_ -= 1

                # Remove main function
                lines_to_remove.append(idx)

                idx_ = idx
                # Remove all arguments if they are in multiple lines
                while "):" not in self.lines[idx_] and "->" not in self.lines[idx_]:
                    idx_ += 1
                    lines_to_remove.append(idx_)

                # Remove body of the method
                # Count tabs
                spaces = 0
                for char in line:
                    if char.isspace():
                        spaces += 1
                    else:
                        break

                idx_ += 1
                while len(self.lines) > idx_ and len(self.lines[idx_]) > spaces and self.lines[idx_][spaces].isspace():
                    lines_to_remove.append(idx_)
                    idx_ += 1
                if len(self.lines) > idx_:
                    lines_to_remove.append(idx_)

        for idx in sorted(lines_to_remove)[::-1]:
            self.lines.pop(idx)

    def remove_all_instance_variables(self, class_name: str) -> None:
        """
        Removes all instance variables from a class.

        Args:
            class_name (str): The name of the class.
        """
        upper_idx = self.search_line(f"class {class_name}:") + 1

        lower_idx = self.search_method("__init__", return_index_above_decorator=True)[-1]
        for idx in list(range(upper_idx, lower_idx))[::-1]:
            if "classes_created" in self.lines[idx] or "classes_created" in self.lines[idx - 1]:
                continue
            self.lines.pop(idx)

    def add_imports(self, lines: Union[str, Sequence[str]], *, in_type_checking_block: bool = False) -> None:
        """
        Adds import statements to the file.

        Args:
            lines (Union[str, Sequence[str]]): The import statements to add. It can
                be a single string or a sequence of strings.
            in_type_checking_block (bool, optional): Specifies whether the import
                statements should be added inside a type checking block.
                Defaults to False.
        """
        idx = 0
        if isinstance(lines, str):
            lines = [lines]

        if in_type_checking_block:
            idx = self.search_line("if TYPE_CHECKING:") + 1
            lines = [f"{TAB}{line}" for line in lines]
        for line in lines[::-1]:
            self.lines.insert(idx, line)

    def get_signature(self, method_name: str) -> Tuple[str, slice]:
        """
        Retrieves the signature of a method.

        Args:
            method_name (str): The name of the method.

        Returns:
            Tuple[str, slice]: A tuple containing the method signature as a string and a
                slice object representing the range of lines in the file that contain
                the signature.
        """
        upper_idx = self.search_method(method_name, return_index_above_decorator=True)[-1]
        bottom_idx = upper_idx

        while ")" not in self.lines[bottom_idx] and ":" not in self.lines[bottom_idx]:
            bottom_idx += 1

        return "\n".join(self.lines[upper_idx : bottom_idx + 1]), slice(upper_idx, bottom_idx + 1)
