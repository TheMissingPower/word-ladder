"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    IS_WORD = "is_word"
    PIN_PUZZLE = "pin_puzzle"
    NEIGHBORS = "neighbors"


class Task(Enum):
    SOLVE_LADDER = "solve-ladder"


START = "The start word: 4 lowercase ASCII letters, e.g. cold"
END = "The end word: 4 lowercase ASCII letters, e.g. warm"
# The most words one neighbors call takes.
MAX_NEIGHBOR_WORDS = 25


@dataclass
class LadderInput(Output):
    start: Annotated[str, START]
    end: Annotated[str, END]


@dataclass
class LadderOutput(Output):
    solvable: Annotated[bool, "Whether a ladder from start to end exists"]
    ladder: Annotated[
        list[str],
        "A shortest ladder: start first, end last, each next word one letter different; [] when solvable is false",
    ]


@dataclass
class IsWordInput(Output):
    word: Annotated[str, "The word to look up, e.g. cord"]


@dataclass
class IsWordOutput(Output):
    word: Annotated[str, "The word, as given"]
    is_word: Annotated[bool, "Whether the word is in the puzzle dictionary, the 4-letter words of ENABLE"]


@dataclass
class NeighborsInput(Output):
    words: Annotated[list[str], "1 to 25 dictionary words to expand, e.g. [\"cold\", \"warm\"]"]


@dataclass
class WordNeighbors(Output):
    word: Annotated[str, "A word asked about, as given"]
    neighbors: Annotated[list[str], "Every dictionary word one letter different from it, in alphabetical order"]


@dataclass
class NeighborsOutput(Output):
    results: Annotated[list[WordNeighbors], "One entry per word asked about, in the order asked"]


@dataclass
class PuzzleOutput(Output):
    start: Annotated[str, START]
    end: Annotated[str, END]
    solvable: Annotated[bool, "Whether a ladder from start to end exists in the dictionary"]
    optimal_length: Annotated[int | None, "The number of words in a shortest ladder, both ends included; null when unsolvable"]


TOOLS = {
    Tool.IS_WORD: (IsWordInput, IsWordOutput),
    Tool.PIN_PUZZLE: (LadderInput, PuzzleOutput),
    Tool.NEIGHBORS: (NeighborsInput, NeighborsOutput),
}
TASKS = {
    Task.SOLVE_LADDER: (LadderInput, LadderOutput),
}
