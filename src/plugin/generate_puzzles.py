"""Freeze the puzzles and the verifier's word list. Run once, from the plugin root:

    uv run python -m plugin.generate_puzzles

It writes src/plugin/data/puzzles.json and verifier/words.py. Both are committed; nothing regenerates them at
run or verification time, and the same seed and dictionary always give the same files.
"""

from __future__ import annotations

import json
import random
import textwrap
from pathlib import Path

from plugin.dictionary import WORDS, distances, neighbors
from plugin.puzzles import PUZZLES

SEED = 480
# Optimal lengths (words, both ends included) of the solvable puzzles: two short ones, then three each of 4 to 8.
LENGTHS = [2, 3] + [length for length in range(4, 9) for _ in range(3)]
VERIFIER_WORDS = Path(__file__).parents[2] / "verifier" / "words.py"


def components() -> list[list[str]]:
    """The connected components of the ladder graph, largest first, each sorted."""
    seen: set[str] = set()
    found = []
    for word in sorted(WORDS):
        if word not in seen:
            component = sorted(distances(word))
            seen.update(component)
            found.append(component)
    return sorted(found, key=lambda component: (-len(component), component[0]))


def puzzles(rng: random.Random) -> list[dict]:
    graph = components()
    giant = graph[0]
    chosen: list[dict] = []
    for length in LENGTHS:
        while True:
            start = rng.choice(giant)
            ends = sorted(word for word, steps in distances(start).items() if steps == length - 1)
            if ends:
                end = rng.choice(ends)
                if all((start, end) != (puzzle["start"], puzzle["end"]) for puzzle in chosen):
                    break
        chosen.append({"start": start, "end": end, "solvable": True, "optimal_length": length})
    # No ladder: an isolated word (no neighbors at all) at either end, and a word of a small component (3 to 6
    # words) to the giant one, which can be shown unsolvable by exhausting the small side.
    isolated = [word for word in sorted(WORDS) if not neighbors(word)]
    small = [word for component in graph if 3 <= len(component) <= 6 for word in component]
    pairs = [(rng.choice(giant), rng.choice(isolated)), (rng.choice(isolated), rng.choice(giant))]
    pairs.append((rng.choice(small), rng.choice(giant)))
    chosen += [{"start": start, "end": end, "solvable": False, "optimal_length": None} for start, end in pairs]
    return chosen


def words_module() -> str:
    body = textwrap.fill(" ".join(sorted(WORDS)), width=116)
    return (
        '"""The puzzle dictionary, the 4-letter words of ENABLE: written by plugin.generate_puzzles, never by hand."""\n'
        f'\nTEXT = """\n{body}\n"""\nWORDS = frozenset(TEXT.split())\n'
    )


def main() -> None:
    PUZZLES.write_text(json.dumps(puzzles(random.Random(SEED)), indent=2) + "\n", encoding="utf-8")
    VERIFIER_WORDS.write_text(words_module(), encoding="utf-8")


if __name__ == "__main__":
    main()
