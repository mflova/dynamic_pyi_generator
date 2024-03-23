from typing import TYPE_CHECKING, Any, List, Sequence, Tuple

from dynamic_pyi_generator.data_type_tree.data_type_tree import DataTypeTree, DataTypeTreeError
from dynamic_pyi_generator.data_type_tree.generic_type.generic_data_type_tree import (
    instantiate_childs_for_set_and_sequence,
)
from dynamic_pyi_generator.data_type_tree.generic_type.sequence_data_type_tree import (
    SequenceDataTypeTree,
)

if TYPE_CHECKING:
    from typing_extensions import override
else:
    override = lambda x: x


class ListDataTypeTree(SequenceDataTypeTree):
    wraps = list
    original_data = List[object]

    @override
    def _instantiate_childs(self, data: Sequence[Any]) -> Tuple[DataTypeTree, ...]:  # type: ignore
        return instantiate_childs_for_set_and_sequence(self, data, allow_repeated_childs=False)

    @override
    def _get_str_top_node(self) -> str:
        if self.strategies.list_strategy == "list":
            self.imports.add("list")
            container = "List"
        elif self.strategies.list_strategy == "Sequence":
            self.imports.add("Sequence")
            container = "Sequence"
        else:
            raise DataTypeTreeError(f"The chosen strategy ({self.strategies.list_strategy}) is not available.")
        return f"{self.name} = {container}[{self.get_type_alias_childs()}]"
