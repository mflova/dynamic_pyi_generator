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
                # Transfer all the information to the already added DictDataTypeTree child
                if child in childs and isinstance(child, DictDataTypeTree) and child.dict_metadata.is_typed_dict:
                    for child_added in childs:
                        if child == child_added and isinstance(child_added, DictDataTypeTree):
                            child_added.update(child)
                if child not in childs:
                    childs.add(child)  # type: ignore
                    names_added.add(name)

        return self._merge_typed_dicts(childs)

    @staticmethod
    def _merge_typed_dicts(childs: "Union[Set[DataTypeTree], Sequence[DataTypeTree]]") -> "Tuple[DataTypeTree, ...]":
        info = SetAndSequenceOperations._get_key_info_from_its_typed_dict_childs(childs)
        # TODO: IDK
        return childs

    @staticmethod
    def _transfer_hidden_keys(from_child: DictDataTypeTree, to_child: DictDataTypeTree) -> None:
        for hidden_key, docstring in from_child.dict_metadata.get_key_docstrings(
            return_formatted_as_docstring=False
        ).items():
            hidden_key = f"{DictDataTypeTree.hidden_keys_preffix}{hidden_key}"
            if hidden_key not in to_child.data:
                to_child.data[hidden_key] = docstring

    @staticmethod
    def _get_key_info_from_its_typed_dict_childs(childs: Iterable["DataTypeTree"]) -> Optional[MultipleTypedDictsInfo]:
        typed_dict_based_childs: Set[DictDataTypeTree] = set()
        for child in childs:
            if isinstance(child, DictDataTypeTree):
                if child.dict_metadata.is_typed_dict:
                    typed_dict_based_childs.add(child)

        if len(typed_dict_based_childs) < 2:
            return None

        keys_per_dictionary = [set(child.childs.keys()) for child in typed_dict_based_childs]
        common_keys = cast(Set[str], set.intersection(*keys_per_dictionary))
        total_keys = cast(Set[str], set.union(*keys_per_dictionary))
        non_common_keys = total_keys - common_keys
        return MultipleTypedDictsInfo(common_keys=common_keys, non_common_keys=non_common_keys)
