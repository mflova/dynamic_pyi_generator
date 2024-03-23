from dataclasses import dataclass, fields
from typing import Literal, get_args, get_type_hints

LIST_STRATEGIES = Literal["Sequence", "list"]
TUPLE_SIZE_STRATEGIES = Literal["fixed", "any size"]
MAPPING_STRATEGIES = Literal["TypedDict", "Mapping", "dict"]


@dataclass(frozen=True)
class ParsingStrategies:
    list_strategy: LIST_STRATEGIES = "list"
    tuple_size_strategy: TUPLE_SIZE_STRATEGIES = "fixed"
    dict_strategy: MAPPING_STRATEGIES = "TypedDict"
    min_height_to_define_type_alias: int = 1
    key_used_as_doc: str = ""

    def __post_init__(self) -> None:
        type_hints = get_type_hints(self)
        for field in fields(type(self)):
            allowed_values = get_args(type_hints[field.name])
            if allowed_values and getattr(self, field.name) not in allowed_values:
                raise ValueError(
                    f"Invalid value for {field.name}. Expected any of ({', '.join(allowed_values)}) but got "
                    f"{getattr(self, field.name)}"
                )
        if self.min_height_to_define_type_alias < 0:
            raise ValueError("`min_height_to_define_type_alias` must be greater or equal than 0")
