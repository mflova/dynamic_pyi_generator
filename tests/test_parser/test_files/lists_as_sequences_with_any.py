from typing import Any
from typing import Sequence
from typing import Set
from typing import Tuple
from typing import TypedDict

NewClassNumbers = Sequence[Any]

NewClassNumbersTuple = Tuple[float, int]

NewClassKids = Sequence[Any]

NewClassRandomDict = TypedDict(
    "NewClassRandomDict",
    {
        "1$": int,
        "2 3": float,
    },
)

NewClassFavouriteColors = Set[str]

NewClassRandomData = Sequence[Any]

NewClassTupleExample = Tuple[int, str]

class NewClassAddress(TypedDict):
    street: str
    city: str
    state: str

class NewClass(TypedDict):
    name: str
    age: int
    numbers: NewClassNumbers
    numbers_tuple: NewClassNumbersTuple
    kids: NewClassKids
    random_dict: NewClassRandomDict
    favourite_colors: NewClassFavouriteColors
    random_data: NewClassRandomData
    tuple_example: NewClassTupleExample
    address: NewClassAddress