"""Tests for the response metrics utilities."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from classic.response_metrics import ResponseMetrics, compute_response_metrics


def test_compute_response_metrics_counts_words_letters_and_alpha_sum() -> None:
    text = "Code with instruction or with this as that is as a unit."
    metrics = compute_response_metrics(text)

    assert metrics.word_count == 12
    assert metrics.letter_count == 44
    # Manually computed alphabetical sum for reproducibility.
    assert metrics.alphabetical_sum == 580


def test_response_metrics_formatting() -> None:
    metrics = ResponseMetrics(word_count=3, letter_count=12, alphabetical_sum=78)

    assert metrics.as_dict() == {
        "word_count": 3,
        "letter_count": 12,
        "alphabetical_sum": 78,
    }
    assert metrics.format_for_suffix() == "words=3 letters=12 alpha_sum=78"

