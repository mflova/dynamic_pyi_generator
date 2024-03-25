from typing import TYPE_CHECKING, Any, FrozenSet, Hashable, Literal, Sequence, Set, Tuple, Union

if TYPE_CHECKING:
    from typing_extensions import override
else:
    override = lambda x: x

from dynamic_pyi_generator.data_type_tree.data_type_tree import DataTypeTree
from dynamic_pyi_generator.data_type_tree.generic_type.generic_data_type_tree import (
    GenericDataTypeTree,
)
from dynamic_pyi_generator.data_type_tree.generic_type.set_and_sequence_operations import SetAndSequenceOperations


class SetDataTypeTree(GenericDataTypeTree):
    wraps = (frozenset, set)
    childs: Sequence[DataTypeTree]
    original_data: Union[Set[object], FrozenSet[object]]
    operations: SetAndSequenceOperations

    @override
    def __pre_child_instantiation__(self) -> None:
        self.operations = SetAndSequenceOperations(self)

    @override
    def _instantiate_childs(self, data: Sequence[Any]) -> Tuple[DataTypeTree, ...]:  # type: ignore
        return self.operations.instantiate_childs(data, allow_repeated_childs=False)

    @override
    def _get_str_top_node(self) -> str:
        container: Literal["FrozenSet", "set"] = "FrozenSet" if self.holding_type is frozenset else "set"
        self.imports.add(container)

        if container == "FrozenSet":
            return f"{self.name} = FrozenSet[{self.get_type_alias_childs()}]"
        return f"{self.name} = Set[{self.get_type_alias_childs()}]"

    @override
    def _get_hash(self) -> Hashable:
        hashes: Set[object] = set()
        for child in self:
            hashes.add(child._get_hash())
        return frozenset(hashes)
