from typing import TYPE_CHECKING, Hashable, Union

if TYPE_CHECKING:
    from typing_extensions import Self, override
else:
    override = lambda x: x

from dynamic_pyi_generator.data_type_tree.data_type_tree import DataTypeTree


class SimpleDataTypeTree(DataTypeTree):
    """Tree that holds any kind of object that cannot container inner structures."""

    childs: None
    wraps = (bool, int, float, range, slice, str, type(None))
    original_data = Union[bool, int, float, range, slice, str, None]

    @override
    def _instantiate_childs(self, data: Union[bool, float, str]) -> None:  # type: ignore  # noqa: ARG002
        return None

    @override
    def _get_str_top_node(self) -> str:
        if self.holding_type.__name__ == "NoneType":
            self.imports.add("Optional")
            return f"{self.name} = Optional[object]"
        return f"{self.name} = {self.holding_type.__name__}"

    @override
    def __iter__(self) -> "Self":
        return self

    @override
    def __next__(self) -> DataTypeTree:
        raise StopIteration

    @override
    def _get_hash(self) -> Hashable:
        return id(self.holding_type)

    @override
    def _get_height(self) -> int:
        return 0

    @override
    @property
    def permission_to_create_type_alias(self) -> bool:
        return False
