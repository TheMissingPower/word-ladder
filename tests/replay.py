"""Replay a scripted case (tests/cases/*.json) with no model, the way NanoAgent runs an agent task: the answer key
first, in its own scratch folder; then each step through the real tools, every call's input and output checked by
the verifier as NanoAgent checks them; and the verdict on what the submit step hands in."""

from __future__ import annotations

import tempfile
from pathlib import Path

from slimconfig import build_output, plain_output

import verifier
from contract import TASKS, TOOLS, Task, Tool
from plugin import is_word, neighbors, pin_puzzle

# The tools an agent may call; pin_puzzle is the task's reference, which only NanoAgent calls.
IMPLEMENTATIONS = {Tool.IS_WORD: is_word, Tool.NEIGHBORS: neighbors}


def call(tool: Tool, arguments: dict, workspace: Path) -> dict:
    """The tool's output as JSON; ValueError where NanoAgent would hand the agent an error instead."""
    given_class, output_class = TOOLS[tool]
    given = build_output(arguments, given_class)
    check = verifier.verify_input(tool.value, given)
    if not check["valid"]:
        raise ValueError(f"plugin input verification failed: {check['message']}")
    output = plain_output(IMPLEMENTATIONS[tool](given, workspace))
    check = verifier.verify_output(tool.value, given, build_output(output, output_class), str(workspace))
    if not check["valid"]:
        raise AssertionError(f"{tool.value}'s output fails its own check: {check['message']}")
    return output


def replay(case: dict) -> dict:
    """The verdict of a case, or {"error": ...} when the scripted agent never submits."""
    task = Task(case["task"])
    given_class, output_class = TASKS[task]
    arguments = build_output(case["arguments"], given_class)
    pinned = plain_output(pin_puzzle(arguments, Path(tempfile.mkdtemp(prefix="word-ladder-ref-"))))
    reference = build_output(pinned, TOOLS[Tool.PIN_PUZZLE][1])
    workspace = Path(tempfile.mkdtemp(prefix="word-ladder-case-"))
    submitted = None
    for step in case["steps"]:
        if step["tool"] == "submit":
            submitted = step["arguments"]
            continue
        try:
            call(Tool(step["tool"]), step["arguments"], workspace)
            error = False
        except ValueError:
            error = True
        if error != step.get("expect_error", False):
            raise AssertionError(f"step {step['tool']}: expected error={step.get('expect_error', False)}, got {error}")
    if submitted is None:
        return {"error": "the agent ended the task without calling submit"}
    output = build_output(submitted, output_class)
    return verifier.verify_task(task.value, arguments, output, reference, str(workspace))


def matches(found: dict, expect: dict) -> list[str]:
    """What differs between a verdict (or a refusal) and a case's expectation."""
    if "error" in found:
        return [f"the run was refused: {found['error']}"]
    problems = []
    if "valid" in expect and found["valid"] != expect["valid"]:
        problems.append(f"valid={found['valid']} expected {expect['valid']}: {found['message']}")
    if "score_min" in expect and found["score"] < expect["score_min"]:
        problems.append(f"score {found['score']} below {expect['score_min']}")
    if "score_max" in expect and found["score"] > expect["score_max"]:
        problems.append(f"score {found['score']} above {expect['score_max']}")
    if "message_contains" in expect and expect["message_contains"] not in found["message"]:
        problems.append(f"message {found['message']!r} lacks {expect['message_contains']!r}")
    return problems
