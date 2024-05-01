import os
import pickle
from abc import ABC
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    Callable,
    Optional,
    Sequence,
    TypeVar,
    Union,
)

from lazy_type_hint.data_type_tree import data_type_tree_factory
from lazy_type_hint.data_type_tree.data_type_tree import DataTypeTree
from lazy_type_hint.file_modifiers.yaml_file_modifier import YAML_COMMENTS_POSITION, YamlFileModifier
from lazy_type_hint.strategies import ParsingStrategies
from lazy_type_hint.utils import is_string_python_keyword_compatible


class LazyTypeHintError(Exception):
    """Raised by `LazyTypeHint` class."""


PathT = TypeVar("PathT", str, Path)


@dataclass(frozen=True)
class Tree:
    _tree: DataTypeTree

    def to_string(self, *, include_imports: bool = True) -> str:
        return self._tree.get_str_all_nodes(include_imports=include_imports)

    def to_file(self, path_to_py: Union[Path, str], *, create_non_existing_dir: bool = False) -> None:
        path_to_py = Path(path_to_py)
        if not path_to_py.exists():
            if not create_non_existing_dir:
                raise ValueError(
                    "The given directory does not exist and permissions to create the folder "
                    "(create_non_existing_dir input argument) were not set"
                )
            os.makedirs(path_to_py.parent)
        path_to_py.write_text(self.to_string(include_imports=True))


class LazyTypeHintABC(ABC):
    strategies: ParsingStrategies
    """Strategies to follow when parsing the objects."""

    def __init__(
        self,
        strategies: ParsingStrategies = ParsingStrategies(),  # noqa: B008
        **kwargs: Any,
    ) -> None:
        """Instantiate the tool. Pass strategies to be followed when creating type hints."""
        self.strategies = strategies

    def from_pickle_file(
        self,
        path: PathT,
        *,
        class_name: str,
    ) -> Any:
        """
        Type hint the data from a pickle file.

        Args:
            path: The path to the YAML file.
            class_name: The name of the class to use for deserialization.
        """
        with open(path, "rb") as f:
            data = pickle.load(f)
        return self.from_data(data, class_name=class_name)

    def from_yaml_file(
        self,
        loader: Callable[[PathT], object],
        path: PathT,
        *,
        class_name: str,
        comments_are: Optional[Union[YAML_COMMENTS_POSITION, Sequence[YAML_COMMENTS_POSITION]]] = "side",
        **kwargs: Any,
    ) -> Any:
        """
        Type hint the data from a YAML file.

        This method will also find and parse as docstrings the comments found.

        Args:
            loader: A callable that takes a `PathT` argument and returns an object.
            path: The path to the YAML file.
            class_name: The name of the class to use for deserialization.
            comments_are: The position of comments in the YAML file. Defaults to "side".
        """
        if comments_are is None:
            return self.from_data(loader(path), class_name=class_name)
        yaml_file_modifier = YamlFileModifier(path, comments_are=comments_are)
        original_data = loader(path)
        try:
            new_path: PathT = type(path)(yaml_file_modifier.create_temporary_file_with_comments_as_keys())
            potentially_modified_data = loader(new_path)
            return self.from_data(potentially_modified_data, class_name=class_name)
        except Exception:  # noqa: BLE001
            return self.from_data(original_data, class_name=class_name)

    def from_data(
        self,
        data: object,
        *,
        class_name: str,
        **kwargs: Any,
    ) -> Any:
        """
        Create type hints for the `data` given.

        Args:
            data (object): The data to create an instance from.
            class_name (str): The name of the class to create an instance of.
        """
        if not is_string_python_keyword_compatible(class_name):
            raise LazyTypeHintError(
                f"Given class_name is not compatible with Python class naming conventions: {class_name}"
            )
        return data_type_tree_factory(data, name=class_name, strategies=self.strategies)
