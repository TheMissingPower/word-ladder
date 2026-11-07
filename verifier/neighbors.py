"""neighbors' checks: dictionary words in, and out each one's exact one-letter neighbors, in order."""

from .checks import result, word_problem
from .words import WORDS


def one_letter_neighbors(word):
    """Every dictionary word differing from ``word`` in exactly one position, by a brute-force scan."""
    return sorted(
        other for other in WORDS if len(other) == len(word) and sum(a != b for a, b in zip(word, other)) == 1
    )


def verify_input(value):
    if not value.words:
        return result(False, "neighbors needs at least 1 word")
    for index, word in enumerate(value.words):
        problem = word_problem(word, f"word {index + 1}")
        if problem:
            return result(False, problem)
    return result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    asked = list(input_value.words)
    answered = [entry.word for entry in output_value.results]
    if answered != asked:
        return result(False, f"the output answers {answered}, not the words asked, {asked}")
    for entry in output_value.results:
        expected = one_letter_neighbors(entry.word)
        if list(entry.neighbors) != expected:
            return result(False, f"{entry.word!r} has neighbors {expected}, not {list(entry.neighbors)}")
    return result(True, "every entry matches the dictionary", words=len(asked))
