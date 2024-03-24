from typing import List, Tuple


def _split_string(string: str, *, max_line_length: int) -> Tuple[str, ...]:
    """
    Splits a string into substrings based on a maximum line length.

    Args:
        string (str): The input string to be split.
        max_line_length (int): The maximum length of each line.

    Returns:
        Tuple[str, ...]: A tuple of substrings, where each substring has a length less than or equal to the
            maximum line length.
    """
    substrings: List[str] = []
    for line in string.split("\n"):
        if not line:
            substrings.append("")
        words = line.split()
        current_substring = ""
        for word in words:
            if len(current_substring) + len(word) + 1 <= max_line_length:
                if current_substring:
                    current_substring += " " + word
                else:
                    current_substring = word
            else:
                if current_substring:
                    substrings.append(current_substring)
                current_substring = word
        if current_substring:
            substrings.append(current_substring)
    return tuple(substrings)


def format_string_as_docstring(string: str, *, max_line_length: int = 90, indentation: str = "") -> str:
    """
    Formats a string as a docstring.

    Args:
        string (str): The string to be formatted as a docstring.
        max_line_length (int, optional): The maximum line length for the docstring. Defaults to 90.
        indentation (str, optional): The indentation to be applied to each line of the docstring. Defaults to "".

    Returns:
        str: The formatted docstring.
    """
    string = string.rstrip("\n")
    if not string.endswith("."):
        string += "."
    docstring = '"""' + string + '"""'
    if len(docstring) <= max_line_length and "\n" not in docstring:
        return indentation + docstring
    substrings = _split_string(string, max_line_length=max_line_length)
    if len(substrings) == 1 and "\n" not in docstring:
        return indentation + docstring

    substrings = tuple([f"{indentation}{substring}" for substring in substrings])
    return f'{indentation}"""\n' + "\n".join(substrings) + f'\n{indentation}"""'
