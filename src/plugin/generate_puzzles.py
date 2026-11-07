"""Freeze the puzzles, the verifier's word list and the scripted cases. Run once, from the plugin root:

    uv run python -m plugin.generate_puzzles

It writes src/plugin/data/puzzles.json, verifier/words.py and tests/cases/*.json, and prints each puzzle's
simulated search (the README's table). All are committed; nothing regenerates them at run or verification time,
and the same seed and dictionary always give the same files.

A puzzle is live only if the search the task's instructions prescribe (two_sided_search) fits RUSH Lab's hosted
limits with room to spare: at most LIVE_CALLS neighbors calls (the hard limit is MAX_CALLS: with submit, 5 tool
steps, as the 6th step must answer), at most LIVE_CALL_WORDS words per call, a small token cost for the tool
results (which every later request re-sends), and a meeting that leaves nothing to check: every word on both
sides gives a shortest ladder, so the agent can submit the first one it sees. Longer ladders (5 and 6 words, or
calls of 20+ words) made the hosted agent spend its 2048-token response re-checking the answer and never submit.
"""

from __future__ import annotations

import json
import math
import random
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

from contract import MAX_NEIGHBOR_WORDS
from plugin.dictionary import WORDS, distances, neighbors
from plugin.puzzles import PUZZLES

SEED = 480
# Optimal lengths (words, both ends included) of the solvable live puzzles.
LENGTHS = [3] * 6 + [4] * 6
MAX_CALLS = 4  # neighbors calls; then submit (step 5) and the forced answer (step 6)
LIVE_CALLS = 2  # a live puzzle's search needs at most this many calls
LIVE_CALL_WORDS = 12  # and at most this many words in any call, so each step has little to read
UNSOLVABLE_CALLS = 2  # an unsolvable puzzle's search runs out of words within this many calls
TOKEN_BUDGET = 20_000  # estimated tokens of tool results over the whole run, re-sends included
CHARS_PER_TOKEN = 3  # conservative for JSON lists of 4-letter words
TOKENS_PER_WORD = 1.3  # the brief's rough figure, reported alongside
ROOT = Path(__file__).parents[2]
VERIFIER_WORDS = ROOT / "verifier" / "words.py"
CASES = ROOT / "tests" / "cases"


@dataclass
class Search:
    """The prescribed search: neighbors on [start, end], then on every newest word of both sides, until a word
    is on both sides (``meet``) or a side has no new word (``dead``); ``unfinished`` past ``max_calls``."""

    calls: list[list[str]] = field(default_factory=list)
    outcome: str = "unfinished"
    ladder: list[str] = field(default_factory=list)  # a shortest ladder, as the search finds it, when met
    output_chars: list[int] = field(default_factory=list)  # each call's result, as compact JSON
    output_words: int = 0  # every word in every result: each asked word and its neighbors
    meeting_lengths: list[int] = field(default_factory=list)  # the ladder length through each word on both sides

    @property
    def tokens(self) -> int:
        """Estimated tokens of tool results the run is billed: call k's result is in every later request (the
        later calls', submit's at step n+1 and the answer's at n+2)."""
        n = len(self.calls)
        return sum(math.ceil(chars / CHARS_PER_TOKEN) * (n + 2 - k) for k, chars in enumerate(self.output_chars, 1))

    def fits(self) -> bool:
        return (
            self.outcome in ("meet", "dead")
            and len(self.calls) <= MAX_CALLS
            and max(map(len, self.calls)) <= MAX_NEIGHBOR_WORDS
            and self.tokens < TOKEN_BUDGET
        )

    def live(self) -> bool:
        """Fits with room to spare, and any meeting the agent sees is a shortest ladder."""
        return (
            self.fits()
            and len(self.calls) <= LIVE_CALLS
            and max(map(len, self.calls)) <= LIVE_CALL_WORDS
            and len(set(self.meeting_lengths)) <= 1
        )


def two_sided_search(start: str, end: str, max_calls: int = MAX_CALLS) -> Search:
    search = Search()
    depth = {"start": {start: 0}, "end": {end: 0}}
    parent: dict[str, dict[str, str]] = {"start": {}, "end": {}}
    newest = {"start": [start], "end": [end]}
    while len(search.calls) < max_calls:
        call = newest["start"] + newest["end"]
        search.calls.append(call)
        if len(call) > MAX_NEIGHBOR_WORDS:  # the tool would refuse it: the puzzle cannot be live
            search.outcome = "too_wide"
            return search
        results = []
        added: dict[str, list[str]] = {}
        for side in ("start", "end"):
            added[side] = []
            for word in newest[side]:
                listed = neighbors(word)
                results.append({"word": word, "neighbors": listed})
                for after in listed:
                    if after not in depth[side]:
                        depth[side][after] = depth[side][word] + 1
                        parent[side][after] = word
                        added[side].append(after)
        search.output_chars.append(len(json.dumps({"results": results})))
        search.output_words += sum(1 + len(result["neighbors"]) for result in results)
        met = [(depth["start"][word] + depth["end"][word], word) for word in depth["start"] if word in depth["end"]]
        if met:
            search.meeting_lengths = sorted(steps + 1 for steps, _ in met)
            _, middle = min(met)
            search.outcome, search.ladder = "meet", trace(middle, parent["start"])[::-1] + trace(middle, parent["end"])[1:]
            return search
        newest = {side: sorted(added[side]) for side in added}
        if not newest["start"] or not newest["end"]:
            search.outcome = "dead"
            return search
    return search


def trace(word: str, parents: dict[str, str]) -> list[str]:
    path = [word]
    while path[-1] in parents:
        path.append(parents[path[-1]])
    return path


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
    too_many = sorted(WORDS)[: MAX_NEIGHBOR_WORDS + 1]
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
        "too_many_words": case(
            "A 26-word neighbors call is refused, then the prescribed search and its ladder.", three,
            [{"tool": "neighbors", "arguments": {"words": too_many}, "expect_error": True}] + calls(three),
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
