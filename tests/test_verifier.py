from __future__ import annotations

import pytest
from slimconfig import build_output, plain_output

import verifier
from contract import IsWordInput, IsWordOutput, LadderInput, LadderOutput, PuzzleOutput
from plugin.puzzles import pin_puzzle
from verifier.words import WORDS

# duke -> wake: two shortest ladders of 4 words (duke cuke cake wake, duke juke jake wake).
SOLVABLE = {"start": "duke", "end": "wake"}
# kilt -> djin: djin has no neighbors in the dictionary.
UNSOLVABLE = {"start": "kilt", "end": "djin"}


# The verifier gets contract instances, as NanoAgent's sandbox builds them from JSON.
def verdict(puzzle: dict, output: dict, tmp_path) -> dict:
    given = build_output(puzzle, LadderInput)
    reference = build_output(plain_output(pin_puzzle(given, tmp_path)), PuzzleOutput)
    return verifier.verify_task("solve-ladder", given, build_output(output, LadderOutput), reference, str(tmp_path))


def ladder(*words: str) -> dict:
    return {"solvable": True, "ladder": list(words)}


@pytest.mark.parametrize(
    "words", [("duke", "cuke", "cake", "wake"), ("duke", "juke", "jake", "wake")], ids=["one", "another"]
)
def test_passes_any_shortest_ladder(words, tmp_path) -> None:
    result = verdict(SOLVABLE, ladder(*words), tmp_path)
    assert result["valid"] is True and result["score"] == 1.0


def test_passes_a_single_step_puzzle(tmp_path) -> None:
    assert verdict({"start": "jaws", "end": "yaws"}, ladder("jaws", "yaws"), tmp_path)["valid"] is True


def test_passes_an_unsolvable_puzzle_reported_as_unsolvable(tmp_path) -> None:
    assert verdict(UNSOLVABLE, {"solvable": False, "ladder": []}, tmp_path)["valid"] is True


@pytest.mark.parametrize(
    ("puzzle", "output", "reason"),
    [
        (SOLVABLE, ladder("duke", "juke", "jake", "cake", "wake"), "not shortest"),
        (SOLVABLE, ladder("duke", "cake", "wake"), "changes 2 letters"),
        (SOLVABLE, ladder("duke", "cuke", "zake", "wake"), "'zake' is not in the dictionary"),
        (SOLVABLE, ladder("juke", "jake", "wake"), "starts with 'juke'"),
        (SOLVABLE, ladder("duke", "cuke", "cake"), "ends with 'cake'"),
        (SOLVABLE, ladder("duke", "cuke", "duke", "cuke", "cake", "wake"), "'duke' repeats"),
        (SOLVABLE, ladder("duke", "cuke", "cuke", "cake", "wake"), "changes 0 letters"),
        (SOLVABLE, ladder("duke", "CUKE", "cake", "wake"), "not lowercase ASCII letters"),
        (SOLVABLE, ladder("duke", "cukes", "cake", "wake"), "does not have 4 letters"),
        (SOLVABLE, ladder("duke", "cuké", "cake", "wake"), "not lowercase ASCII letters"),
        (SOLVABLE, {"solvable": False, "ladder": []}, "says none does"),
        (SOLVABLE, {"solvable": False, "ladder": ["duke", "cuke", "cake", "wake"]}, "says none does"),
        (SOLVABLE, ladder(), "ladder is empty"),
        (UNSOLVABLE, ladder("kilt", "djin"), "no ladder from kilt to djin exists"),
        (UNSOLVABLE, {"solvable": True, "ladder": []}, "no ladder from kilt to djin exists"),
        (UNSOLVABLE, {"solvable": False, "ladder": ["kilt"]}, "no ladder from kilt to djin exists"),
    ],
    ids=[
        "longer",
        "two-letter-step",
        "not-a-word",
        "wrong-start",
        "wrong-end",
        "repeated-word",
        "repeated-neighbor",
        "uppercase",
        "wrong-length",
        "non-ascii",
        "solvable-called-unsolvable",
        "unsolvable-with-ladder",
        "empty-ladder",
        "invented-ladder",
        "claims-solvable",
        "stray-ladder",
    ],
)
def test_fails_a_wrong_answer(puzzle, output, reason, tmp_path) -> None:
    assert "zake" not in WORDS
    result = verdict(puzzle, output, tmp_path)
    assert result["valid"] is False and result["score"] == 0.0
    assert reason in result["message"]


@pytest.mark.parametrize(
    "output",
    [
        {"solvable": True},
        {"ladder": ["duke", "wake"]},
        {"solvable": "yes", "ladder": []},
        {"solvable": 1, "ladder": []},
        {"solvable": True, "ladder": None},
        {"solvable": True, "ladder": "duke cuke cake wake"},
        {"solvable": True, "ladder": ["duke", 7]},
        {"solvable": None, "ladder": []},
        {"solvable": True, "ladder": [], "steps": 3},
        None,
    ],
)
def test_malformed_output_never_reaches_the_verifier(output) -> None:
    # NanoAgent builds the submitted output into LadderOutput first, so a malformed one fails the task there.
    with pytest.raises(ValueError):
        build_output(output, LadderOutput)


def test_checks_is_word_calls() -> None:
    for word, answer in [("cold", True), ("zake", False), ("COLD", False), ("colder", False)]:
        given = build_output({"word": word}, IsWordInput)
        assert verifier.verify_input("is_word", given)["valid"] is True
        right = build_output({"word": word, "is_word": answer}, IsWordOutput)
        wrong = build_output({"word": word, "is_word": not answer}, IsWordOutput)
        assert verifier.verify_output("is_word", given, right, "")["valid"] is True
        assert verifier.verify_output("is_word", given, wrong, "")["valid"] is False
    renamed = build_output({"word": "cord", "is_word": True}, IsWordOutput)
    assert verifier.verify_output("is_word", build_output({"word": "cold"}, IsWordInput), renamed, "")["valid"] is False
    assert verifier.verify_input("is_word", build_output({"word": ""}, IsWordInput))["valid"] is False


@pytest.mark.parametrize(
    ("puzzle", "reason"),
    [
        ({"start": "Duke", "end": "wake"}, "not lowercase"),
        ({"start": "duke", "end": "wakes"}, "4 letters"),
        ({"start": "zake", "end": "wake"}, "not in the dictionary"),
        ({"start": "duke", "end": "duke"}, "must differ"),
    ],
)
def test_refuses_a_puzzle_input_that_is_no_puzzle(puzzle, reason) -> None:
    result = verifier.verify_input("pin_puzzle", build_output(puzzle, LadderInput))
    assert result["valid"] is False and reason in result["message"]


def test_refuses_a_tampered_answer_key(tmp_path) -> None:
    given = build_output(SOLVABLE, LadderInput)
    pinned = plain_output(pin_puzzle(given, tmp_path))
    assert verifier.verify_output("pin_puzzle", given, build_output(pinned, PuzzleOutput), "")["valid"] is True
    for tampered in [
        {**pinned, "optimal_length": 5},
        {**pinned, "solvable": False, "optimal_length": None},
        {**pinned, "solvable": False},
        {**pinned, "end": "cake"},
    ]:
        assert verifier.verify_output("pin_puzzle", given, build_output(tampered, PuzzleOutput), "")["valid"] is False
