from abc import abstractmethod
from typing import (
    Hashable,
    Iterable,
    Iterator,
    List,
    Mapping,
    Sequence,
    Tuple,
    Union,
    final,
)

from typing_extensions import Self, override

from dynamic_pyi_generator.data_type_tree.data_type_tree import ChildStructure, DataTypeTree


class GenericDataTypeTree(DataTypeTree):
    """Tree that holds any kind of object that must contain other inner structures."""

    childs: ChildStructure[DataTypeTree]

    # Iterable-protocol related
    _iterator: Union[int, Iterator[Hashable]]

    @abstractmethod
    def _instantiate_childs(self, data: object) -> ChildStructure[DataTypeTree]:
        ...

    def get_type_alias_childs(self) -> str:
        """Get, in a format manner, a single string with all subtypes found within the generic structure.

        Examples:
            - Union[float, MyDict]
            - Union[float, MyDict, str]
            - MyDict
        """
        child_types = self._get_types()
        return self._format_types(child_types)

    def _format_types(self, child_types: Sequence[str]) -> str:
        """Given a collection of type or type aliases, format them.

        If multiple of them are given, a `Union` type will be used.
        """
        if len(child_types) == 1:
            return child_types[0]
        self.imports.add("Union")
        return f"Union[{', '.join(child_types)}]"

    @final
    def _get_types(self, iterable: Iterable[object] = (), *, remove_repeated: bool = True) -> Tuple[str, ...]:
        """
        Get the types of the generic data type tree. Child ones by default.

        This method keeps the order in case the structure used is an ordered one.

        Args:
            iterable (Iterable[object], optional): An iterable of objects. Defaults to an empty iterable.
            remove_repeated (bool, optional): Whether to remove repeated child types. Defaults to True.

        Returns:
            Tuple[str, ...]: A tuple containing the child types.
        """
        child_types: List[str] = []
        if iterable:
            child_types = [type(element).__name__ for element in iterable]
        else:
            for child in self:
                if not child.permission_to_be_created_as_type_alias:
                    child_types.append(child.get_str_top_node_without_lvalue())
                else:
                    child_types.append(child.name)
        if not child_types:
            self.imports.add("Any")
            child_types.append("Any")

        if remove_repeated:
            child_types_set = sorted(set(child_types))
            if "float" in child_types and "int" in child_types:
                child_types_set.remove("int")
            return tuple(sorted(child_types_set))
        return tuple(child_types)

    def __iter__(self) -> "Self":
        if isinstance(self.childs, Mapping):
            self._iterator = iter(self.childs.keys())
        else:
            self._iterator = 0  # Reset the index to zero when starting a new iteration
        return self

    @override
    def __next__(self) -> DataTypeTree:
        # Many type ignores here but everything is safe
        if isinstance(self.childs, Mapping):
            key = next(self._iterator, None)  # type: ignore
            if key is not None:
                return self.childs[key]
            else:
                raise StopIteration
        else:
            if self._iterator < len(self.childs):  # type: ignore
                element = list(self.childs)[self._iterator]  # type: ignore
                self._iterator += 1  # type: ignore
                return element
            else:
                raise StopIteration

    @override
    def _get_hash(self) -> Hashable:
        hashes: List[object] = []
        for child in self:
            hashes.append(child._get_hash())
        return tuple(hashes)
