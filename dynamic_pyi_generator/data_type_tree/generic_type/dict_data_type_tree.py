from functools import cached_property
from typing import TYPE_CHECKING, Dict, Hashable, KeysView, List, Mapping, NamedTuple, Optional, Sequence, cast

if TYPE_CHECKING:
    from typing_extensions import TypeGuard, override
else:
    override = lambda x: x

from dataclasses import dataclass
from typing import TypeVar

from dynamic_pyi_generator.data_type_tree.data_type_tree import DataTypeTree
from dynamic_pyi_generator.data_type_tree.generic_type.mapping_data_type_tree import MappingDataTypeTree
from dynamic_pyi_generator.strategies import ParsingStrategies
from dynamic_pyi_generator.utils import TAB, format_string_as_docstring, is_string_python_keyword_compatible

ValueT = TypeVar("ValueT")


@dataclass
class KeyInfo:
    docstring: str = ""
    required: bool = True


class DictMetadata:
    """
    Represents the profile of a dictionary data type.

    Attributes:
        is_typed_dict (bool): Indicates whether the dictionary is a TypedDict.
        is_functional_syntax (bool): Indicates whether the dictionary is defined using functional syntax.
    """

    _data: Dict[Hashable, object]
    _strategies: ParsingStrategies
    _initial_keys: KeysView[Hashable]

    hidden_key_preffix: str
    key_info: Dict[Hashable, KeyInfo]

    def __init__(
        self, data: Mapping[Hashable, object], *, hidden_key_preffix: str, strategies: ParsingStrategies
    ) -> None:
        self._data = data
        self._initial_keys = data.keys()
        self._strategies = strategies
        self.hidden_key_preffix = hidden_key_preffix
        self.key_info = {}
        self._update_key_info(force_all_required_to_true=True)

    @property
    def is_typed_dict(self) -> bool:
        if self._all_keys_are_string(self._data) and self._strategies.dict_strategy == "TypedDict":
            return True
        return False

    @property
    def is_functional_syntax(self) -> bool:
        if self._all_keys_are_string(self._data) and self._all_keys_are_parsable():
            return False
        return True

    @staticmethod
    def _all_keys_are_string(dct: Mapping[Hashable, ValueT]) -> "TypeGuard[Mapping[str, ValueT]]":
        return all(isinstance(key, str) for key in dct)

    def _all_keys_are_parsable(self) -> bool:
        if self._all_keys_are_string(self._data):
            return all(is_string_python_keyword_compatible(key) for key in self._data)
        return False

    def update(self, other: "DictMetadata") -> Mapping[Hashable, object]:
        for key, value in other._data.items():
            if key not in self._data:
                self._data[key] = value
        self._update_key_info(other._initial_keys)
        return self._data

    def _update_key_info(
        self, keys_that_were_introduced: Optional[KeysView[Hashable]] = None, force_all_required_to_true: bool = False
    ) -> None:
        docstrings = self.get_key_docstrings(docstring_keys_start_with=self.hidden_key_preffix)

        for key in self._data:
            if key not in self.key_info:
                if isinstance(key, str) and key.startswith(self.hidden_key_preffix):
                    continue
                if force_all_required_to_true:
                    self.key_info[key] = KeyInfo(required=True)
                else:
                    self.key_info[key] = KeyInfo(required=False)
            else:
                if key in docstrings:
                    self.key_info[key].docstring = docstrings[key]

        if not keys_that_were_introduced:
            return

        non_required_key: Hashable
        for non_required_key in set.difference(set(self._initial_keys), keys_that_were_introduced):
            if isinstance(non_required_key, str) and non_required_key.startswith(self.hidden_key_preffix):
                continue
            self.key_info[non_required_key].required = False

    def get_key_docstrings(
        self, *, docstring_keys_start_with: str = "", return_formatted_as_docstring: bool = False
    ) -> Mapping[Hashable, str]:
        if not docstring_keys_start_with:
            docstring_keys_start_with = self.hidden_key_preffix
        if not self._all_keys_are_string(self._data):
            return {}
        dct: Dict[str, str] = {}
        # Insert key docstrings
        for key in self._data:
            if not key.startswith(docstring_keys_start_with):  # Check key is not docstring based
                doc_key: str = f"{self.hidden_key_preffix}{key}"
                if doc_key in self._data:  # Check if there is key docstring
                    unformatted_docstring = self._data[doc_key]  # type: ignore
                    if not isinstance(unformatted_docstring, str):
                        continue
                    if return_formatted_as_docstring:
                        formated_docstring = (
                            "\n" + format_string_as_docstring(unformatted_docstring, indentation=TAB) + "\n"
                        )
                        dct[key] = formated_docstring
                    else:
                        dct[key] = unformatted_docstring
        return dct


class DictDataTypeTree(MappingDataTypeTree):
    wraps = dict  # type: ignore
    data: Dict[Hashable, object]
    dict_metadata: DictMetadata

    @staticmethod
    @override
    def _validate_name(name: str) -> None:  # noqa: ARG004
        """Removed name validation as the TypedDict can type any name."""
        return

    @override
    @property
    def permission_to_create_type_alias(self) -> bool:
        if self.dict_metadata.is_typed_dict:
            return True
        return super().permission_to_create_type_alias

    @override
    def __pre_child_instantiation__(self) -> None:
        self.dict_metadata = DictMetadata(
            self.data, hidden_key_preffix=self.hidden_keys_preffix, strategies=self.strategies
        )

    @override
    def __post_child_instantiation__(self) -> None:
        """TypedDicts are "forced" to have a type alias."""
        if self.dict_metadata.is_typed_dict:
            self._needs_type_alias = True

    @override
    def _get_str_top_node(self) -> str:
        if self.dict_metadata.is_typed_dict:
            childs_str_key = cast(Mapping[str, DataTypeTree], self.childs)
            return self._parse_typed_dict(childs=childs_str_key)
        else:
            return self._parse_dict(self.childs)

    def _parse_typed_dict(
        self,
        childs: Mapping[str, DataTypeTree],
    ) -> str:
        """
        Define the name of the keys and values for the current dictionary.

        If the name of a child type alias needs to be created, this one will use as a suffix the name
        of the associated key.

        Example:
            - address: AddressList
            - age: AgeInt
        """
        self.imports.add("TypedDict")

        content: Dict[str, str] = {}
        for key, value in childs.items():
            if isinstance(value, dict):
                type_value = f"{self.name}{self._to_camel_case(key)}"
                content[key] = type_value
            else:
                if not value.permission_to_create_type_alias:
                    content[key] = value.get_str_top_node_without_lvalue()
                else:
                    name = f"{self.name}{self._to_camel_case(key)}"
                    content[key] = name
        return self._build_typed_dict(
            name=self.name,
            content=content,
            functional_syntax=self.dict_metadata.is_functional_syntax,
            key_used_as_class_docstring=self.strategies.key_used_as_doc,
        )

    def _build_typed_dict(
        self,
        name: str,
        content: Mapping[str, str],
        *,
        functional_syntax: bool = False,
        key_used_as_class_docstring: str = "",
    ) -> str:
        """
        Build a typed dictionary based on the given name and content.

        Args:
            name (str): The name of the typed dictionary.
            content (Mapping[str, str]): The content of the typed dictionary, where each
                key-value pair represents a field and its type.
            functional_syntax (bool, optional): If True, use functional syntax to define
                the typed dictionary. Defaults to False.
            key_used_as_class_docstring (str, optional): The key to be used as the class docstring.
                This is a hidden one and it will not be represented in the final `TypedDict`.
                Defaults to an empty string.

        Returns:
            str: The string representation of the typed dictionary.
        """
        if functional_syntax:
            template = f"""{name} = TypedDict(
{TAB}"{name}",
{TAB}{{
{TAB}{TAB}"{{key}}": {{value}},
{TAB}}},
)"""
            idx_to_repeat = -3
        else:
            template = f"""class {name}(TypedDict):
{TAB}{{key}}: {{value}}{{optional_key_docstring}}"""
            idx_to_repeat = -1

        # Build the dictionary
        lines = template.splitlines()
        modified_line = ""
        key_docstrings = self.dict_metadata.get_key_docstrings(
            docstring_keys_start_with=self.hidden_keys_preffix, return_formatted_as_docstring=True
        )
        for key, value in content.items():
            if key.startswith(self.hidden_keys_preffix):  # Do not add artificially created keys
                continue
            if self.dict_metadata.is_functional_syntax:
                modified_line += lines[idx_to_repeat].format(key=key, value=value) + "\n"
            else:
                docstring = key_docstrings.get(key, "")
                modified_line += lines[idx_to_repeat].format(key=key, value=value, optional_key_docstring=docstring)
                if not docstring:
                    modified_line += "\n"
        lines[idx_to_repeat] = modified_line[:-1]

        # Append class docstring if found
        if key_used_as_class_docstring in self.data and key_used_as_class_docstring:
            lines = self._insert_class_docstring(lines, key_used_as_doc=key_used_as_class_docstring)
        return "\n".join(lines)

    def update(self, other: "DictDataTypeTree") -> None:
        self.data = self.dict_metadata.update(other.dict_metadata)

    def _insert_class_docstring(self, lines: Sequence[str], *, key_used_as_doc: str) -> List[str]:
        string = self.data[key_used_as_doc]
        lines = list(lines)
        if isinstance(string, str):
            indentation = "" if self.dict_metadata.is_functional_syntax else TAB
            docstring = format_string_as_docstring(string, indentation=indentation)
            if self.dict_metadata.is_functional_syntax:
                lines.insert(len(lines), docstring)
            else:
                lines.insert(1, docstring + "\n")
        return lines

    @override
    def _get_hash(self) -> Hashable:
        if not self.dict_metadata.is_typed_dict:
            return super()._get_hash()
        hashes: List[object] = []
        for name, child in self.childs.items():
            hashes.append(("typed_dict", name, child._get_hash()))
        return frozenset(hashes)
