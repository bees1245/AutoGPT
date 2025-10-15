from __future__ import annotations

import json
from pathlib import Path

import pytest

from forge.utils import token_registry


def test_make_token_layout_preserves_severity_with_flags() -> None:
    token_hex = token_registry.make_token(
        domain=1,
        category=2,
        evidence_bytes=b"example evidence",
        severity=200,
        flags=0xBE,
    )

    token_bytes = bytes.fromhex(token_hex)

    assert len(token_bytes) == 12
    assert token_bytes[0] == 1  # domain
    assert token_bytes[1] == 2  # category
    assert token_bytes[8] == 200  # severity remains intact
    assert token_bytes[9] == 0xBE  # flags stay within their byte
    assert token_bytes[10] == 0  # reserved high byte
    assert token_bytes[11] == 0  # reserved low byte


def test_make_token_rejects_large_flags() -> None:
    with pytest.raises(ValueError):
        token_registry.make_token(
            domain=1,
            category=2,
            evidence_bytes=b"example",
            severity=10,
            flags=0x1FF,
        )


def test_handle_event_registers_and_uses_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(token_registry, "PAGES_DIR", str(tmp_path))
    monkeypatch.setattr(token_registry.time, "time", lambda: 1_700_000_000)
    token_registry.reset_registry()

    evidence = b"audio_sample_bytes_example"

    first = token_registry.handle_event(domain=1, category=2, evidence_bytes=evidence)

    assert first["fast"] is False
    assert first["policy"]["action"] == "quarantine"
    assert "leaf" in first["policy"]

    # ensure marker file was written and matches expectations
    marker_file = tmp_path / "page_28333333.jsonl"
    assert marker_file.exists()
    with marker_file.open("r", encoding="utf8") as fh:
        marker_line = fh.readline()
    record = json.loads(marker_line)
    assert record["marker"]["token"] == first["token"]

    second = token_registry.handle_event(domain=1, category=2, evidence_bytes=evidence)

    assert second["fast"] is True
    assert second["policy"] == first["policy"]


@pytest.mark.parametrize(
    "name",
    [
        "blake2s128_hex",
        "make_token",
        "emit_marker",
        "register_token",
        "handle_event",
        "reset_registry",
    ],
)
def test_docstrings_include_bible_marker(name: str) -> None:
    func = getattr(token_registry, name)
    assert token_registry.BIBLE_MARKER in (func.__doc__ or "")

