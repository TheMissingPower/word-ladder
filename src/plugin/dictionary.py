"""The puzzle dictionary, the 4-letter words of the vendored ENABLE list, and the ladder graph over them."""

from __future__ import annotations

from collections import deque
from pathlib import Path
from string import ascii_lowercase

DATA = Path(__file__).with_name("data")
ENABLE = DATA / "enable1.txt"
LENGTH = 4
WORDS = frozenset(word for word in ENABLE.read_text(encoding="ascii").splitlines() if len(word) == LENGTH)


def neighbors(word: str) -> list[str]:
    """The dictionary words one letter different from ``word``, in alphabetical order."""
    found = {word[:i] + letter + word[i + 1 :] for i in range(len(word)) for letter in ascii_lowercase}
    return sorted((found - {word}) & WORDS)


def distances(start: str) -> dict[str, int]:
    """Each word reachable from ``start`` and the fewest steps (one-letter changes) it takes, by BFS."""
    steps = {start: 0}
    queue = deque([start])
    while queue:
        word = queue.popleft()
        for after in neighbors(word):
            if after not in steps:
                steps[after] = steps[word] + 1
                queue.append(after)
    return steps
