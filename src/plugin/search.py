"""The search the task's instructions prescribe, simulated, and whether a puzzle's search fits the hosted limits.

RUSH Lab runs the agent with max_tokens 2048 per response, max_steps 6 (the 6th must answer), token_limit 65536
and cost_limit 0.10. A puzzle is live (pin_puzzle accepts it, and the generator may freeze it) only if its search
fits with room to spare: at most LIVE_CALLS neighbors calls of at most LIVE_CALL_WORDS words, a small token cost
for the tool results (which every later request re-sends), and a meeting that leaves nothing to check: every word
on both sides gives a shortest ladder, so the agent can submit the first one it sees. Longer searches (5- and
6-word ladders, calls of 20+ words) made the hosted agent spend its 2048-token response re-checking its answer and
never submit.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field

from contract import MAX_NEIGHBOR_WORDS
from plugin.dictionary import neighbors

MAX_CALLS = 4  # neighbors calls; then submit (step 5) and the forced answer (step 6)
LIVE_CALLS = 2  # a live puzzle's search needs at most this many calls
LIVE_CALL_WORDS = 12  # and at most this many words in any call, so each step has little to read
UNSOLVABLE_CALLS = 2  # an unsolvable puzzle's search runs out of words within this many calls
TOKEN_BUDGET = 20_000  # estimated tokens of tool results over the whole run, re-sends included
CHARS_PER_TOKEN = 3  # conservative for JSON lists of 4-letter words


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
