"""This module groups common operations that are applied to both sets and sequences.

Although they present a total different behaviour at runtime, from the point of view of type
hinting they are quite similar.
"""

from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    FrozenSet,
    Iterable,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
    cast,
)

from dynamic_pyi_generator.data_type_tree.factory import data_type_tree_factory
from dynamic_pyi_generator.data_type_tree.generic_type.dict_data_type_tree import DictDataTypeTree, DictMetadata

if TYPE_CHECKING:
    from dynamic_pyi_generator.data_type_tree.data_type_tree import DataTypeTree
    from dynamic_pyi_generator.data_type_tree.generic_type.sequence_data_type_tree import SequenceDataTypeTree
    from dynamic_pyi_generator.data_type_tree.generic_type.set_data_type_tree import SetDataTypeTree


@dataclass(frozen=True)
class SetAndSequenceOperations:
    data_type_tree: "Union[SetDataTypeTree, SequenceDataTypeTree]"

    def instantiate_childs(self, data: Sequence[Any], *, allow_repeated_childs: bool) -> Tuple["DataTypeTree", ...]:
        """Instantiate the childs for sets and sequences.

        If `allow_repeated_childs` is set to True, all childs will be returned even if they are repeated.
        """
        if allow_repeated_childs:
            childs: Union[Set[DataTypeTree], List[DataTypeTree]] = []
        else:
            childs = set()
        names_added: Set[str] = set()

        for element in data:
            name = f"{self.data_type_tree.name}{type(element).__name__.capitalize()}"
            # Generate new name in case this one was already added
            if name in names_added:
                modified_name = name
                count = 2
                while modified_name in names_added:
                    modified_name = f"{name}{count}"
                    count += 1
                name = modified_name
            child = data_type_tree_factory(
                data=element,
                name=name,
                imports=self.data_type_tree.imports,
                depth=self.data_type_tree.depth + 1,
                parent=self.data_type_tree,
                strategies=self.data_type_tree.strategies,
            )
            if allow_repeated_childs:
                childs.append(child)  # type: ignore
                names_added.add(name)
            else:
                # Transfer all the information to the already added DictDataTypeTree child
                if child in childs and isinstance(child, DictDataTypeTree) and child.dict_metadata.is_typed_dict:
                    for child_added in childs:
                        if child == child_added and isinstance(child_added, DictDataTypeTree):
                            child_added.update(child)
                if child not in childs:
                    childs.add(child)  # type: ignore
                    names_added.add(name)

        return self._merge_typed_dicts(childs)

    def _merge_typed_dicts(
        self, childs: "Union[Set[DataTypeTree], Sequence[DataTypeTree]]"
    ) -> "Tuple[DataTypeTree, ...]":
        comparison = DictDataTypeTree.compare_multiple_typed_dicts_based_trees(
            *childs, ignore_functional_syntax_ones=True
        )
        if comparison.percentage_similarity < self.data_type_tree.strategies.merge_typed_dicts_if_similarity_above:
            return tuple(childs)

        # TODO: Merge all TypedDicts here. ONLY THE ONES WITH FUNCTIONAL SYNTAX
        # First TypedDict in the sequence will alreayd have all dictionary updated with all the data
        # Remember to leave only one of type `DictTypeDataTree`
        return tuple(childs)
