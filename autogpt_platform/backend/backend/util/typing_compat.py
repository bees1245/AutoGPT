"""Runtime compatibility helpers for optional typing features."""

from __future__ import annotations

from typing import Any, Callable

import typing_extensions as _typing_extensions


def _ensure_type_is() -> None:
    """Provide a no-op implementation of :func:`typing_extensions.TypeIs`."""

    if hasattr(_typing_extensions, "TypeIs"):
        return

    def _type_is(_: object) -> Callable[[Callable[[Any], bool]], Callable[[Any], bool]]:
        def _decorator(func: Callable[[Any], bool]) -> Callable[[Any], bool]:
            return func

        return _decorator

    _typing_extensions.TypeIs = _type_is  # type: ignore[attr-defined]

    all_attr = getattr(_typing_extensions, "__all__", None)
    if isinstance(all_attr, list) and "TypeIs" not in all_attr:
        all_attr.append("TypeIs")


_ensure_type_is()
