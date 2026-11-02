"""The solve-ladder task's check: any ladder that keeps every rule and is as short as the pinned optimum passes."""

from itertools import pairwise

from .checks import changed_letters, result, word_problem


def verify_task(arguments, output, reference, workspace):
    """``output``: a contract LadderOutput; ``reference``: the puzzle's pinned PuzzleOutput."""
    start, end, ladder = arguments.start, arguments.end, output.ladder
    if not reference.solvable:
        if output.solvable or ladder:
            return result(False, f"no ladder from {start} to {end} exists, but the output claims one")
        return result(True, f"correctly reports that no ladder from {start} to {end} exists")
    if not output.solvable:
        return result(False, f"a ladder from {start} to {end} exists, but the output says none does")
    if not ladder:
        return result(False, "solvable is true but the ladder is empty")
    if ladder[0] != start:
        return result(False, f"the ladder starts with {ladder[0]!r}, not {start!r}")
    if ladder[-1] != end:
        return result(False, f"the ladder ends with {ladder[-1]!r}, not {end!r}")
    for index, word in enumerate(ladder):
        problem = word_problem(word, f"word {index + 1}")
        if problem:
            return result(False, problem)
    for index, (before, after) in enumerate(pairwise(ladder)):
        changed = changed_letters(before, after)
        if changed != 1:
            return result(False, f"step {index + 1}, {before} -> {after}, changes {changed} letters, not 1")
    seen = set()
    for word in ladder:
        if word in seen:
            return result(False, f"{word!r} repeats")
        seen.add(word)
    if len(ladder) != reference.optimal_length:
        return result(
            False,
            f"not shortest: {len(ladder)} words, but a shortest ladder has {reference.optimal_length}",
            words=len(ladder),
            optimal_length=reference.optimal_length,
        )
    return result(True, f"a valid shortest ladder of {len(ladder)} words", ladder=ladder)
