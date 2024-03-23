import subprocess
from pathlib import Path
from typing import Iterable, List, NamedTuple, Union

from dynamic_pyi_generator.utils.utils import check_if_command_available


class Mypy:
    """
    A class for running the Mypy static type checker.

    Attributes:
        Result: A named tuple representing the result of running Mypy.
    """

    @staticmethod
    def is_available() -> bool:
        return check_if_command_available("mypy")

    class Result(NamedTuple):
        """Results returned by Mypy."""

        success: bool
        errors: List[str]
        scanned: Union[Path, str]

        def errors_as_str(self) -> str:
            return "\n".join(self.errors)

        def file_content_with_lineno(self) -> str:
            if isinstance(self.scanned, str):
                raise ValueError("This method is only callable when a file has been scanned.")
            lines: List[str] = []
            for idx, line in enumerate(self.scanned.read_text().splitlines()):
                lines.append(f"{idx} {line}")
            return "\n".join(lines)

        def __str__(self) -> str:
            if self.success:
                return "No errors"
            else:
                string = "Errors were found"
            if isinstance(self.scanned, Path):
                return (
                    f"{string}. {self.errors_as_str()}\n\nFile scanned ({self.scanned.name}): "
                    f"\n{self.file_content_with_lineno()}"
                )
            return f"{string}. {self.errors_as_str()}"

    def scan_string(
        self, string: str, *, strict: bool = False, python_version: str = "3.8", ignore_errors: Iterable[str] = ()
    ) -> Result:
        """
        Scan a string using the mypy static type checker.

        Args:
            string (str): The string to be scanned.
            strict (bool, optional): Whether to enable strict mode. Defaults to False.
            python_version (str, optional): The Python version to use for type checking. Defaults to "3.8".
            ignore_errors (Iterable[str], optional): A collection of error keywords to ignore during type checking.
                Defaults to ().

        Returns:
            Result: The result of the type checking, including success status, errors, and the scanned string.
        """
        command = ["mypy"]
        if strict:
            command.append("--strict")
        command.append("--python-version")
        command.append(python_version)
        command.append("-c")
        command.append(string)
        result = subprocess.run(command, capture_output=True)
        if result.stderr:
            return self.Result(success=False, errors=[str(result.stderr)], scanned=string)
        stdout = str(result.stdout)
        errors: List[str] = []
        lines = stdout.split("error: ")
        for error in lines:
            error_str = error[: error.rfind("]") + 1]
            if error_str:
                if ignore_errors:
                    if all(keyword not in error_str for keyword in ignore_errors):
                        print(error_str)
                        errors.append(error_str)
                else:
                    errors.append(error_str)
        return self.Result(success=not bool(errors), errors=errors, scanned=string)

    def scan_file(
        self,
        file: Union[str, Path],
        *,
        strict: bool = False,
        python_version: str = "3.8",
        ignore_errors: Iterable[str] = (),
    ) -> Result:
        """
        Run Mypy on the specified file.

        Args:
            file (Union[str, Path]): The file to run Mypy on.
            strict (bool, optional): Whether to enable strict mode. Defaults to False.
            python_version (str, optional): The Python version to use. Defaults to "3.8".
            ignore_errors (Iterable[str], optional): A collection of error strings to
                ignore. Defaults to ().

        Returns:
            Result: The result of running Mypy.

        """
        command = ["mypy"]
        if strict:
            command.append("--strict")
        command.append(f"--python-version {python_version}")
        command.append(str(file))
        result = subprocess.run(" ".join(command), capture_output=True, text=True)

        if result.stderr:
            raise ValueError(f"Mypy could not run: {result.stderr}")

        error_lst = [line for line in result.stdout.splitlines() if "error: " in line]
        if ignore_errors:
            error_lst = [line for line in error_lst if not all(ignore_error in line for ignore_error in ignore_errors)]
        # Filter out to only get the errors from the file
        error_lst = [error for error in error_lst if Path(file).name in error]
        return self.Result(
            success=not bool(error_lst),
            errors=error_lst,
            scanned=Path(file),
        )
