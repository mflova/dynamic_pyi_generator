import os
import re
import shutil
from pathlib import Path
from types import ModuleType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Final,
    Literal,
    Mapping,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    final,
    overload,  # noqa: F401
)

import dynamic_pyi_generator
from dynamic_pyi_generator.data_type_tree.data_type_tree import DataTypeTree
from dynamic_pyi_generator.file_handler import FileHandler
from dynamic_pyi_generator.strategies import Strategies
from dynamic_pyi_generator.utils import (
    TAB,
    compare_str_via_ast,
    is_string_python_keyword_compatible,
)

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

THIS_DIR = Path(__file__).parent


class PyiGeneratorError(Exception):
    """Raised by `PyiGenerator` class."""


ObjectT = TypeVar("ObjectT")


class PyiGenerator:
    # Utils
    this_file_pyi: FileHandler
    """.pyi representation of this same module."""
    this_file_pyi_path: Path
    """Path to the .pyi file associated to this same module."""
    custom_classes_dir: Tuple[Union[ModuleType, str], ...]
    """Hold the information where the class interfaces will be created.
    
    First one is `ModuleType`. Following ones are strings. At least one must be provided.
    """
    if_interface_exists: Literal["overwrite", "validate"]
    """Strategy to follow if a requested class has been found as existing."""
    strategies: Strategies
    """Strategies to follow when parsing the objects."""

    # Constants that should not be modified
    header: Final = "# Class automatically generated. DO NOT MODIFY."
    """Header that will be prepended to all new classes created."""
    classes_created: "TypeAlias" = Any
    """Classes created by the class. Do not modify."""
    methods_to_be_overloaded: Final = ("from_data", "from_file")
    """Methods that will be modified in the PYI interface when new classes are added."""

    @final
    def __init__(
        self,
        *,
        strategies: Strategies = Strategies(),  # noqa: B008
        if_interface_exists: Literal["overwrite", "validate"] = "validate",
        generated_classes_custom_dir: Tuple[Union[ModuleType, str], ...] = (
            dynamic_pyi_generator,
            "build",
        ),
    ) -> None:
        self.custom_classes_dir = generated_classes_custom_dir
        self.if_interface_exists = if_interface_exists
        self.strategies = strategies

        self.this_file_pyi_path = Path(__file__).with_suffix(".pyi")
        if not self.this_file_pyi_path.exists():
            self.this_file_pyi = self._generate_this_file_pyi()
        else:
            self.this_file_pyi = FileHandler(self.this_file_pyi_path.read_text(encoding="utf-8"))

        # Validation
        self._validate_classes_custom_dir(self.custom_classes_dir)

    def _validate_classes_custom_dir(
        self,
        generated_classes_custom_dir: Tuple[Union[ModuleType, str], ...],
    ) -> None:
        arg_name = "generated_classes_custom_dir"
        if not isinstance(generated_classes_custom_dir[0], ModuleType):
            raise PyiGeneratorError(
                f"First element of `{arg_name}` must be a `ModuleType` that can be "
                "imported within your current Python environment."
            )
        if len(generated_classes_custom_dir) == 1:
            raise PyiGeneratorError(
                f"`{arg_name}` must have at least first element of type `ModuleType` "
                "and a second one being a string."
            )
        if not all(isinstance(element, str) for element in generated_classes_custom_dir[1:]):
            raise PyiGeneratorError(f"All elements of `{arg_name}` (but the first one) must be strings.")

        if any(
            not is_string_python_keyword_compatible(string)  # type: ignore
            for string in generated_classes_custom_dir[1:]
        ):
            raise PyiGeneratorError(
                f"All strings provided in `{arg_name}` must contain only alphanumeric "
                "or underscores. They must be compliant with the Python module naming "
                "rules."
            )

        # Check that this directory only contains custom data generated by this class
        if self._custom_class_dir_path.exists():
            classes_added = self._get_classes_added()
            if len(list(self._custom_class_dir_path.iterdir())) != len(classes_added):
                raise PyiGeneratorError(
                    "The given directory to generate custom data "
                    f"({self._custom_class_dir_path}) contains data that was not "
                    "generated by this class. Choose a non existing one."
                )

    def _get_classes_added(self) -> Mapping[str, Path]:
        to_find = "classes_created"
        values = self.this_file_pyi.search_assignment("classes_created", only_values=True)
        if not values:
            raise PyiGeneratorError(f"No `{to_find}` was found in this file.")

        if values[0] == "Any":
            return {}
        matches = re.findall(r'"(.*?)"', values[0])

        dct: Dict[str, Path] = {}
        for match in matches:
            path = Path(self._custom_class_dir_path / f"{match}.py")
            if not path.exists():
                raise PyiGeneratorError(
                    f"A class `{match}` was apparently created but cannot find its "
                    f"corresponding source code within {self._custom_class_dir_path}"
                )
            dct[match] = path
        return dct

    def from_file(
        self,
        loader: Callable[[str], ObjectT],
        path: str,
        class_name: str,
    ) -> ObjectT:
        return self.from_data(
            loader(path),
            class_name=class_name,
        )

    def from_data(
        self,
        data: ObjectT,
        class_name: str,
    ) -> ObjectT:
        if not is_string_python_keyword_compatible(class_name):
            raise PyiGeneratorError(
                f"Given class_name is not compatible with Python class naming conventions: {class_name}"
            )
        cls = DataTypeTree.get_data_type_tree_for_type(type(data))
        string_representation = str(cls(data, name=class_name, strategies=self.strategies))
        string_representation = self.header + "\n" + string_representation
        classes_added = self._get_classes_added()
        if class_name not in classes_added:
            self._create_custom_class_py(string_representation, class_name)
            self._add_new_class_to_loader_pyi(new_class=class_name)
        elif self.if_interface_exists == "overwrite":
            self._create_custom_class_py(string_representation, class_name)
        else:
            if not compare_str_via_ast(
                classes_added[class_name].read_text(),
                string_representation,
                ignore_imports=True,
            ):
                raise PyiGeneratorError(
                    f"An attempt to load a dictionary with an already existing class "
                    f"type ({class_name}) has been made. However, the given dictionary"
                    f" is not compliant with `{class_name}` type. Possible solutions:"
                    " 1) Create a new interface by modifying `class_type` input "
                    "argument, 2) reset all the interfaces with `reset` or 3) make the"
                    " input dictionary compliant."
                )
        return data

    def reset(self) -> None:
        self._reset_custom_class_pyi()
        self.this_file_pyi = self._generate_this_file_pyi()
        self._update_this_file_pyi()

    @final
    def _generate_this_file_pyi(self) -> FileHandler:
        content = Path(__file__).read_text()

        # Prepend @overload decorator to load function
        file_handler = FileHandler(content)
        file_handler.remove_all_method_bodies()
        file_handler.remove_all_private_methods()
        file_handler.remove_all_instance_variables(class_name=(type(self)).__name__)
        return file_handler

    @property
    def _custom_class_dir_path(self) -> Path:
        package_path: Path = Path(self.custom_classes_dir[0].__path__[0])  # type: ignore
        sub_paths: Sequence[Path] = self.custom_classes_dir[1:]  # type: ignore

        for string in sub_paths:
            package_path = package_path / string
        return package_path

    def _create_custom_class_py(self, string: str, class_name: str) -> None:
        if not self._custom_class_dir_path.exists():
            os.makedirs(self._custom_class_dir_path)

        path = self._custom_class_dir_path / f"{class_name}.py"
        path.write_text(string)

    @final
    def _add_new_class_to_loader_pyi(self, *, new_class: str) -> None:
        self._add_class_created_to_this_file_pyi(new_class)
        self._add_import_to_this_file_pyi(new_class)
        for method_name in self.methods_to_be_overloaded:
            self._add_overload_to_this_file_pyi(new_class=new_class, method_name=method_name)

    @final
    def _reset_custom_class_pyi(self) -> None:
        if self._custom_class_dir_path.exists():
            shutil.rmtree(self._custom_class_dir_path)

    @final
    def _add_import_to_this_file_pyi(self, new_class: str) -> None:
        import_statement = (
            f"from {self.custom_classes_dir[0].__name__}."  # type: ignore
            f"{'.'.join(self.custom_classes_dir[1:])}.{new_class} import {new_class}"  # type: ignore
        )
        self.this_file_pyi.add_imports(
            import_statement,
            in_type_checking_block=True,
        )
        self._update_this_file_pyi()

    @final
    def _add_overload_to_this_file_pyi(
        self, *, new_class: str, method_name: str, input_argument: str = "class_name"
    ) -> None:
        # First time the function is called it will attach an extra @overload decorator
        if not self.this_file_pyi.search_decorator(decorator_name="overload", method_name=method_name):
            idx_lst = self.this_file_pyi.search_method(method_name, return_index_above_decorator=True)
            if not idx_lst:
                raise PyiGeneratorError(f"No method `{method_name}` could be found")

            self.this_file_pyi.add_line(idx_lst[-1], f"{TAB}@overload")

        signature, _ = self.this_file_pyi.get_signature(method_name)

        # At this point idx is the index of the line where the input argument was found
        first_idx = signature.find(input_argument)
        if first_idx == -1:
            raise PyiGeneratorError(f"No {input_argument} could be found within the signature {signature}")
        first_idx += len(input_argument)
        last_idx = first_idx
        while signature[last_idx] not in (",", ")"):
            last_idx += 1
        # The type hint of the input argument to modify is between first_idx and last_idx
        signature = signature[: first_idx + 1] + f' Literal["{new_class}"]' + signature[last_idx:]

        # Modifying returned value
        last_idx = signature.rfind(":")
        first_idx = signature.rfind("->")
        signature = signature[: first_idx + len("->") + 1] + new_class + signature[last_idx:]

        idx = self.this_file_pyi.search_method(method_name=method_name, return_index_above_decorator=True)[-1]
        self.this_file_pyi.add_line(idx, signature)
        self._update_this_file_pyi()

    @final
    def _add_class_created_to_this_file_pyi(self, new_class: str) -> None:
        label = "classes_created"

        value = self.this_file_pyi.search_assignment(label, only_values=True)[0]
        if not value:
            raise PyiGeneratorError(f"No `{label}` was found in this file.")
        # Case: Any
        if value == "Any":
            value = f'Union[Literal["{new_class}"], Any]'
        # Case: Union[Literal["A"], Any]
        else:
            value = value.replace("], Any]", f', "{new_class}"], Any]')

        self.this_file_pyi.replace_assignement(label, value)
        self._update_this_file_pyi()

    @final
    def _update_this_file_pyi(self) -> None:
        self.this_file_pyi_path.write_text(str(self.this_file_pyi))
