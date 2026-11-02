"""Checks shared by the verifiers. Pure functions of their arguments and the frozen word list."""

import re
from collections import deque
from string import ascii_lowercase

from .words import WORDS

LENGTH = 4
LETTERS = re.compile(r"[a-z]+")


def result(valid, message, *, score=None, **details):
    return {
        "valid": valid,
        "score": float(valid) if score is None else score,
        "message": message,
        "details": details,
    }


def word_problem(word, name):
    """What makes ``word`` no puzzle word, or None."""
    if not LETTERS.fullmatch(word):
        return f"{name} {word!r} is not lowercase ASCII letters"
    if len(word) != LENGTH:
        return f"{name} {word!r} does not have {LENGTH} letters"
    if word not in WORDS:
        return f"{name} {word!r} is not in the dictionary"
    return None


def changed_letters(before, after):
    return sum(1 for a, b in zip(before, after) if a != b)


def optimal_length(start, end):
    """The number of words in a shortest ladder from ``start`` to ``end``, by BFS, or None when there is none."""
    steps = {start: 0}
    queue = deque([start])
    while queue:
        word = queue.popleft()
        if word == end:
            return steps[word] + 1
        for i in range(len(word)):
            for letter in ascii_lowercase:
                after = word[:i] + letter + word[i + 1 :]
                if after in WORDS and after not in steps:
                    steps[after] = steps[word] + 1
                    queue.append(after)
    return None
