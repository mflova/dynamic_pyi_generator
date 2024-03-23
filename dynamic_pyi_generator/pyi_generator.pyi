import os
import re
import shutil
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable, Dict, Final, Literal, Mapping, Sequence, Tuple, TypeVar, Union, final, overload
import dynamic_pyi_generator
from dynamic_pyi_generator.data_type_tree import data_type_tree_factory
from dynamic_pyi_generator.file_handler import FileHandler
from dynamic_pyi_generator.strategies import ParsingStrategies
from dynamic_pyi_generator.utils import TAB, compare_str_via_ast, is_string_python_keyword_compatible
if TYPE_CHECKING:
    from dynamic_pyi_generator.build.Example import Example
    from typing_extensions import TypeAlias
THIS_DIR = Path(__file__).parent

class PyiGeneratorError(Exception):
    """Raised by `PyiGenerator` class."""
ObjectT = TypeVar('ObjectT')

class PyiGenerator:
    classes_created: 'TypeAlias' =Union[Literal["Example"], Any]
    'Classes created by the class. Do not modify.'
    @final
    def __init__(self, *, strategies: ParsingStrategies=ParsingStrategies(), if_interface_exists: Literal['overwrite', 'validate']='validate', generated_classes_custom_dir: Tuple[Union[ModuleType, str], ...]=(dynamic_pyi_generator, 'build')) -> None:...

    @overload
    def from_file(self, loader: Callable[[str], ObjectT], path: str, class_name: Literal["Example"]) -> Example:...
    @overload
    def from_file(self, loader: Callable[[str], ObjectT], path: str, class_name: str) -> ObjectT:...

    @overload
    def from_data(self, data: ObjectT, class_name: Literal["Example"]) -> Example:...
    @overload
    def from_data(self, data: ObjectT, class_name: str) -> ObjectT:...

    def reset(self) -> None:...
