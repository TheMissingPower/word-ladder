"""The frozen puzzles (data/puzzles.json, made once by generate_puzzles.py) and the task's answer key.

pin_puzzle answers any pair of dictionary words whose search fits the hosted limits (plugin.search's live), not
only the frozen ones: every pair with a 3-word ladder, a 4-word ladder whose search stays small, or no ladder when
a side runs out of words quickly. It refuses any other pair with the reason, before the agent starts.
"""

from __future__ import annotations

import json
from pathlib import Path

from contract import LadderInput, PuzzleOutput
from plugin.dictionary import DATA, WORDS, distances
from plugin.search import LIVE_CALL_WORDS, LIVE_CALLS, two_sided_search

PUZZLES = DATA / "puzzles.json"


def load_puzzles() -> list[PuzzleOutput]:
    return [PuzzleOutput(**puzzle) for puzzle in json.loads(PUZZLES.read_text(encoding="utf-8"))]


def pin_puzzle(given: LadderInput, workspace: Path) -> PuzzleOutput:
    for puzzle in load_puzzles():
        if (puzzle.start, puzzle.end) == (given.start, given.end):
            return puzzle
    return answer_key(given.start, given.end)


def answer_key(start: str, end: str) -> PuzzleOutput:
    """The answer key of a pair that is not frozen, by BFS, or ValueError when the pair is no puzzle the hosted
    agent can solve."""
    for name, word in (("start", start), ("end", end)):
        if word not in WORDS:
            raise ValueError(f"{name} {word!r} is not a 4-letter word in the dictionary")
    if start == end:
        raise ValueError("start and end must differ")
    steps = distances(start).get(end)
    if steps == 1:
        raise ValueError(f"{start} and {end} differ in one letter: a puzzle needs at least one word between them")
    if not two_sided_search(start, end).live():
        size = "no ladder" if steps is None else f"a shortest ladder of {steps + 1} words"
        raise ValueError(
            f"{start} -> {end} ({size}) needs a bigger search than the hosted agent can finish: try a pair with a "
            f"3-word ladder, or a 4-word one whose search takes at most {LIVE_CALLS} neighbors calls of at most "
            f"{LIVE_CALL_WORDS} words"
        )
    return PuzzleOutput(start=start, end=end, solvable=steps is not None, optimal_length=None if steps is None else steps + 1)
