from typing import TYPE_CHECKING, Any, Literal, Sequence, Set, Tuple

if TYPE_CHECKING:
    from typing_extensions import override
else:
    override = lambda x: x

from dynamic_pyi_generator.data_type_tree.data_type_tree import DataTypeTree
from dynamic_pyi_generator.data_type_tree.generic_type.generic_data_type_tree import (
    GenericDataTypeTree,
    get_childs_for_set_and_sequence,
)


class SetDataTypeTree(GenericDataTypeTree):
    wraps = (frozenset, set)
    childs: Sequence[DataTypeTree]

    @override
    def _get_childs(self, data: Sequence[Any]) -> Tuple[DataTypeTree, ...]:  # type: ignore
        return get_childs_for_set_and_sequence(self, data, allow_repeated_childs=False)

    @override
    def _get_str_py(self) -> str:
        container: Literal["FrozenSet", "set"] = "FrozenSet" if self.holding_type is frozenset else "set"
        self.imports.add(container)

        if container == "FrozenSet":
            return f"{self.name} = FrozenSet[{self.get_type_alias_childs()}]"
        return f"{self.name} = Set[{self.get_type_alias_childs()}]"

    @override
    def _get_hash(self) -> object:
        hashes: Set[object] = set()
        for child in self:
            hashes.add(child._get_hash())
        return frozenset(hashes)
