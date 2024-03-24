import os
import re
import shutil
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable, Dict, Final, Literal, Mapping, Sequence, Tuple, TypeVar, Union, final, overload
import dynamic_pyi_generator
from dynamic_pyi_generator.data_type_tree import data_type_tree_factory
from dynamic_pyi_generator.file_modifiers.py_file_modifier import PyFileModifier
from dynamic_pyi_generator.file_modifiers.yaml_file_modifier import YAML_COMMENTS_POSITION, YamlFileModifier
from dynamic_pyi_generator.strategies import ParsingStrategies
from dynamic_pyi_generator.utils import TAB, compare_str_via_ast, is_string_python_keyword_compatible
if TYPE_CHECKING:
    from typing_extensions import TypeAlias
THIS_DIR = Path(__file__).parent

class PyiGeneratorError(Exception):
    """Raised by `PyiGenerator` class."""
ObjectT = TypeVar('ObjectT')
PathT = TypeVar('PathT', str, Path)

class PyiGenerator:
    classes_created: 'TypeAlias' = Any
    'Classes created by the class. Do not modify.'
    @final
    def __init__(self, *, strategies: ParsingStrategies=ParsingStrategies(), if_interface_exists: Literal['overwrite', 'validate']='validate', generated_classes_custom_dir: Tuple[Union[ModuleType, str], ...]=(dynamic_pyi_generator, 'build')) -> None:...

    def from_yaml_file(self, loader: Callable[[PathT], ObjectT], path: PathT, *, class_name: str, comments_are: Union[YAML_COMMENTS_POSITION, Sequence[YAML_COMMENTS_POSITION]]) -> ObjectT:...

    def from_data(self, data: ObjectT, class_name: str) -> ObjectT:...

    def reset(self) -> None:...
