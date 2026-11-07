"""The search the task's instructions prescribe, simulated, and whether a puzzle's search fits the hosted limits.

RUSH Lab runs the agent with max_tokens 2048 per response, max_steps 6 (the 6th must answer), token_limit 65536
and cost_limit 0.10. A puzzle is live (pin_puzzle accepts it, and the generator may freeze it) only if its search
fits with room to spare: a ladder of at most LIVE_LADDER_WORDS words (or no ladder, shown within LIVE_CALLS
calls), a small token cost for the tool results (which every later request re-sends), and a meeting that leaves
nothing to check: every word on both sides gives a shortest ladder, so the agent can submit the first one it sees.
A 6-word puzzle made the hosted agent spend its 2048-token response re-checking its answer and never submit.
There is no limit on the words in one neighbors call.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field

from plugin.dictionary import neighbors

MAX_CALLS = 4  # neighbors calls; then submit (step 5) and the forced answer (step 6)
LIVE_CALLS = 2  # a live puzzle's search needs at most this many calls
LIVE_LADDER_WORDS = 4  # and a ladder of at most this many words
UNSOLVABLE_CALLS = 2  # an unsolvable puzzle's search runs out of words within this many calls
TOKEN_BUDGET = 20_000  # estimated tokens of tool results over the whole run, re-sends included
CHARS_PER_TOKEN = 3  # conservative for JSON lists of 4-letter words


@dataclass
class Search:
    """The prescribed search: neighbors on [start, end], then on every newest word of the side with fewer of them,
    until a word is on both sides (``meet``) or an expanded side has no new word (``dead``); ``unfinished`` past
    ``max_calls``."""

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
            and self.tokens < TOKEN_BUDGET
        )

    def problem(self) -> str | None:
        """Why the hosted agent could not be trusted to finish this search, or None when it is live."""
        if self.outcome == "meet" and len(self.ladder) > LIVE_LADDER_WORDS:
            return (
                f"its shortest ladder has {len(self.ladder)} words, more than the {LIVE_LADDER_WORDS} the hosted "
                "agent reliably finishes"
            )
        if self.outcome != "meet" and not (self.outcome == "dead" and len(self.calls) <= LIVE_CALLS):
            return f"it has no ladder, but neither side of the search runs out of words within {LIVE_CALLS} calls"
        if len(set(self.meeting_lengths)) > 1:
            return "its search meets on ladders of different lengths at once, so the agent could submit a longer one"
        if self.tokens >= TOKEN_BUDGET:
            return "its search returns more tool results than the hosted token budget allows"
        return None

    def live(self) -> bool:
        """Fits with room to spare, and any meeting the agent sees is a shortest ladder."""
        return self.problem() is None


def two_sided_search(start: str, end: str, max_calls: int = MAX_CALLS) -> Search:
    search = Search()
    depth = {"start": {start: 0}, "end": {end: 0}}
    parent: dict[str, dict[str, str]] = {"start": {}, "end": {}}
    newest = {"start": [start], "end": [end]}
    sides = ("start", "end")  # the first call expands both ends
    while len(search.calls) < max_calls:
        call = [word for side in sides for word in newest[side]]
        search.calls.append(call)
        results = []
        added: dict[str, list[str]] = {}
        for side in sides:
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
        for side in sides:
            newest[side] = sorted(added[side])
        if any(not newest[side] for side in sides):
            search.outcome = "dead"
            return search
        # Each later call expands one side only, the one with fewer newest words (start on a tie): still breadth-first,
        # and every word a call puts on both sides gives a ladder of the same length.
        sides = ("start",) if len(newest["start"]) <= len(newest["end"]) else ("end",)
    return search


def trace(word: str, parents: dict[str, str]) -> list[str]:
    path = [word]
    while path[-1] in parents:
        path.append(parents[path[-1]])
    return path
