from typing import Any, List, Sequence, Tuple

from typing_extensions import override

from dynamic_pyi_generator.data_type_tree.data_type_tree import DataTypeTree, DataTypeTreeError
from dynamic_pyi_generator.data_type_tree.generic_type.sequence_data_type_tree import (
    SequenceDataTypeTree,
)


class ListDataTypeTree(SequenceDataTypeTree):
    wraps = list
    original_data = List[object]

    @override
    def _instantiate_childs(self, data: Sequence[Any]) -> Tuple[DataTypeTree, ...]:  # type: ignore
        return self.operations.instantiate_childs(data, allow_repeated_childs=False)

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
