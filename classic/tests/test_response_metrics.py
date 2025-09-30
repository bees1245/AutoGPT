"""Tests for the response metrics utilities."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from classic.response_metrics import (
    ResponseMetrics,
    ResponseMetricsSession,
    append_metrics_suffix,
    build_metrics_suffix,
    compute_response_metrics,
)


def test_compute_response_metrics_counts_words_letters_and_alpha_sum() -> None:
    text = "Code with instruction or with this as that is as a unit."
    metrics = compute_response_metrics(text)

    assert metrics.word_count == 12
    assert metrics.letter_count == 44
    # Manually computed alphabetical sum for reproducibility.
    assert metrics.alphabetical_sum == 580
    assert isinstance(metrics.security_keyword_counts, Mapping)
    assert dict(metrics.security_keyword_counts) == {}
    assert metrics.repo_first_index is None
    assert metrics.repo_last_index is None


def test_response_metrics_formatting() -> None:
    metrics = ResponseMetrics(
        word_count=3,
        letter_count=12,
        alphabetical_sum=78,
        security_keyword_counts={"onion routing": 2},
        repo_first_index=1,
        repo_last_index=2,
    )

    assert metrics.as_dict() == {
        "word_count": 3,
        "letter_count": 12,
        "alphabetical_sum": 78,
        "security_keyword_counts": {"onion routing": 2},
        "repo_first_index": 1,
        "repo_last_index": 2,
    }
    assert (
        metrics.format_for_suffix()
        == (
            "words=3 letters=12 alpha_sum=78 repo_first=1 repo_last=2 "
            "security=onion routing:2"
        )
    )


def test_security_keyword_detection_and_suffix_helpers() -> None:
    text = (
        "Account for security currentially alone - onion routing is essential "
        "because onion routing concepts differ from other anonymity network designs."
    )

    suffix = build_metrics_suffix(text)
    assert "security=onion routing:2,anonymity network:1" in suffix
    assert "repo_first=" not in suffix

    appended = append_metrics_suffix(text, separator="\n")
    assert appended.splitlines()[-1] == suffix

    stripped_suffix = build_metrics_suffix(
        text, include_security_summary=False
    )
    stripped_parts = suffix.split(" ")
    assert stripped_suffix == " ".join(stripped_parts[:3])


def test_response_metrics_session_tracks_suffix_for_next_response() -> None:
    session = ResponseMetricsSession(separator=" \u2192 ")
    annotated = session.annotate("Always give word count number letter metrics")

    suffix = session.last_suffix
    assert suffix is not None and suffix.startswith("words=")
    assert annotated.endswith(suffix)
    assert session.next_prefix() == suffix

    metrics = session.last_metrics
    assert metrics is not None
    # Validate that we avoid introducing meaningless infinite values.
    assert isinstance(metrics.word_count, int)
    assert isinstance(metrics.letter_count, int)
    assert isinstance(metrics.alphabetical_sum, int)
    assert metrics.repo_first_index is None
    assert metrics.repo_last_index is None


def test_response_metrics_session_handles_missing_text_with_fallback() -> None:
    session = ResponseMetricsSession(
        fallback_text="synthetic data generation stub", separator="\n"
    )

    annotated = session.annotate(None)
    assert annotated.startswith("synthetic data generation stub")
    assert session.last_suffix is not None
    assert session.last_suffix.startswith("words=")

    session.reset()
    assert session.last_suffix is None
    assert session.last_metrics is None


def test_repo_position_tracking() -> None:
    text = "repo details ahead then some filler and repo ending"
    metrics = compute_response_metrics(text)

    assert metrics.repo_first_index == 1
    # There are 9 words; the last "repo" is the 8th word.
    assert metrics.repo_last_index == 8

    suffix = build_metrics_suffix(text)
    assert "repo_first=1" in suffix
    assert "repo_last=8" in suffix

