from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import pytest

import verifier.words
from contract import IsWordInput, LadderInput
from plugin import is_word, pin_puzzle
from plugin.dictionary import ENABLE, WORDS, distances
from plugin.generate_puzzles import SEED, VERIFIER_WORDS, puzzles, words_module
from plugin.puzzles import PUZZLES, load_puzzles

# sha256 of enable1.txt as published at github.com/dolph/dictionary (172,823 words, LF line endings).
ENABLE_SHA256 = "3f16130220645692ed49c7134e24a18504c2ca55b3c012f7290e3e77c63b1a89"


def test_the_dictionary_is_the_vendored_enable_list() -> None:
    lines = ENABLE.read_text(encoding="ascii").splitlines()
    assert hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest() == ENABLE_SHA256
    assert len(WORDS) == 3903 and all(len(word) == 4 and word.isalpha() and word.islower() for word in WORDS)
    assert verifier.words.WORDS == WORDS


def test_every_frozen_puzzle_matches_a_fresh_bfs() -> None:
    for puzzle in load_puzzles():
        steps = distances(puzzle.start).get(puzzle.end)
        assert puzzle.solvable == (steps is not None)
        assert puzzle.optimal_length == (None if steps is None else steps + 1)


def test_the_frozen_files_are_what_the_generator_makes() -> None:
    assert json.loads(PUZZLES.read_text(encoding="utf-8")) == puzzles(random.Random(SEED))
    assert Path(VERIFIER_WORDS).read_text(encoding="utf-8") == words_module()


def test_the_puzzle_mix() -> None:
    frozen = load_puzzles()
    lengths = sorted(puzzle.optimal_length for puzzle in frozen if puzzle.solvable)
    assert len(frozen) == 20 and len({(puzzle.start, puzzle.end) for puzzle in frozen}) == 20
    assert lengths == [3] * 17
    assert sum(not puzzle.solvable for puzzle in frozen) == 3


def test_is_word_answers_from_the_dictionary(tmp_path: Path) -> None:
    assert is_word(IsWordInput(word="cold"), tmp_path).is_word is True
    assert is_word(IsWordInput(word="zake"), tmp_path).is_word is False
    assert is_word(IsWordInput(word="Cold"), tmp_path).is_word is False
    assert is_word(IsWordInput(word="colder"), tmp_path).is_word is False


def test_pin_puzzle_pins_only_frozen_puzzles(tmp_path: Path) -> None:
    pinned = pin_puzzle(LadderInput(start="duke", end="joke"), tmp_path)
    assert (pinned.solvable, pinned.optimal_length) == (True, 3)
    with pytest.raises(ValueError, match="not one of this plugin's puzzles"):
        pin_puzzle(LadderInput(start="cold", end="warm"), tmp_path)
