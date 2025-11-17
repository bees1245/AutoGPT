from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from forge.utils import token_registry


def configure_temp_storage(tmp_path: Path) -> None:
    pages_dir = tmp_path / "pages"
    db_path = tmp_path / "tokens.sqlite3"
    token_registry.configure_storage(
        pages_dir=str(pages_dir),
        db_path=str(db_path),
    )


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


def test_database_lookup_recovers_persisted_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure_temp_storage(tmp_path)
    token_registry.reset_registry()
    monkeypatch.setattr(token_registry.time, "time", lambda: 1_700_000_000)

    evidence = b"stored evidence"
    first = token_registry.handle_event(domain=3, category=4, evidence_bytes=evidence)
    assert first["fast"] is False

    token_registry.TOKEN_REGISTRY.clear()
    configure_temp_storage(tmp_path)

    second = token_registry.handle_event(domain=3, category=4, evidence_bytes=evidence)

    assert second["fast"] is True
    assert second["policy"] == first["policy"]


def test_cache_hydrates_before_lookup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    configure_temp_storage(tmp_path)
    token_registry.reset_registry()
    monkeypatch.setattr(token_registry.time, "time", lambda: 1_700_000_000)

    evidence = b"rehydrate evidence"

    first = token_registry.handle_event(domain=5, category=6, evidence_bytes=evidence)

    assert first["fast"] is False

    token_registry.configure_storage(
        pages_dir=str(tmp_path / "pages"),
        db_path=str(tmp_path / "tokens.sqlite3"),
    )

    second = token_registry.handle_event(domain=5, category=6, evidence_bytes=evidence)

    assert second["fast"] is True
    assert second["policy"] == first["policy"]


def test_handle_event_registers_and_uses_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    configure_temp_storage(tmp_path)
    token_registry.reset_registry()
    monkeypatch.setattr(token_registry.time, "time", lambda: 1_700_000_000)

    evidence = b"audio_sample_bytes_example"

    first = token_registry.handle_event(
        domain=1,
        category=2,
        evidence_bytes=evidence,
        language="es",
    )

    assert first["fast"] is False
    assert first["policy"]["action"] == "quarantine"
    assert "leaf" in first["policy"]

    # ensure marker file was written and matches expectations
    marker_file = tmp_path / "pages" / "page_28333333.jsonl"
    assert marker_file.exists()
    with marker_file.open("r", encoding="utf8") as fh:
        marker_line = fh.readline()
    record = json.loads(marker_line)
    assert record["marker"]["token"] == first["token"]
    assert record["marker"]["language"] == "es"
    assert (
        record["marker"]["marker_phrase"]
        == token_registry.get_bible_marker("es")
    )

    # ensure policy persisted to the database
    with sqlite3.connect(token_registry.DB_PATH) as conn:
        stored = conn.execute("SELECT policy_json FROM tokens").fetchall()
    assert len(stored) == 1

    second = token_registry.handle_event(domain=1, category=2, evidence_bytes=evidence)

    assert second["fast"] is True
    assert second["policy"] == first["policy"]


def test_get_bible_marker_translations() -> None:
    assert token_registry.get_bible_marker("en") == token_registry.BIBLE_MARKER
    assert "entropy automate" in token_registry.BIBLE_MARKER
    spanish = token_registry.get_bible_marker("es")
    assert spanish.startswith("BIBLIA")
    french = token_registry.get_bible_marker("fr")
    assert "entrop" in french.lower()
    fallback = token_registry.get_bible_marker("xx")
    assert fallback == token_registry.BIBLE_MARKER


@pytest.mark.parametrize(
    "name",
    [
        "blake2s128_hex",
        "configure_storage",
        "get_bible_marker",
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

