import os
import pickle
import re
import shutil
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Final,
    Literal,
    Mapping,
    Optional,
    Sequence,
    TypeVar,
    Union,
    cast,
    final,
    overload,  # noqa: F401
)

from typing_extensions import TypeAlias, override

from lazy_type_hint.data_type_tree import DataTypeTree
from lazy_type_hint.file_modifiers.py_file_modifier import PyFileModifier
from lazy_type_hint.file_modifiers.yaml_file_modifier import YAML_COMMENTS_POSITION
from lazy_type_hint.generators.lazy_type_hint_abc import LazyTypeHintABC
from lazy_type_hint.strategies import ParsingStrategies
from lazy_type_hint.utils import (
    TAB,
    is_string_python_keyword_compatible,
)

THIS_DIR = Path(__file__).parent


class LazyTypeHintLiveError(Exception):
    """Raised by `LazyTypeHintLive` class."""


ObjectT = TypeVar("ObjectT")
PathT = TypeVar("PathT", str, Path)


class LazyTypeHintLive(LazyTypeHintABC):
    """Generate type hints for any data structure and use them out of the box."""

    # Utils
    this_file_pyi: PyFileModifier
    """.pyi representation of this same module."""
    strategies: ParsingStrategies
    """Strategies to follow when parsing the objects."""
    if_type_hint_exists: Literal["overwrite", "validate"]
    """Strategy to follow if existing type hints were found for the same class name."""

    # Constants that should not be modified
    classes_created: "TypeAlias" = Any
    """Classes created by the class. Do not modify."""
    _methods_to_be_overloaded: Final = ("from_data", "from_yaml_file")
    """Methods that will be modified in the PYI interface when new classes are added."""
    _this_file_pyi_path: Final = Path(__file__).with_suffix(".pyi")
    """Path to the .pyi file associated to this same module."""
    _custom_class_dir_path: Final = _this_file_pyi_path.parent / "build"
    """Path where the new classes will be generated.c"""

    @final
    def __init__(
        self,
        strategies: ParsingStrategies = ParsingStrategies(),  # noqa: B008
        if_type_hint_exists: Literal["overwrite", "validate"] = "overwrite",
    ) -> None:
        self.strategies = strategies
        self.if_type_hint_exists = if_type_hint_exists

        if not self._this_file_pyi_path.exists():
            self.this_file_pyi = self._generate_this_file_pyi()
        else:
            self.this_file_pyi = PyFileModifier(self._this_file_pyi_path.read_text(encoding="utf-8"))

    def _get_classes_added(self) -> Mapping[str, Path]:
        to_find = "classes_created"
        values = self.this_file_pyi.search_assignment("classes_created", only_values=True)
        if not values:
            raise LazyTypeHintLiveError(f"No `{to_find}` was found in this file.")

        if values[0] == "Any":
            return {}
        matches = re.findall(r'"(.*?)"', values[0])

        dct: Dict[str, Path] = {}
        for match in matches:
            path = Path(self._custom_class_dir_path / f"{match}.py")
            if not path.exists():
                raise LazyTypeHintLiveError(
                    f"A class `{match}` was apparently created but cannot find its "
                    f"corresponding source code within {self._custom_class_dir_path}"
                )
            dct[match] = path
        return dct

    @override
    def from_pickle_file(
        self,
        path: PathT,
        *,
        class_name: str,
    ) -> Any:
        # TODO: Make LiveABC covariant with the returned type
        return super().from_pickle_file(path=path, class_name=class_name)


    @override
    def from_yaml_file(
        self,
        loader: Callable[[PathT], ObjectT],
        path: PathT,
        *,
        class_name: str,
        comments_are: Optional[Union[YAML_COMMENTS_POSITION, Sequence[YAML_COMMENTS_POSITION]]] = "side",
        **kwargs: Any,
    ) -> ObjectT:
        return super().from_yaml_file(loader=loader, path=path, class_name=class_name, comments_are=comments_are)  # type: ignore

    @override
    def from_data(
        self,
        data: ObjectT,
        class_name: str,
        **kwargs: Any,
    ) -> ObjectT:
        if not is_string_python_keyword_compatible(class_name):
            raise LazyTypeHintLiveError(
                f"Given class_name is not compatible with Python class naming conventions: {class_name}"
            )
        custom_class_file_path = self._custom_class_dir_path / f"{class_name}.py"

        if class_name in self._get_classes_added() and self.if_type_hint_exists == "validate":
            string_representation = cast(
                DataTypeTree, super().from_data(data=data, class_name=class_name)
            ).get_str_all_nodes(make_parent_class_inherit_from_original_type=False)
            if self._remove_docstrings(string_representation) != self._remove_docstrings(
                custom_class_file_path.read_text(encoding="utf-8")
            ):
                raise LazyTypeHintLiveError(
                    f"Error in validation: Existing type hints were found for `{class_name}` and this one does not "
                    "match the inner structure of the input data given."
                )
        else:
            string_representation = cast(
                DataTypeTree, super().from_data(data=data, class_name=class_name)
            ).get_str_all_nodes(make_parent_class_inherit_from_original_type=False)

        self._create_custom_class_py(string_representation, class_name)
        if class_name in self._get_classes_added():
            return data
        self._add_new_class_to_loader_pyi(new_class=class_name)
        return data

    @staticmethod
    def _remove_docstrings(string: str) -> str:
        if '"""' not in string:
            return string

        strings = string.splitlines()
        for idx, string in enumerate(strings):
            strings[idx] = "" if '"""' in string else string
        return "\n".join(strings)

    @classmethod
    def reset(cls) -> None:
        """Remove all existing type hints generated by this class."""
        if cls._custom_class_dir_path.exists():
            shutil.rmtree(cls._custom_class_dir_path)
        if cls._this_file_pyi_path.exists():
            os.remove(cls._this_file_pyi_path)

    @final
    def _generate_this_file_pyi(self) -> PyFileModifier:
        content = Path(__file__).read_text()

        file_handler = PyFileModifier(content)
        file_handler.remove_all_method_bodies()
        file_handler.remove_all_private_methods()
        file_handler.remove_all_instance_variables(class_name=(type(self)).__name__)
        return file_handler

    def _create_custom_class_py(self, string: str, class_name: str) -> None:
        if not self._custom_class_dir_path.exists():
            os.makedirs(self._custom_class_dir_path)

        path = self._custom_class_dir_path / f"{class_name}.py"
        path.write_text(string)

    @final
    def _add_new_class_to_loader_pyi(self, *, new_class: str) -> None:
        self._add_class_created_to_this_file_pyi(new_class)
        self._add_import_to_this_file_pyi(new_class)
        for method_name in self._methods_to_be_overloaded:
            self._add_overload_to_this_file_pyi(new_class=new_class, method_name=method_name)

    @final
    def _add_import_to_this_file_pyi(self, new_class: str) -> None:
        import_statement = f"from lazy_type_hint.generators.build.{new_class} import {new_class}"
        self.this_file_pyi.add_imports(
            import_statement,
            in_type_checking_block=False,
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
                raise LazyTypeHintLiveError(f"No method `{method_name}` could be found")

            self.this_file_pyi.add_line(idx_lst[-1], f"{TAB}@overload")

        signature, _ = self.this_file_pyi.get_signature(method_name)

        # At this point idx is the index of the line where the input argument was found
        first_idx = signature.find(input_argument)
        if first_idx == -1:
            raise LazyTypeHintLiveError(f"No {input_argument} could be found within the signature {signature}")
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
            raise LazyTypeHintLiveError(f"No `{label}` was found in this file.")
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
        self._this_file_pyi_path.write_text(str(self.this_file_pyi))
