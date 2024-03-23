from typing import Any

import pytest

from dynamic_pyi_generator.utils import TAB
from dynamic_pyi_generator.utils.import_manager import ImportManager


@pytest.fixture
def import_manager() -> ImportManager:
    return ImportManager()


@pytest.fixture(autouse=True)
def _assert_valid_code(import_manager: ImportManager) -> Any:
    yield
    try:
        exec(import_manager.format())
    except Exception as error:  # noqa: BLE001
        pytest.fail(f"Code generated is not valid: {error}")


class TestAdd:
    def test_import_manager_add(self, import_manager: ImportManager) -> None:
        import_manager.add("list").add("tuple").add("dict")
        assert import_manager._set == {"list", "tuple", "dict"}


class TestFormatSinglePackage:
    def test_import_manager_format_single_package(self, import_manager: ImportManager) -> None:
        import_manager.add("list").add("tuple").add("dict").add("MappingProxyType")
        formatted_imports = import_manager._format_single_package("typing", ["List", "Tuple", "Dict"], line_length=80)
        expected_output = "from typing import Dict, List, Tuple"
        assert formatted_imports == expected_output

    def test_import_manager_format_single_package_long_line(self, import_manager: ImportManager) -> None:
        formatted_imports = import_manager._format_single_package("typing", ["List", "Tuple", "Dict"], line_length=30)
        expected_output = f"from typing import (\n{TAB}Dict,\n{TAB}List,\n{TAB}Tuple,\n)"
        assert formatted_imports == expected_output


class TestFormat:
    def test_import_manager_format_short_line(self, import_manager: ImportManager) -> None:
        import_manager.add("list").add("tuple").add("dict").add("MappingProxyType")
        formatted_imports = import_manager.format(line_length=120)
        expected_output = """from types import MappingProxyType
from typing import Dict, List, Tuple"""
        assert expected_output == formatted_imports

    def test_import_manager_format_long_line(self, import_manager: ImportManager) -> None:
        import_manager.add("list").add("tuple").add("dict").add("MappingProxyType")
        formatted_imports = import_manager.format(line_length=35)
        expected_output = """from types import MappingProxyType
from typing import (
    Dict,
    List,
    Tuple,
)"""

        assert expected_output == formatted_imports

    def test_import_manager_format_no_imports(self, import_manager: ImportManager) -> None:
        formatted_imports = import_manager.format(line_length=80)
        expected_output = ""
        assert expected_output == formatted_imports
