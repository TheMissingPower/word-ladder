"""The neighbors tool: each asked word's one-letter neighbors in the dictionary, for the agent's own search."""

from __future__ import annotations

import re
from pathlib import Path

from contract import MAX_NEIGHBOR_WORDS, NeighborsInput, NeighborsOutput, WordNeighbors
from plugin.dictionary import LENGTH, WORDS
from plugin.dictionary import neighbors as one_letter_neighbors

LETTERS = re.compile(r"[a-z]+")


def neighbors(given: NeighborsInput, workspace: Path) -> NeighborsOutput:
    words = given.words
    if not words:
        raise ValueError("neighbors needs at least 1 word")
    if len(words) > MAX_NEIGHBOR_WORDS:
        raise ValueError(f"neighbors takes at most {MAX_NEIGHBOR_WORDS} words per call, got {len(words)}: split the call")
    for word in words:
        if not LETTERS.fullmatch(word) or len(word) != LENGTH:
            raise ValueError(f"{word!r} is not {LENGTH} lowercase ASCII letters")
        if word not in WORDS:
            raise ValueError(f"{word!r} is not in the dictionary")
    return NeighborsOutput(results=[WordNeighbors(word=word, neighbors=one_letter_neighbors(word)) for word in words])
