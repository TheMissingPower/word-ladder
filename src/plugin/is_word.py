from __future__ import annotations

from pathlib import Path

from contract import IsWordInput, IsWordOutput
from plugin.dictionary import WORDS


def is_word(given: IsWordInput, workspace: Path) -> IsWordOutput:
    return IsWordOutput(word=given.word, is_word=given.word in WORDS)
