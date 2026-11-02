"""pin_puzzle's checks: the pinned answer key names the asked puzzle and agrees with a fresh BFS of the dictionary."""

from .checks import optimal_length, result, word_problem


def verify_input(value):
    problem = word_problem(value.start, "start") or word_problem(value.end, "end")
    if problem:
        return result(False, problem)
    if value.start == value.end:
        return result(False, "start and end must differ")
    return result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    if (output_value.start, output_value.end) != (input_value.start, input_value.end):
        return result(False, "the answer key is for another puzzle")
    if output_value.solvable != (output_value.optimal_length is not None):
        return result(False, "optimal_length must be set exactly when the puzzle is solvable")
    expected = optimal_length(input_value.start, input_value.end)
    if output_value.optimal_length != expected:
        return result(False, f"the answer key says {output_value.optimal_length}, BFS says {expected}")
    return result(True, "the answer key matches the dictionary", optimal_length=expected)
