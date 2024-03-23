"""Automated script to run all code quality related tools over the entire repo."""

import argparse
import concurrent.futures
import multiprocessing
import os
import subprocess
import sys
from argparse import Namespace
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Any, Dict, Final, List, Optional, Tuple, Union

import yaml
from colorama import Fore, Style, init

if TYPE_CHECKING:
    from typing_extensions import Self

THIS_DIR: Final = os.path.dirname(__file__)
"""Absolute path to the folder holding this file."""
THIS_FILE: Final = os.path.basename(__file__)
"""Name of this file"""
TOML_FILE: Final = os.path.join(THIS_DIR, "pyproject.toml")
"""Absolute path to TOML file."""
ERR_MSG: Final = f"\n{Fore.LIGHTRED_EX}ERRORS WERE FOUND.{Style.RESET_ALL}"
"""Error message that will be displayed if something went wrong."""
OK_MSG: Final = f"\n{Fore.LIGHTGREEN_EX}EVERYTHING IS OK.{Style.RESET_ALL}"
"""Message that will be displayed if everything was ok."""

# Set up colorama
init(convert=True)

# Pre push hook
PRE_PUSH_TEMPLATE: Final = """#!/bin/sh

echo "\n"
echo "---------------RUNNING AUTOMATED LINTING--------------------------"
cd "{cwd}"
python3 -m poetry run python "{file}" --single-tool 'all linters'
if [ $? -eq 0 ]; then
  echo 'Everything is OK! Code will be pushed.'
  echo "-----------------------------------------------------------------\n"
  exit 0
else
  echo 'Errors found. Fix them, commit (or amend) the changes and try again.'
  echo "-----------------------------------------------------------------\n"
  exit 1
fi
"""


@dataclass
class Arguments:
    """Command lie arguments."""

    auto_linting: Optional[bool]
    """`True/False to enable disable auto linting. `None` to ignore it."""
    disable_parallel: bool
    """Disable any parallel execution of the tools."""
    only_run_tools: List[str]
    """Select multiple tools to run among the configured ones."""
    single_tool: str
    """Select a single tool to runa mong the configured ones."""
    cls: bool
    """Clear the terminal before calling the script."""

    def __post_init__(self) -> None:
        if self.single_tool and self.only_run_tools:
            raise ValueError("Only either `single-tool` or `only-run-tools` can be used.")

    @property
    def tools(self) -> Union[str, List[str]]:
        if self.single_tool:
            return self.single_tool
        return self.only_run_tools

    @classmethod
    def from_argparse(cls, args: Namespace) -> "Self":
        attributes: Dict[str, Any] = {}
        for field in fields(cls):
            if hasattr(args, field.name):
                attributes[field.name] = getattr(args, field.name)
        try:
            if auto_linting := attributes.get("auto_linting"):
                if "enable" in auto_linting.lower():
                    attributes["auto_linting"] = True
                elif "disable" in auto_linting.lower():
                    pass
                else:
                    raise ValueError(
                        f"Not recognized command for `auto_linting`: {auto_linting}. "
                        "Make sure that the keywords `enable` or `disable` are present."
                    )

            return cls(**attributes)
        except TypeError as error:
            raise ValueError(
                "Make sure that `argparse` defines all of the attributes defined in this class."
            ) from error


def parser_args() -> Arguments:
    parser = argparse.ArgumentParser(description="Description of your program.")

    parser.add_argument(
        "--auto-linting",
        type=str,
        help="`enable` or `disable` to perform automated linting before pushing.",
    )
    parser.add_argument(
        "--disable-parallel",
        action="store_true",
        default=True,
        help="Disable parallel runs.",
    )
    parser.add_argument(
        "--only-run-tools",
        default=[],
        nargs="*",
        help="Specify those tools that will be run.",
    )
    parser.add_argument("--single-tool", type=str, default="", help="Select a single tool to be run.")
    parser.add_argument(
        "--cls",
        action="store_true",
        default=False,
        help="Activate this flag to clear terminal.",
    )
    args = parser.parse_args()
    return Arguments.from_argparse(args)


def print_output(
    command: str,
    *,
    status: bool,
    tool_desc: str = "",
    suggestions: Iterable[str] = "",
    err_str: str = "",
    cli_command: str = "",
) -> None:
    """Pretty print the status or output returned from a linter.

    Args:
        command (str): Command used (typically name of the tool)
        status (bool): `True` if there were no problems. `False` otherwise.
        tool_desc (str, optional): Description of the tool that will be added to the
            message. Defaults to "".
        suggestions (Iterable[str], optional): Suggestions that will be printed if
            something went wrong.
        err_str (str, optional): Print the error string that was returned from the
            tool in case `status` is `False` (problems).
        cli_command (str, optional): Command used to get that message.
    """
    description = "" if not tool_desc else f" - {tool_desc}"
    if status is True:
        code = f"[{Fore.LIGHTGREEN_EX}OK{Style.RESET_ALL}]"
        print(f"{code} {command}{description}")
    else:
        # Put some indents
        err_lines = err_str.splitlines()
        prefix = "     "
        lines_with_prefix = [prefix + line for line in err_lines]
        err_str = "\n".join(lines_with_prefix)

        code = f"[{Fore.LIGHTRED_EX}NOK{Style.RESET_ALL}]"
        print(f"{code} {command}{description}")
        if cli_command:
            print(f" - Command used: {Fore.LIGHTYELLOW_EX}{cli_command}{Style.RESET_ALL}")
        if suggestions:
            if isinstance(suggestions, str):
                print(f" - {Fore.LIGHTYELLOW_EX}{suggestions}{Style.RESET_ALL}")
            else:
                for suggestion in suggestions:
                    print(f" - {Fore.LIGHTYELLOW_EX}{suggestion}{Style.RESET_ALL}")
        print(f" - Output from the tool: \n{err_str}\n")


def run_tool(
    tool: str,
    *,
    extra_args: str = "",
    path: str = "",
    tool_desc: str = "",
    suggestions: Iterable[str] = "",
    ignore: Iterable[str] = "",
    only_include: Optional[Iterable[str]] = None,
    pass_if_output_contains: Iterable[str] = "",
    display_output: bool = True,
    **kwargs: Any,  # noqa: ARG001
) -> bool:
    """Run a linter-based tool.

    Args:
        tool (str): Name of the tool used. It will be used as command in CLI.
        extra_args (str, optional): Extra arguments passed to the tool.
        path (str, optional): Specific path that tool should analyze.
        tool_desc (str, optional): Description of the tool to be more verbose.
            Defaults to "".
        suggestions (Iterable[str], optional): Messages that will be displayed as
            suggestion in case something went wrong.
        ignore (Iterable[str], optional): All those lines from the output (stderr)
            of the tool containing these strings will be not printed.
        only_include (Optional[Iterable[str]], optional): Only those lines from
            the output (stderr) of the tool containing these strings will be printed.
        pass_if_output_contains (Iterable[str], optional): Return code will be
            modified from NOK to OK if otuput string contains any of these.
        display_output: `False` to execute the command in silent mode.
        kwargs: Any other argument custom to the command.

    Returns:
        bool: `True` if the tool succeeded.
    """
    if path and not path.replace(" ", "").isalpha():
        path = f'"{path}"'
    full_command = f"python3 -m poetry run {tool} {extra_args} {path}"
    process = subprocess.Popen(
        full_command,
        shell=True,
        cwd=THIS_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    output, err = process.communicate()  # Capture the output of tool execution
    output_str, err_str = (
        output.decode("utf-8"),
        err.decode("utf-8"),
    )  # Decode the output to a string
    status = not bool(process.returncode) and "ERROR" not in output_str

    # Modify status if there are some specific keywords
    if pass_if_output_contains:
        for sub_str in pass_if_output_contains:
            if sub_str in output_str:
                status = True

    # For those tools that print errors into stdout instead of stderr,
    # copy problems into err_str
    if status is False:
        if output_str and not err_str:
            err_str = output_str

    # Filter output
    err_lines = err_str.splitlines()
    filtered_err_lines = [line for line in err_lines if not any([ignore_ in line for ignore_ in ignore])]
    if only_include:
        filtered_err_lines = [line for line in err_lines if any([only_ in line for only_ in only_include])]
    err_str = "\n".join(filtered_err_lines)

    if display_output:
        print_output(
            tool,
            status=status,
            tool_desc=tool_desc,
            suggestions=suggestions,
            err_str=err_str,
            cli_command=full_command,
        )
    return status


def setup_dmypy_server(dct: Mapping[str, Any], *, timeout: Optional[int] = None) -> Mapping[str, Any]:
    """Replace the normal `mypy` command.

    Replaced by one that performs the same action but with Daemon server.

    This is useful at it will speed up next executions.
    """
    if dct["tool"] != "mypy":
        return dct
    if dct["dmypy"]["enable"] is False:
        return dct
    is_dmypy_active = run_tool("dmypy", extra_args="status", display_output=False)
    dct_copy = dict(dct)
    if not is_dmypy_active:
        dct_copy["tool"] = "dmypy"
        if timeout:
            dct_copy["extra_args"] = f"run --timeout {timeout} --"
        else:
            dct_copy["extra_args"] = "run --"
    else:
        dct_copy["tool"] = "dmypy"
        dct_copy["extra_args"] = "check"
    return dct_copy


def run_tool_from_dct(dct: Mapping[str, Any]) -> bool:
    """Wrapper around `run_tool` that forwards all arguments to `run_tool`.

    Typically used for multiprocessing purposes.

    Args:
        dct (Mapping[str, Any]): Arguments forwarded.
    """
    if dct["tool"] == "mypy" and dct.get("dmypy", None):
        if "dmypy" in dct:
            if dct["dmypy"]:
                dct = setup_dmypy_server(dct, timeout=dct["dmypy"].get("timeout", None))
    return run_tool(**dct)


def _disable_auto_run() -> None:
    """Disable git pre-push hook implemented by this same script."""
    pre_push_path = os.path.join(THIS_DIR, ".git", "hooks", "pre-push")
    if os.path.isfile(pre_push_path):
        os.remove(pre_push_path)
    print(
        f"{Fore.LIGHTGREEN_EX}Auto run removed!{Style.RESET_ALL} No code verification "
        "will be done before pushin to online repo."
    )


def _setup_auto_run() -> None:
    """Enable git pre-push hook to run this script before pushing."""
    pre_push_path = os.path.join(THIS_DIR, ".git", "hooks", "pre-push")
    if os.path.isfile(pre_push_path):
        print("An automatic auto-run of this script is already set up.")
        return

    with open(pre_push_path, "w") as f:
        f.write(PRE_PUSH_TEMPLATE.format(cwd=THIS_DIR, file=THIS_FILE))
    print(
        f"{Fore.LIGHTGREEN_EX}Auto run enabled!{Style.RESET_ALL} Whenever you push to "
        "the online repo, code will be first checked."
    )


def read_and_parse_args(path: str = "") -> Tuple[Mapping[str, Any], ...]:
    """Read and parse the yaml file indicating tools to be run.

    Args:
        path (str, optional): Path to the yaml file.

    Returns:
        Tuple[Mapping[str, Any], ...]: Tuple being each element one call.
    """
    if not path:
        path = os.path.join(THIS_DIR, "check_code_args.yaml")
    with open(path) as f:
        all_args: List[Dict[str, Any]] = yaml.load(f, Loader=yaml.SafeLoader)

    # Check format
    if not isinstance(all_args, list):
        raise ValueError("Configuration must be shaped as a list.")

    # Check mandatory args
    for args in all_args:
        if "tool" not in args:
            raise ValueError("At least the tool must be defined.")

    # Parse . to absolute current dir
    for args in all_args:
        if "path" in args and args["path"] == ".":
            args["path"] = THIS_DIR

    return tuple(all_args)


def filter_tools_to_be_used(
    args: Tuple[Mapping[str, Any], ...], *, only_use_tools: Union[str, Sequence[str]]
) -> Tuple[Mapping[str, Any], ...]:
    """From the configuration options, remove all those tools that will not be used.

    Args:
        args (Tuple[Mapping[str, Any], ...]): Content of the configuration file.
        only_use_tools (Sequence[str]): Name of the only tools that will be used.

    Returns:
        Tuple[Mapping[str, Any], ...]: Filtered content of the configuration file.
    """
    if not only_use_tools:
        return args  # All tools

    only_use_tools_ = only_use_tools.lower() if isinstance(only_use_tools, str) else set(only_use_tools)
    if "all linters" in only_use_tools_:
        return tuple([arg for arg in args if arg["tool"] != "pytest"])

    filtered_args: List[Mapping[str, Any]] = []
    for arg in args:
        if arg["tool"] in only_use_tools_:
            filtered_args.append(arg)

    if not filtered_args:
        raise ValueError("No tools were chosen")

    return tuple(filtered_args)


def main() -> None:
    cli_args = parser_args()
    if cli_args.auto_linting is not None:
        if cli_args.auto_linting is True:
            _setup_auto_run()
        else:
            _disable_auto_run()
        return

    results: List[bool] = []
    args = read_and_parse_args()
    args = filter_tools_to_be_used(args, only_use_tools=cli_args.tools)
    num_workers = min(multiprocessing.cpu_count(), len(args))

    if cli_args.cls:
        subprocess.Popen("cls", shell=True)
    if cli_args.disable_parallel or len(args) <= 1:
        for args_ in args:
            results.append(run_tool_from_dct(args_))

    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(run_tool_from_dct, args_) for args_ in args]

            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)

    if False in results:
        print(ERR_MSG)
        sys.exit(1)
    print(OK_MSG)
    sys.exit(0)


if __name__ == "__main__":
    main()
