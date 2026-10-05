"""Модель данных: трек Spotify с валидацией в __post_init__."""

import re
from dataclasses import dataclass

# ID в Spotify: ровно 22 символа base62 (цифры и латиница)
SPOTIFY_ID_RE = re.compile(r"[0-9A-Za-z]{22}")


@dataclass(frozen=True, slots=True)
class Track:
    id: str
    title: str
    artists: tuple[str, ...]
    album: str
    duration_ms: int
    explicit: bool = False

    def __post_init__(self) -> None:
        # Сообщения только ASCII: чужие строки выводим через ascii()
        if not SPOTIFY_ID_RE.fullmatch(self.id):
            raise ValueError(f"id must be 22 base62 chars, got {ascii(self.id)}")
        if not self.title.strip():
            raise ValueError("title must not be empty")
        if not self.artists or not all(name.strip() for name in self.artists):
            raise ValueError("artists must be a non-empty list of names")
        if self.duration_ms <= 0:
            raise ValueError(f"duration_ms must be > 0, got {self.duration_ms!r}")

    @property
    def url(self) -> str:
        return f"https://open.spotify.com/track/{self.id}"

    @property
    def duration(self) -> str:
        """Длительность как в приложении Spotify: 4:44."""
        minutes, seconds = divmod(self.duration_ms // 1000, 60)
        return f"{minutes}:{seconds:02d}"
