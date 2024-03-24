from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Final, List, Literal, Mapping, Sequence, Set, Tuple

from dynamic_pyi_generator.utils.utils import TAB

if TYPE_CHECKING:
    from typing_extensions import Self, TypeAlias

KEYWORDS_AVAILABLE: "TypeAlias" = Literal[
    "list",
    "Sequence",
    "tuple",
    "set",
    "FrozenSet",
    "dict",
    "Mapping",
    "MappingProxyType",
    "TypedDict",
    "Any",
    "Union",
    "Optional",
]


@dataclass(frozen=True)
class ImportManager:
    _set: Set[KEYWORDS_AVAILABLE] = field(default_factory=set)

    TEMPLATE: Final[str] = field(init=False, default="from {package} import {name}")
    PACKAGE: Mapping[KEYWORDS_AVAILABLE, Tuple[str, ...]] = field(
        default_factory=lambda: {
            "list": ("typing", "List"),
            "Sequence": ("typing", "Sequence"),
            "tuple": ("typing", "Tuple"),
            "set": ("typing", "Set"),
            "FrozenSet": ("typing", "FrozenSet"),
            "dict": ("typing", "Dict"),
            "Mapping": ("typing", "Mapping"),
            "MappingProxyType": ("types", "MappingProxyType"),
            "TypedDict": ("typing", "TypedDict"),
            "Any": ("typing", "Any"),
            "Union": ("typing", "Union"),
            "Optional": ("typing", "Optional"),
        }
    )

    def add(self, keyword: KEYWORDS_AVAILABLE) -> "Self":
        self._set.add(keyword)
        return self

    def format(self, *, line_length: int = 90) -> str:
        import_statements: Dict[str, List[str]] = defaultdict(list)
        for keyword in self._set:
            try:
                reference = self.PACKAGE[keyword]
            except KeyError as error:
                raise ValueError(
                    f"The given keyword `{keyword}` could not be located among the available imports: "
                    f"{''.join(self.PACKAGE.keys())}"
                ) from error
            import_statements[".".join(reference[:-1])].append(reference[-1])

        imports_lst: List[str] = []
        for package, imports in sorted(import_statements.items(), key=lambda x: x[0]):
            imports_lst.append(self._format_single_package(package, imports, line_length=line_length))
        return "\n".join(imports_lst)

    def _format_single_package(self, package: str, imports: Sequence[str], *, line_length: int) -> str:
        string = self.TEMPLATE.format(package=package, name=", ".join(sorted(imports)))
        if len(string) > line_length:
            name = f",\n{TAB}".join(sorted(imports))
            string = self.TEMPLATE.format(package=package, name=f"(\n{TAB}{name}")
            string += ",\n)"
        return string
