"""Utilities for generating conversational response metrics.

This module provides helpers for computing lightweight statistics about
textual responses.  The goal is to make it simple to append information such
as word counts or alphabetical character totals at the end of a message – a
pattern that some conversational workflows rely on.

Alongside the general metrics we also expose minimal keyword analysis geared
around security and privacy conversations (for example *onion routing*).  This
allows callers to surface potentially sensitive topics alongside the numerical
breakdown so operators can make an informed decision before echoing a response.

The implementation is deliberately dependency free so it can be reused from
either the classic CLI tools or ad-hoc scripts without pulling in the broader
AutoGPT runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from types import MappingProxyType
from typing import Dict, Iterable, Mapping, Tuple


WORD_PATTERN = re.compile(r"\b[\w'-]+\b")

# Keywords that warrant additional scrutiny when they appear in conversational
# responses.  The list is intentionally short and focused on the request we are
# addressing ("security currentially alone - onion routing") but callers can
# pass their own set if they wish.
SECURITY_KEYWORDS: Tuple[str, ...] = (
    "onion routing",
    "tor",
    "tor network",
    "anonymity network",
)


def _empty_mapping() -> Mapping[str, int]:
    """Return an immutable empty mapping for security keyword counts."""

    return MappingProxyType({})


@dataclass(frozen=True)
class ResponseMetrics:
    """Container describing simple statistics for a text snippet."""

    word_count: int
    letter_count: int
    alphabetical_sum: int
    security_keyword_counts: Mapping[str, int] = field(default_factory=_empty_mapping)
    repo_first_index: int | None = None
    repo_last_index: int | None = None

    def as_dict(self) -> Dict[str, object]:
        """Return the metrics as a plain dictionary."""

        return {
            "word_count": self.word_count,
            "letter_count": self.letter_count,
            "alphabetical_sum": self.alphabetical_sum,
            "security_keyword_counts": dict(self.security_keyword_counts),
            "repo_first_index": self.repo_first_index,
            "repo_last_index": self.repo_last_index,
        }

    def has_security_mentions(self) -> bool:
        """Return ``True`` if any monitored security keywords were found."""

        return any(self.security_keyword_counts.values())

    def format_for_suffix(self) -> str:
        """Format the metrics as a compact suffix for conversational use."""

        parts = [
            f"words={self.word_count}",
            f"letters={self.letter_count}",
            f"alpha_sum={self.alphabetical_sum}",
        ]

        if self.repo_first_index is not None:
            parts.append(f"repo_first={self.repo_first_index}")
        if self.repo_last_index is not None:
            parts.append(f"repo_last={self.repo_last_index}")

        if self.has_security_mentions():
            keyword_bits = ",".join(
                f"{keyword}:{count}"
                for keyword, count in self.security_keyword_counts.items()
                if count
            )
            if keyword_bits:
                parts.append(f"security={keyword_bits}")

        return " ".join(parts)


def _alphabet_position(char: str) -> int:
    """Return the alphabetical index for ``char`` (a=1, b=2, … z=26)."""

    return ord(char.lower()) - 96


def compute_response_metrics(
    text: str,
    *,
    security_keywords: Iterable[str] | None = None,
) -> ResponseMetrics:
    """Compute simple statistics describing ``text``.

    The metrics are intentionally aligned with a common conversational request:

    - ``word_count`` counts natural words using a permissive regular expression
      that keeps apostrophes and hyphenated compounds together.
    - ``letter_count`` counts only alphabetical characters, ignoring digits and
      punctuation.
    - ``alphabetical_sum`` adds the alphabetical positions (a=1 … z=26) for the
      letters that appear in the text.  Non-letter characters are ignored.
    - ``security_keyword_counts`` tracks occurrences of security-sensitive
      keywords such as "onion routing".  The default list can be overridden via
      the ``security_keywords`` argument.

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

    keyword_set = (
        tuple(security_keywords)
        if security_keywords is not None
        else SECURITY_KEYWORDS
    )
    keyword_counts = _count_security_keywords(text, keyword_set)
    keyword_mapping = (
        MappingProxyType(dict(keyword_counts)) if keyword_counts else _empty_mapping()
    )

    lowered_words = [word.lower() for word in words]
    repo_indices = [index for index, word in enumerate(lowered_words, start=1) if word == "repo"]
    repo_first = repo_indices[0] if repo_indices else None
    repo_last = repo_indices[-1] if repo_indices else None

    return ResponseMetrics(
        word_count=len(words),
        letter_count=len(letters),
        alphabetical_sum=alpha_sum,
        security_keyword_counts=keyword_mapping,
        repo_first_index=repo_first,
        repo_last_index=repo_last,
    )


def _format_metrics_suffix(
    metrics: ResponseMetrics, *, include_security_summary: bool
) -> str:
    """Return the formatted suffix for ``metrics`` respecting security options."""

    suffix = metrics.format_for_suffix()

    if not include_security_summary and metrics.has_security_mentions():
        base_parts = suffix.split(" ")[:3]
        suffix = " ".join(base_parts)

    return suffix


def build_metrics_suffix(
    text: str,
    *,
    security_keywords: Iterable[str] | None = None,
    include_security_summary: bool = True,
) -> str:
    """Return a formatted suffix describing metrics for ``text``.

    Parameters
    ----------
    text:
        The response body to analyse.
    security_keywords:
    Optional iterable of keywords to surface alongside the general metrics. By
    default the helper scans for a short list centred on onion routing and
    related privacy terms.
    include_security_summary:
        When ``True`` (the default) any detected security keyword counts are
        appended to the suffix.  When ``False`` only the numeric metrics are
        reported.
    """

    metrics = compute_response_metrics(text, security_keywords=security_keywords)
    return _format_metrics_suffix(
        metrics, include_security_summary=include_security_summary
    )


def append_metrics_suffix(
    text: str,
    *,
    security_keywords: Iterable[str] | None = None,
    include_security_summary: bool = True,
    separator: str = "\n\n",
) -> str:
    """Append a metrics suffix to ``text``.

    The helper is primarily intended for conversational agents that must
    conclude their responses with the numeric summary requested by the user.
    It keeps the response body intact and appends a separator (``"\n\n"`` by
    default) followed by the formatted metrics suffix.  When security keywords
    are detected they are included alongside the numeric statistics so that the
    receiving system can apply onion-routing or other privacy safeguards if
    desired.
    """

    metrics = compute_response_metrics(text, security_keywords=security_keywords)
    suffix = _format_metrics_suffix(
        metrics, include_security_summary=include_security_summary
    )
    return f"{text}{separator}{suffix}" if suffix else text


@dataclass
class ResponseMetricsSession:
    """Stateful helper that carries metrics between conversation turns.

    The session captures the metrics suffix appended to each response so it can be
    surfaced at the *beginning* of the next response if desired.  This matches the
    user's requirement to always keep the word, letter, and alphabetical totals in
    mind for follow-up messages.  The session also supports producing annotated
    output even when no new user input is provided, by falling back to synthetic
    text suitable for automated training loops.
    """

    security_keywords: Iterable[str] | None = None
    include_security_summary: bool = True
    separator: str = "\n\n"
    fallback_text: str = ""

    _last_suffix: str | None = field(default=None, init=False, repr=False)
    _last_metrics: ResponseMetrics | None = field(default=None, init=False, repr=False)

    def annotate(self, text: str | None = None) -> str:
        """Append the metrics suffix to ``text`` and store it for later reuse."""

        body = self._resolve_body(text)
        metrics = compute_response_metrics(
            body, security_keywords=self.security_keywords
        )
        suffix = _format_metrics_suffix(
            metrics, include_security_summary=self.include_security_summary
        )

        self._last_suffix = suffix
        self._last_metrics = metrics

        if not suffix:
            return body
        return f"{body}{self.separator}{suffix}"

    def next_prefix(self) -> str:
        """Return the stored suffix so it can prefix the next response."""

        return self._last_suffix or ""

    @property
    def last_suffix(self) -> str | None:
        """Expose the suffix captured during the most recent call to ``annotate``."""

        return self._last_suffix

    @property
    def last_metrics(self) -> ResponseMetrics | None:
        """Return the metrics computed for the most recent response."""

        return self._last_metrics

    def reset(self) -> None:
        """Clear the stored suffix and metrics."""

        self._last_suffix = None
        self._last_metrics = None

    def _resolve_body(self, text: str | None) -> str:
        """Return ``text`` or fall back to synthetic content for training loops."""

        if text is None or text == "":
            return self.fallback_text
        return text


def _count_security_keywords(text: str, keywords: Iterable[str]) -> Dict[str, int]:
    """Return a mapping of keyword occurrences detected in ``text``.

    Matching is case-insensitive and literal (keywords are escaped prior to
    searching) to avoid surprises while still allowing multi-word phrases.
    """

    lowered_text = text.lower()
    counts: Dict[str, int] = {}
    for keyword in keywords:
        escaped = re.escape(keyword.lower())
        pattern = rf"(?<!\w){escaped}(?!\w)"
        count = len(re.findall(pattern, lowered_text))
        if count:
            counts[keyword] = count
    return counts


__all__ = [
    "ResponseMetrics",
    "append_metrics_suffix",
    "build_metrics_suffix",
    "compute_response_metrics",
    "ResponseMetricsSession",
]

