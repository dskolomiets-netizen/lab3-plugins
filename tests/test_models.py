"""Модель Track: свойства и негативные тесты валидации в __post_init__."""

from dataclasses import FrozenInstanceError, replace
from typing import Any

import pytest

from spotexport.models import Track

NUMB = Track(
    id="2nLtzopw4rPReszdYBJU6h",
    title="Numb",
    artists=("Linkin Park",),
    album="Meteora",
    duration_ms=187520,
)


def test_track_validation() -> None:
    assert NUMB.duration == "3:07"
    assert NUMB.url == "https://open.spotify.com/track/2nLtzopw4rPReszdYBJU6h"
    with pytest.raises(FrozenInstanceError):
        setattr(NUMB, "title", "Faint")

    bad_values: list[tuple[str, Any]] = [
        ("id", ""),
        ("id", "2nLtzopw4rPRes"),                # короче 22 символов
        ("id", "spotify:track:2nLtzopw4rP"),     # URI вместо ID
        ("id", "\u0430" * 22),                   # кириллица в ID
        ("title", ""),
        ("title", "   "),
        ("artists", ()),
        ("artists", ("Linkin Park", " ")),
        ("duration_ms", 0),
        ("duration_ms", -1),
    ]
    for field, value in bad_values:
        # replace() создаёт новый объект через __init__, значит, и __post_init__
        with pytest.raises(ValueError, match=field) as exc_info:
            replace(NUMB, **{field: value})
        assert str(exc_info.value).isascii()
