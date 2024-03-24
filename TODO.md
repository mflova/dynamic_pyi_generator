# TODO


feat:

- Strategy: Type hint Type aliases and keys within typedDict as `Final`?
- Parsing docs: What happens if there is a list of same dictionaries and one comment is added to only one key within one of the list elements?
- Create `TypedDict` with docstrings if those are present within a file
  - Ideas: Two modes:
    - Either giving a specific key that will be used specifically for docs
    - yaml: Or using the # symbols to detect comments and pre-parse the document to modify
      those lines as a new key within that dictionary. This key will be a reserved word like __doc
- Make it compatible with different Python versions.This include:
  - Migration for some of the classes from `typing` to `collections.abc`
  - Use of `list` instead of `typing.List`
- Generating `.py` files locally:
  - Allow different subfolders
  - Think from a collaborative point of view: Think that the `.pyi` file will not be up
    to date. Therefore I cannot use it to check the existing `.py` files
  - Ideas:
    - Have a file in the root of the repo that will keep track of all custom classes created.
    - Detect that these are generated custom classes by looking at the header "Do not modify"

refactor:

- Move as much as I can into TYPE_CHECKING block
- Related to the tree, make as many generators as I can
- Remove unused methods/functions/attributes
- Remove unused methods
- Rename some methods
- Rename main class
- Make it easier to import for users
- Refactor imports
- Try to fix type: ignore


docs:

- Better docstrings (specially for parsers)
- Edit README.md:
  - Explain some differences like: "Cattrs or pydantic require knowing the structure you
    want to cast beforehand. They are validation-oriented. Although my tool can be used
    for validation, it is more geared towards providing better type hints and ensuring
    that the structure is accessed correctly. Stubgen generates the pyi file for you, but
    then you have to work with files until you can use it. It's not always easy to
    organize.

ci:

- Setup pipelines
- Setup branch protection

tests:
- Test tht the pyi file generated is not broken. Read its string, compile and exec
- test main API features:
    - Add flag "if intefcace exists = Literal["validate", "overwrite"]"
