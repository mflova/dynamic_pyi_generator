from typing import TYPE_CHECKING, Hashable, List, Sequence

if TYPE_CHECKING:
    from typing_extensions import override
else:
    override = lambda x: x

from dynamic_pyi_generator.data_type_tree.generic_type.generic_data_type_tree import (
    GenericDataTypeTree,
)
from dynamic_pyi_generator.data_type_tree.generic_type.set_and_sequence_operations import SetAndSequenceOperations


class SequenceDataTypeTree(GenericDataTypeTree):
    original_data = Sequence[object]
    operations: SetAndSequenceOperations

    @override
    def __pre_child_instantiation__(self) -> None:
        self.operations = SetAndSequenceOperations(self)

    @override
    def _get_hash(self) -> Hashable:
        hashes: List[object] = []
        for child in self:
            hashes.append(child._get_hash())
        return frozenset(hashes)
