# TODO

TODO:
- Test: Check that the `input_data` is not modified by any mean
- Refactor: Create a new module called SequenceSetOperations. This one will
contain the function that instantiates the childs but also the operations that will be
used in the feature commented below.
- Include some kind of pytest coverage.
- New feature: Possibility to merge ALL dictionaries
within a sequence/set. Add a new strategy parameter called:
`merge_typed_dicts_if_similarity_is_above_percentage` Feature itself would merge
dictionaries if:
    - At least 1 key is shared in common among ALL dictionaries
    - If this percentage is higher
    If these conditions are met, two scenarios are possible:
      - Among the repated keys, all values are the same type:
        - In this case, create a normal `TypedDict` that uses `NotRequried` for the non
          common keys.
      - Among the repated keys, some value types are different:
        - Continue using `NotRquired` for those non repeated keys.
        - In such case, merge them with `Union` operator


Backlog:

feat:

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

- Rename main class
- Make it easier to import for users
- Try to fix type: ignore


docs:

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
