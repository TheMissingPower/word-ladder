"""is_word's checks: its answer is the word's membership in the frozen dictionary."""

from .checks import result
from .words import WORDS


def verify_input(value):
    if not value.word:
        return result(False, "word must not be empty")
    return result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    if output_value.word != input_value.word:
        return result(False, f"output names {output_value.word!r}, not the word asked about, {input_value.word!r}")
    expected = input_value.word in WORDS
    if output_value.is_word != expected:
        return result(False, f"{input_value.word!r} is {'' if expected else 'not '}in the dictionary")
    return result(True, "the answer matches the dictionary", is_word=expected)
