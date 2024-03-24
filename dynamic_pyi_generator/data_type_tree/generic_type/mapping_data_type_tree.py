import re
from types import MappingProxyType
from typing import TYPE_CHECKING, Dict, Final, Hashable, Iterator, List, Literal, Mapping, Set

from dynamic_pyi_generator.file_modifiers.yaml_file_modifier import YamlFileModifier

if TYPE_CHECKING:
    from typing_extensions import override
else:
    override = lambda x: x

from dynamic_pyi_generator.data_type_tree.data_type_tree import DataTypeTree
from dynamic_pyi_generator.data_type_tree.factory import data_type_tree_factory
from dynamic_pyi_generator.data_type_tree.generic_type.generic_data_type_tree import GenericDataTypeTree
from dynamic_pyi_generator.file_modifiers.yaml_file_modifier import YamlFileModifier


class MappingDataTypeTree(GenericDataTypeTree):
    childs: Mapping[Hashable, DataTypeTree]
    wraps = MappingProxyType
    original_data: Mapping[Hashable, object]
    hidden_keys_preffix: Final = YamlFileModifier.preffix

    # Iterable-protocol related
    _keys: Iterator[Hashable]

    @override
    def _instantiate_childs(self, data: Mapping[Hashable, object]) -> Mapping[Hashable, DataTypeTree]:  # type: ignore
        childs: Dict[Hashable, DataTypeTree] = {}
        for key, value in data.items():
            suffix = type(key).__name__ if not isinstance(key, str) else self._to_camel_case(key)
            if isinstance(key, str) and key.startswith(self.hidden_keys_preffix):
                continue
            childs[key] = data_type_tree_factory(
                data=value,
                name=f"{self.name}{suffix}",
                imports=self.imports,
                depth=self.depth + 1,
                strategies=self.strategies,
                parent=self,
            )
        return childs

    def _get_str_top_node(self) -> str:
        return self._parse_dict(self.childs)

    def _parse_dict(self, childs: Mapping[Hashable, DataTypeTree]) -> str:
        """Get a string representation of the dictionary for this same top node.

        Examples:
            - Mapping[str, Union[float, str]]
            - Mapping[str, str]
        """
        container: Literal["dict", "TypedDict", "MappingProxyType", "Mapping"] = (
            "dict" if self.strategies.dict_strategy == "TypedDict" else self.strategies.dict_strategy
        )
        if self.holding_type.__name__ == "mappingproxy":
            container = "MappingProxyType"
            self.imports.add(container)
        else:
            self.imports.add(container)

        keys = self._get_types(iterable=childs.keys(), remove_repeated=True)
        keys_str = self._format_types(keys)
        value_types = self.get_type_alias_childs()

        container_ = "Dict" if container == "dict" else container
        return f"{self.name} = {container_}[{keys_str}, {value_types}]"

    @staticmethod
    def _to_camel_case(string: str) -> str:
        """Make it camel case and compatible with Python keywords."""
        # Remove any initial number within the string
        match = re.match(r"^\d+", string)
        if match:
            number = match.group()
            string = string[len(number) :]

        new_string = [""] * len(string)
        idx_to_remove: Set[int] = set()
        removed = False
        for idx, char in enumerate(string):
            if not char.isalpha() and not char.isnumeric():
                idx_to_remove.add(idx)
            if idx not in idx_to_remove:
                if removed is True:
                    new_string[idx] = string[idx].upper()
                    removed = False
                else:
                    new_string[idx] = string[idx]
            else:
                removed = True

        new_string[0] = new_string[0].upper()
        return "".join(new_string)

    @override
    def _get_hash(self) -> Hashable:
        hashes: List[object] = []
        for name, child in self.childs.items():
            hashes.append(("mapping", hash(type(name)), child._get_hash()))
        return frozenset(hashes)
