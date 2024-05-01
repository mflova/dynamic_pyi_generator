import os
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

from lazy_type_hint.data_type_tree.data_type_tree import DataTypeTree
from lazy_type_hint.file_modifiers.yaml_file_modifier import YAML_COMMENTS_POSITION
from lazy_type_hint.generators.lazy_type_hint_abc import LazyTypeHintABC
from lazy_type_hint.strategies import ParsingStrategies


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
        if not path_to_py.parent.exists():
            if not create_non_existing_dir:
                raise ValueError(
                    "The given directory does not exist and permissions to create the folder "
                    "(create_non_existing_dir input argument) were not set"
                )
            os.makedirs(path_to_py.parent)
        path_to_py.write_text(self.to_string(include_imports=True))


class LazyTypeHint(LazyTypeHintABC):
    strategies: ParsingStrategies
    """Strategies to follow when parsing the objects."""

    def __init__(
        self,
        strategies: ParsingStrategies = ParsingStrategies(),  # noqa: B008
        **kwargs: Any,
    ) -> None:
        self.strategies = strategies

    def from_pickle_file(
        self,
        path: PathT,
        *,
        class_name: str,
    ) -> Tree:
        return super().from_pickle_file(path=path, class_name=class_name)

    def from_yaml_file(
        self,
        loader: Callable[[PathT], object],
        path: PathT,
        *,
        class_name: str,
        comments_are: Optional[Union[YAML_COMMENTS_POSITION, Sequence[YAML_COMMENTS_POSITION]]] = "side",
        **kwargs: Any,
    ) -> Tree:
        return super().from_yaml_file(loader=loader, path=path, class_name=class_name, comments_are=comments_are)  # type: ignore

    def from_data(
        self,
        data: object,
        *,
        class_name: str,
        **kwargs: Any,
    ) -> Tree:
        return Tree(super().from_data(data=data, class_name=class_name))
