"""Чтение треков из JSON, сохранённого плагином json (работает без сети)."""

import json
from pathlib import Path

from spotexport.models import Track


def load_tracks_json(path: Path) -> list[Track]:
    """Прочитать файл, который выдал `-f json`, обратно в список Track."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path.name}: expected a JSON array of tracks")
    tracks = []
    for index, item in enumerate(data):
        try:
            tracks.append(
                Track(
                    id=str(item["id"]),
                    title=str(item["title"]),
                    artists=tuple(str(a) for a in item["artists"]),
                    album=str(item["album"]),
                    duration_ms=int(item["duration_ms"]),
                    explicit=bool(item.get("explicit", False)),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{path.name}, track #{index}: {exc}") from exc
    return tracks
