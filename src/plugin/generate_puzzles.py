"""Freeze the puzzles, the verifier's word list and the scripted cases. Run once, from the plugin root:

    uv run python -m plugin.generate_puzzles

It writes src/plugin/data/puzzles.json, verifier/words.py and tests/cases/*.json, and prints each puzzle's
simulated search (the README's table). All are committed; nothing regenerates them at run or verification time,
and the same seed and dictionary always give the same files.

A puzzle is frozen only if it is live (plugin.search): its prescribed search fits RUSH Lab's hosted limits with
room to spare, and any meeting the agent sees is a shortest ladder. pin_puzzle accepts any other live pair too; the
frozen ones are the documented examples and the test set.
"""

from __future__ import annotations

import json
import random
import textwrap
from pathlib import Path

from plugin.dictionary import WORDS, distances, neighbors
from plugin.puzzles import PUZZLES
from plugin.search import UNSOLVABLE_CALLS, two_sided_search

SEED = 480
# Optimal lengths (words, both ends included) of the solvable live puzzles.
LENGTHS = [3] * 6 + [4] * 6
ROOT = Path(__file__).parents[2]
VERIFIER_WORDS = ROOT / "verifier" / "words.py"
CASES = ROOT / "tests" / "cases"


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
    taken: set[tuple[str, str]] = set()
    for length in LENGTHS:
        while True:
            start = rng.choice(giant)
            ends = sorted(word for word, steps in distances(start).items() if steps == length - 1)
            if not ends:
                continue
            end = rng.choice(ends)
            if (start, end) not in taken and two_sided_search(start, end).live():
                break
        taken.add((start, end))
        chosen.append({"start": start, "end": end, "solvable": True, "optimal_length": length})
    # No ladder: an isolated word (no neighbors at all) at the end, then at the start, and a word of a small
    # component (2 to 5 words) to a giant-component word; each side's search runs out within 2 calls.
    isolated = [word for word in sorted(WORDS) if not neighbors(word)]
    small = [word for component in graph if 2 <= len(component) <= 5 for word in component]
    for pick in (lambda: (rng.choice(giant), rng.choice(isolated)), lambda: (rng.choice(isolated), rng.choice(giant))):
        chosen.append(unsolvable(pick))
    chosen.append(unsolvable(lambda: (rng.choice(small), rng.choice(giant))))
    return chosen


def unsolvable(pick) -> dict:
    while True:
        start, end = pick()
        search = two_sided_search(start, end)
        if search.live() and search.outcome == "dead" and len(search.calls) <= UNSOLVABLE_CALLS:
            return {"start": start, "end": end, "solvable": False, "optimal_length": None}


def words_module() -> str:
    body = textwrap.fill(" ".join(sorted(WORDS)), width=116)
    return (
        '"""The puzzle dictionary, the 4-letter words of ENABLE: written by plugin.generate_puzzles, never by hand."""\n'
        f'\nTEXT = """\n{body}\n"""\nWORDS = frozenset(TEXT.split())\n'
    )


def longer_ladder(start: str, end: str) -> list[str]:
    """A valid ladder (no repeated word) longer than the shortest, as short as one can be: a bounded search."""
    to_end = distances(end)
    shortest = to_end[start] + 1
    for length in range(shortest + 1, shortest + 6):
        ladder = _ladder_of(length, [start], end, to_end)
        if ladder:
            return ladder
    raise ValueError(f"no ladder from {start} to {end} a little longer than the shortest")


def _ladder_of(length: int, path: list[str], end: str, to_end: dict[str, int]) -> list[str] | None:
    if path[-1] == end:
        return path if len(path) == length else None
    for after in neighbors(path[-1]):
        if after not in path and len(path) + to_end.get(after, length) < length:
            found = _ladder_of(length, path + [after], end, to_end)
            if found:
                return found
    return None


def cases(frozen: list[dict]) -> dict[str, dict]:
    """The scripted cases (tests/cases/<name>.json): the prescribed neighbors calls, then a submit, and the
    verdict the real verifier must give. tests/replay.py plays them through the real tools with no model."""
    first = {
        "length4": next(puzzle for puzzle in frozen if puzzle["optimal_length"] == 4),
        "length3": next(puzzle for puzzle in frozen if puzzle["optimal_length"] == 3),
        "isolated": next(puzzle for puzzle in frozen if not puzzle["solvable"]),
        "component": [puzzle for puzzle in frozen if not puzzle["solvable"]][-1],
    }

    def calls(puzzle: dict) -> list[dict]:
        search = two_sided_search(puzzle["start"], puzzle["end"])
        return [{"tool": "neighbors", "arguments": {"words": call}} for call in search.calls]

    def case(note: str, puzzle: dict, steps: list[dict], submit: dict, expect: dict) -> dict:
        return {
            "note": note,
            "task": "solve-ladder",
            "arguments": {"start": puzzle["start"], "end": puzzle["end"]},
            "steps": steps + [{"tool": "submit", "arguments": submit}],
            "answer": "Submitted.",
            "expect": expect,
        }

    def gold(puzzle: dict) -> dict:
        if not puzzle["solvable"]:
            return {"solvable": False, "ladder": []}
        return {"solvable": True, "ladder": two_sided_search(puzzle["start"], puzzle["end"]).ladder}

    four, three, isolated, component = first["length4"], first["length3"], first["isolated"], first["component"]
    passed = {"valid": True, "score_min": 1.0}
    failed = {"valid": False, "score_max": 0.0}
    invented = [isolated["start"], neighbors(isolated["start"])[0], isolated["end"]]
    longer = {"solvable": True, "ladder": longer_ladder(four["start"], four["end"])}
    return {
        "gold_length4": case(
            "The prescribed search on a 4-word puzzle, then its ladder.", four, calls(four), gold(four),
            {**passed, "message_contains": "a valid shortest ladder of 4 words"},
        ),
        "gold_length3": case(
            "The prescribed search on a 3-word puzzle, then its ladder.", three, calls(three), gold(three),
            {**passed, "message_contains": "a valid shortest ladder of 3 words"},
        ),
        "gold_unsolvable_isolated": case(
            "The end word has no neighbors: the end side runs out in the first call.", isolated, calls(isolated),
            gold(isolated), {**passed, "message_contains": "correctly reports that no ladder"},
        ),
        "gold_unsolvable_component": case(
            "The start word sits in a small component: its side runs out first.", component, calls(component),
            gold(component), {**passed, "message_contains": "correctly reports that no ladder"},
        ),
        "longer_ladder": case(
            "The search, then a valid ladder longer than the shortest.", four, calls(four), longer,
            {**failed, "message_contains": "not shortest"},
        ),
        "invented_ladder_unsolvable": case(
            "The search shows no ladder, but a ladder is invented anyway.", isolated, calls(isolated),
            {"solvable": True, "ladder": invented}, {**failed, "message_contains": "no ladder from"},
        ),
        "says_unsolvable_when_solvable": case(
            "The search meets, but the puzzle is reported unsolvable.", four, calls(four),
            {"solvable": False, "ladder": []}, {**failed, "message_contains": "says none does"},
        ),
        "refused_unknown_word": case(
            "A neighbors call with a word not in the dictionary is refused, then the prescribed search and its ladder.",
            three, [{"tool": "neighbors", "arguments": {"words": ["zake"]}, "expect_error": True}] + calls(three),
            gold(three), {**passed, "message_contains": "a valid shortest ladder of 3 words"},
        ),
    }


def table(frozen: list[dict]) -> str:
    """Each live puzzle's simulated search, as the README's markdown table."""
    rows = ["| start | end | optimal_length | calls | words per call | output words | est. tokens (re-sent) |", "|---|---|---|---|---|---|---|"]
    for puzzle in frozen:
        search = two_sided_search(puzzle["start"], puzzle["end"])
        length = puzzle["optimal_length"] or "no ladder"
        sizes = ", ".join(str(len(call)) for call in search.calls)
        rows.append(f"| {puzzle['start']} | {puzzle['end']} | {length} | {len(search.calls)} | {sizes} | {search.output_words} | {search.tokens:,} |")
    return "\n".join(rows)


def main() -> None:
    frozen = puzzles(random.Random(SEED))
    PUZZLES.write_text(json.dumps(frozen, indent=2) + "\n", encoding="utf-8")
    VERIFIER_WORDS.write_text(words_module(), encoding="utf-8")
    CASES.mkdir(exist_ok=True)
    for name, case in cases(frozen).items():
        (CASES / f"{name}.json").write_text(json.dumps(case, indent=1) + "\n", encoding="utf-8")
    print(table(frozen))


if __name__ == "__main__":
    main()
