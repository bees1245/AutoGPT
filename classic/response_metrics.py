"""Utilities for generating conversational response metrics.

This module provides helpers for computing lightweight statistics about
textual responses.  The goal is to make it simple to append information such
as word counts or alphabetical character totals at the end of a message – a
pattern that some conversational workflows rely on.

The implementation is deliberately dependency free so it can be reused from
either the classic CLI tools or ad-hoc scripts without pulling in the broader
AutoGPT runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict


WORD_PATTERN = re.compile(r"\b[\w'-]+\b")


@dataclass(frozen=True)
class ResponseMetrics:
    """Container describing simple statistics for a text snippet."""

    word_count: int
    letter_count: int
    alphabetical_sum: int

    def as_dict(self) -> Dict[str, int]:
        """Return the metrics as a plain dictionary."""

        return {
            "word_count": self.word_count,
            "letter_count": self.letter_count,
            "alphabetical_sum": self.alphabetical_sum,
        }

    def format_for_suffix(self) -> str:
        """Format the metrics as a compact suffix for conversational use."""

        return (
            f"words={self.word_count} "
            f"letters={self.letter_count} "
            f"alpha_sum={self.alphabetical_sum}"
        )


def _alphabet_position(char: str) -> int:
    """Return the alphabetical index for ``char`` (a=1, b=2, … z=26)."""

    return ord(char.lower()) - 96


def compute_response_metrics(text: str) -> ResponseMetrics:
    """Compute simple statistics describing ``text``.

    The metrics are intentionally aligned with a common conversational request:

    - ``word_count`` counts natural words using a permissive regular expression
      that keeps apostrophes and hyphenated compounds together.
    - ``letter_count`` counts only alphabetical characters, ignoring digits and
      punctuation.
    - ``alphabetical_sum`` adds the alphabetical positions (a=1 … z=26) for the
      letters that appear in the text.  Non-letter characters are ignored.

    Parameters
    ----------
    text:
        Input string to analyse.

    Returns
    -------
    ResponseMetrics
        A dataclass containing the computed metrics.
    """

    words = WORD_PATTERN.findall(text)
    letters = [char for char in text if char.isalpha()]
    alpha_sum = sum(_alphabet_position(char) for char in letters)

    return ResponseMetrics(
        word_count=len(words),
        letter_count=len(letters),
        alphabetical_sum=alpha_sum,
    )


__all__ = ["ResponseMetrics", "compute_response_metrics"]

