"""The scripted cases under tests/cases/, played through the real tools and the real verifier with no model: each
gets the verdict it expects, and each keeps to the hosted budget and the prescribed search."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from replay import matches, replay

from contract import MAX_NEIGHBOR_WORDS
from plugin.generate_puzzles import two_sided_search

CASES = sorted((Path(__file__).resolve().parent / "cases").glob("*.json"))


def load(case_file: Path) -> dict:
    return json.loads(case_file.read_text(encoding="utf-8"))


def test_there_are_gold_and_broken_cases() -> None:
    names = {case.stem for case in CASES}
    assert {"gold_length4", "gold_length3", "gold_unsolvable_isolated", "gold_unsolvable_component"} <= names
    assert {"longer_ladder", "invented_ladder_unsolvable", "says_unsolvable_when_solvable", "too_many_words"} <= names


@pytest.mark.parametrize("case_file", CASES, ids=[case.stem for case in CASES])
def test_each_case_gets_its_verdict(case_file: Path) -> None:
    case = load(case_file)
    problems = matches(replay(case), case["expect"])
    assert not problems, problems


@pytest.mark.parametrize("case_file", CASES, ids=[case.stem for case in CASES])
def test_each_case_keeps_to_the_hosted_budget(case_file: Path) -> None:
    case = load(case_file)
    steps = [step for step in case["steps"] if not step.get("expect_error")]
    assert {step["tool"] for step in steps} <= {"neighbors", "is_word", "submit"} and steps[-1]["tool"] == "submit"
    assert len(case["steps"]) <= 5, "the hosted agent has six steps and the last may not call a tool"
    assert all(len(step["arguments"]["words"]) <= MAX_NEIGHBOR_WORDS for step in steps if step["tool"] == "neighbors")
    if case_file.stem.startswith("gold"):
        start, end = case["arguments"]["start"], case["arguments"]["end"]
        assert [step["arguments"]["words"] for step in steps[:-1]] == two_sided_search(start, end).calls
