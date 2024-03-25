"""This module groups common operations that are applied to both sets and sequences.

Although they present a total different behaviour at runtime, from the point of view of type
hinting they are quite similar.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, FrozenSet, List, Literal, Mapping, Optional, Sequence, Set, Tuple, Union, cast

from dynamic_pyi_generator.data_type_tree.factory import data_type_tree_factory
from dynamic_pyi_generator.data_type_tree.generic_type.dict_data_type_tree import DictDataTypeTree

if TYPE_CHECKING:
    from dynamic_pyi_generator.data_type_tree.data_type_tree import DataTypeTree
    from dynamic_pyi_generator.data_type_tree.generic_type.sequence_data_type_tree import SequenceDataTypeTree
    from dynamic_pyi_generator.data_type_tree.generic_type.set_data_type_tree import SetDataTypeTree


@dataclass(frozen=True)
class MultipleTypedDictsInfo:
    common_keys: Set[str] = field(default_factory=set)
    non_common_keys: Set[str] = field(default_factory=set)
    types_info: Mapping[str, Sequence[str]] = field(default_factory=dict)

    @property
    def percentage_similarity(self) -> int:
        total_keys = len(self.common_keys) + len(self.non_common_keys)
        return int(100 * (len(self.common_keys) / total_keys))


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
                if child not in childs:
                    childs.add(child)  # type: ignore
                    names_added.add(name)
        return tuple(childs)

    def _get_key_info_from_its_typed_dict_childs(self) -> Optional[MultipleTypedDictsInfo]:
        typed_dict_based_childs: Set[DictDataTypeTree] = set()
        for child in self.data_type_tree:
            if isinstance(child, DictDataTypeTree):
                if child.dict_profile.is_typed_dict:
                    typed_dict_based_childs.add(child)

        if len(typed_dict_based_childs) < 2:
            return None

        keys_per_dictionary = [set(child.childs.keys()) for child in typed_dict_based_childs]
        common_keys = cast(Set[str], set.intersection(*keys_per_dictionary))
        total_keys = cast(Set[str], set.union(*keys_per_dictionary))
        non_common_keys = total_keys - common_keys
        return MultipleTypedDictsInfo(common_keys=common_keys, non_common_keys=non_common_keys)
