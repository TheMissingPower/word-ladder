from __future__ import annotations

import hashlib
import json
import random
from itertools import pairwise
from pathlib import Path

import pytest

import verifier.words
from contract import MAX_NEIGHBOR_WORDS, IsWordInput, LadderInput, NeighborsInput
from plugin import is_word, neighbors, pin_puzzle
from plugin.dictionary import ENABLE, WORDS, distances
from plugin.generate_puzzles import (
    CASES,
    MAX_CALLS,
    SEED,
    TOKEN_BUDGET,
    UNSOLVABLE_CALLS,
    VERIFIER_WORDS,
    cases,
    puzzles,
    two_sided_search,
    words_module,
)
from plugin.puzzles import PUZZLES, load_puzzles

# sha256 of enable1.txt as published at github.com/dolph/dictionary (172,823 words, LF line endings).
ENABLE_SHA256 = "3f16130220645692ed49c7134e24a18504c2ca55b3c012f7290e3e77c63b1a89"
LIVE = load_puzzles()


def brute_force(word: str) -> list[str]:
    """Every dictionary word differing from ``word`` in exactly one position, by scanning the whole dictionary."""
    return sorted(other for other in WORDS if sum(a != b for a, b in zip(word, other)) == 1)


def neighbors_of(word: str) -> list[str]:
    return neighbors(NeighborsInput(words=[word]), Path(".")).results[0].neighbors


def test_the_dictionary_is_the_vendored_enable_list() -> None:
    lines = ENABLE.read_text(encoding="ascii").splitlines()
    assert hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest() == ENABLE_SHA256
    assert len(WORDS) == 3903 and all(len(word) == 4 and word.isalpha() and word.islower() for word in WORDS)
    assert verifier.words.WORDS == WORDS


def test_every_frozen_puzzle_matches_a_fresh_bfs() -> None:
    for puzzle in LIVE:
        steps = distances(puzzle.start).get(puzzle.end)
        assert puzzle.solvable == (steps is not None)
        assert puzzle.optimal_length == (None if steps is None else steps + 1)


def test_the_frozen_files_are_what_the_generator_makes() -> None:
    made = puzzles(random.Random(SEED))
    assert json.loads(PUZZLES.read_text(encoding="utf-8")) == made
    assert Path(VERIFIER_WORDS).read_text(encoding="utf-8") == words_module()
    expected = cases(made)
    assert {path.stem for path in CASES.glob("*.json")} == set(expected)
    for name, case in expected.items():
        assert json.loads((CASES / f"{name}.json").read_text(encoding="utf-8")) == case


def test_the_puzzle_mix() -> None:
    lengths = sorted(puzzle.optimal_length for puzzle in LIVE if puzzle.solvable)
    assert len(LIVE) == 15 and len({(puzzle.start, puzzle.end) for puzzle in LIVE}) == 15
    assert lengths == [3] * 3 + [4] * 3 + [5] * 3 + [6] * 3
    assert sum(not puzzle.solvable for puzzle in LIVE) == 3


@pytest.mark.parametrize("puzzle", LIVE, ids=[f"{puzzle.start}-{puzzle.end}" for puzzle in LIVE])
def test_the_prescribed_search_fits_the_hosted_budget(puzzle) -> None:
    search = two_sided_search(puzzle.start, puzzle.end)
    assert len(search.calls) <= MAX_CALLS, "4 neighbors calls, then submit (step 5) and the forced answer (step 6)"
    assert all(len(call) <= MAX_NEIGHBOR_WORDS for call in search.calls)
    assert search.tokens < TOKEN_BUDGET
    if puzzle.solvable:
        assert search.outcome == "meet" and len(search.ladder) == puzzle.optimal_length
        ladder = search.ladder
        assert ladder[0] == puzzle.start and ladder[-1] == puzzle.end and len(set(ladder)) == len(ladder)
        assert all(after in neighbors_of(before) for before, after in pairwise(ladder))
    else:
        assert search.outcome == "dead" and len(search.calls) <= UNSOLVABLE_CALLS


def test_neighbors_are_exactly_the_one_letter_dictionary_words(tmp_path: Path) -> None:
    live_words = {word for puzzle in LIVE for word in (puzzle.start, puzzle.end)}
    sample = sorted(live_words | set(random.Random(0).sample(sorted(WORDS), 40)))
    for first in range(0, len(sample), MAX_NEIGHBOR_WORDS):
        asked = sample[first : first + MAX_NEIGHBOR_WORDS]
        output = neighbors(NeighborsInput(words=asked), tmp_path)
        assert [entry.word for entry in output.results] == asked
        for entry in output.results:
            assert entry.neighbors == brute_force(entry.word)
    assert neighbors_of("djin") == []


@pytest.mark.parametrize(
    ("words", "reason"),
    [
        (sorted(WORDS)[:26], "at most 25 words per call, got 26"),
        ([], "at least 1 word"),
        (["cold", "zake"], "'zake' is not in the dictionary"),
        (["colder"], "not 4 lowercase ASCII letters"),
        (["col"], "not 4 lowercase ASCII letters"),
        (["Cold"], "not 4 lowercase ASCII letters"),
    ],
    ids=["26-words", "empty", "unknown", "too-long", "too-short", "uppercase"],
)
def test_neighbors_refuses_a_call_out_of_bounds(words, reason, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=reason):
        neighbors(NeighborsInput(words=words), tmp_path)


def test_is_word_answers_from_the_dictionary(tmp_path: Path) -> None:
    assert is_word(IsWordInput(word="cold"), tmp_path).is_word is True
    assert is_word(IsWordInput(word="zake"), tmp_path).is_word is False
    assert is_word(IsWordInput(word="Cold"), tmp_path).is_word is False
    assert is_word(IsWordInput(word="colder"), tmp_path).is_word is False


def test_pin_puzzle_pins_only_frozen_puzzles(tmp_path: Path) -> None:
    live = LIVE[0]
    pinned = pin_puzzle(LadderInput(start=live.start, end=live.end), tmp_path)
    assert (pinned.solvable, pinned.optimal_length) == (live.solvable, live.optimal_length)
    with pytest.raises(ValueError, match="not one of this plugin's puzzles"):
        pin_puzzle(LadderInput(start="cold", end="warm"), tmp_path)
