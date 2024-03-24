"""`DataTypeTree` object that creates a tree representing all container types within the data type given.

This data can then be parsed to a .py compatible file that will type hint your code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    FrozenSet,
    Hashable,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    final,
)

from dynamic_pyi_generator.strategies import ParsingStrategies
from dynamic_pyi_generator.utils import TAB, ImportManager, cache_returned_value, is_string_python_keyword_compatible

if TYPE_CHECKING:
    from typing_extensions import Self


class DataTypeTreeError(Exception):
    ...


DataTypeT = TypeVar("DataTypeT", bound=object)
ChildStructure = Union[FrozenSet[DataTypeT], Sequence[DataTypeT], Mapping[Hashable, DataTypeT]]
"""Different child structures that the Tree can hold."""


class DataTypeTree(ABC):
    """Tree that represents any kind of data with its inner structures."""

    name: str
    """Name that represents this node."""
    depth: int
    """Depth of the current node with respect to the whole tree."""
    height: int
    """Maximum height among all the child nodes."""
    data: object
    """Data that was given as input to parse.
    
    This one might have been modified with respect to the original one.
    """
    imports: ImportManager  # Unique one shared among the whole tree
    """Handle the imports required to generate the string representation."""
    parent: Optional[DataTypeTree]
    """Parent node (if any)."""
    childs: Optional[ChildStructure[DataTypeTree]]
    """All childs available within the tree."""
    holding_type: Type[object]
    """Type of input data given."""
    strategies: ParsingStrategies
    """Strategies to follow when parsing the data."""

    subclasses: ClassVar[Mapping[Type[object], Type[DataTypeTree]]] = {}
    """Available subclasses according to the type they are able to parse."""
    wraps: ClassVar[Union[Type[object], Sequence[Type[object]]]] = object
    """Object type that the tree is able to parse."""

    @final
    def __init__(
        self,
        data: object,
        name: str,
        *,
        imports: Optional[ImportManager] = None,
        depth: int = 0,
        strategies: ParsingStrategies = ParsingStrategies(),  # noqa: B008
        parent: Optional[DataTypeTree] = None,
    ) -> None:
        # Validation
        self._validate_name(name)
        wraps = self.wraps if isinstance(self.wraps, Iterable) else [self.wraps]
        if type(data) not in wraps:
            wraps_str = [element.__name__ for element in wraps]
            raise DataTypeTreeError(
                f"The given parser is meant to parse `{', '.join(wraps_str)}` data type but "
                f"{type(data).__name__} was given"
            )
        self.name = name
        self.holding_type = type(data)
        self.strategies = strategies
        self.depth = depth
        self.imports = ImportManager() if imports is None else imports
        self.childs = self._instantiate_childs(data)
        self.parent = parent
        self.height = self._get_height()
        self._needs_type_alias = False
        self.data = data
        self.__post_init__()

    def __post_init__(self) -> None:
        ...

    def _get_height(self) -> int:
        """Get maximum height of the current node in the tree."""
        max_height = 0
        for child in self:
            max_height = max(child.height, max_height)
        return max_height + 1

    @staticmethod
    def _validate_name(name: str) -> None:
        """CHeck that any given name is compatible with Python keyword naming rules."""
        if not is_string_python_keyword_compatible(name):
            raise DataTypeTreeError(f"The given name ({name}) is not Python-keyword compatible")

    @abstractmethod
    def _instantiate_childs(self, data: object) -> Optional[ChildStructure[DataTypeTree]]:
        """Instantiate the child structure that will be assigned to `self.childs`.

        This one will depend on how each subclass manage the child structure.
        """

    @final
    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Populate `subclasses` with all subclasses of this same class."""
        super().__init_subclass__(**kwargs)
        wraps = cls.wraps if isinstance(cls.wraps, Iterable) else [cls.wraps]
        for type_ in wraps:
            if type_ != object:
                if type_ in cls.subclasses:
                    raise DataTypeTreeError(f"A parser for {type_.__name__} was already found")
                cls.subclasses[type_] = cls  # type: ignore

    @abstractmethod
    def _get_hash(self) -> Hashable:
        """Get a unique hash that identifies the current data type."""

    @final
    def __hash__(self) -> int:
        """Unique hash that identifies whether the current tree is considered to be unique."""
        return hash(self._get_hash())

    @abstractmethod
    def _get_str_top_node(self) -> str:
        """Get the type alias or the representation only for the current self.

        It does not include childs.
        """

    @property
    def permission_to_create_type_alias(self) -> bool:
        """Parameter that indicates wheter the current trype is allowed to create a type alias.

        This will depend on the parsing strategy and on the fact that some trees require a type
        alias no matter the height.
        """
        for child in self:
            if child._needs_type_alias:
                return True
        return bool(self.height > self.strategies.min_height_to_define_type_alias)

    @final
    def get_str_top_node_without_lvalue(self) -> str:
        return self.get_str_top_node().split("=")[-1].strip()

    @final
    def get_str_top_node(self) -> str:
        return self._get_str_top_node()

    @final
    def get_str_all_nodes(self, include_imports: bool = True) -> str:
        """String that represents the .py file created from the tree."""
        return self._formatted_string(self._get_strs_all_nodes_unformatted(include_imports=include_imports))

    @final
    @cache_returned_value
    def _get_strs_all_nodes_unformatted(self, *, include_imports: bool = True) -> Tuple[str, ...]:
        if self.depth == 0 and not self.childs:
            return (self.get_str_top_node(),)  # It will return a type alias for simple data types
        if not self.childs:
            return ()

        class_representations: List[str] = []
        for child in self:
            if child.permission_to_create_type_alias:
                class_representations.extend(child._get_strs_all_nodes_unformatted(include_imports=False))
        class_representations.append(self.get_str_top_node())

        # These are available only when `get_str_py` is called
        if include_imports:
            return (self.imports.format(), *class_representations)
        return tuple(class_representations)

    @final
    def _formatted_string(self, strs_py: Sequence[str]) -> str:
        """Get the string representation of the type hints that represent the whole tree."""
        strs_py = list(strs_py)
        if not strs_py:
            return ""
        for idx, line in enumerate(strs_py):  # noqa: B007
            if "" in line:
                break
        strs_py[idx] = strs_py[idx] + "\n"  # Add extra separation between imports
        return "\n\n".join(strs_py)

    @final
    def __str__(self) -> str:
        """String that represents the .py file created from the tree."""
        return self.get_str_all_nodes(include_imports=True)

    @final
    def __repr__(self) -> str:
        strings: List[str] = []
        if self.depth == 0:
            strings.append(type(self).__name__)
        for child in self:
            strings.append(f"{TAB*child.depth} - {child}")
            strings.append(repr(child))
        return "\n".join(strings)

    @abstractmethod
    def __iter__(self) -> Self:
        """Get an iterator to iterate over the childs of the tree."""

    @final
    def __len__(self) -> int:
        """Number of childs within the tree."""
        if self.childs is None:
            return 0
        return len(self.childs)

    @abstractmethod
    def __next__(self) -> DataTypeTree:
        """Iterate over the childs of the tree."""

    @final
    def print_childs(self) -> None:
        print(repr(self))

    @final
    def __eq__(self, other_object: object) -> bool:
        if type(self) is type(other_object):
            return hash(self) == hash(other_object)
        return False
