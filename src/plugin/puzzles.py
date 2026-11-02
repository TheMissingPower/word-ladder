"""The frozen puzzles (data/puzzles.json, made once by generate_puzzles.py) and the task's answer key."""

from __future__ import annotations

import json
from pathlib import Path

from contract import LadderInput, PuzzleOutput
from plugin.dictionary import DATA

PUZZLES = DATA / "puzzles.json"


def load_puzzles() -> list[PuzzleOutput]:
    return [PuzzleOutput(**puzzle) for puzzle in json.loads(PUZZLES.read_text(encoding="utf-8"))]


def pin_puzzle(given: LadderInput, workspace: Path) -> PuzzleOutput:
    puzzles = load_puzzles()
    for puzzle in puzzles:
        if (puzzle.start, puzzle.end) == (given.start, given.end):
            return puzzle
    pairs = ", ".join(f"{puzzle.start} -> {puzzle.end}" for puzzle in puzzles)
    raise ValueError(f"{given.start} -> {given.end} is not one of this plugin's puzzles: {pairs}")
