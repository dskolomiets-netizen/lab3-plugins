"""Получение треков из Spotify Web API.

Сам HTTP и вход через OAuth делает библиотека spotipy. Здесь она описана
протоколом SpotifyApi: spotipy.Spotify подходит под него структурно, а в
тестах его заменяет фейк без сети.
"""

import re
from collections.abc import Iterator
from typing import Any, Literal, Protocol, cast

from spotexport.models import Track

# Ответы API - это JSON, его форму mypy не знает
JsonDict = dict[str, Any]
LinkKind = Literal["playlist", "album", "track"]

# open.spotify.com/playlist/ID, open.spotify.com/intl-ru/album/ID?si=..., spotify:track:ID
LINK_RE = re.compile(
    r"(?:open\.spotify\.com/(?:intl-[\w-]+/)?|spotify:)(playlist|album|track)[/:]([0-9A-Za-z]{22})"
)
# С февраля 2026 поиск отдаёт не больше 10 результатов за запрос
SEARCH_LIMIT = 10


class SpotifyApi(Protocol):
    """Методы spotipy.Spotify, которыми пользуется SpotifySource."""

    def track(self, track_id: str) -> JsonDict: ...

    def album(self, album_id: str) -> JsonDict: ...

    def playlist_items(
        self, playlist_id: str, *, limit: int, additional_types: tuple[str, ...]
    ) -> JsonDict: ...

    def search(self, q: str, *, limit: int, type: str) -> JsonDict: ...

    def next(self, result: JsonDict) -> JsonDict: ...


def parse_link(link: str) -> tuple[LinkKind, str]:
    """Ссылка или URI Spotify -> (тип, ID)."""
    match = LINK_RE.search(link)
    if match is None:
        raise ValueError(f"not a Spotify playlist/album/track link: {ascii(link)}")
    return cast(LinkKind, match.group(1)), match.group(2)


def track_from_json(data: JsonDict | None, album: str | None = None) -> Track | None:
    """Объект трека из API -> Track. Локальные файлы и подкасты пропускаем (None)."""
    if not data or data.get("type", "track") != "track" or not data.get("id"):
        return None
    return Track(
        id=str(data["id"]),
        title=str(data["name"]),
        artists=tuple(str(artist["name"]) for artist in data["artists"]),
        # У треков внутри альбома поля album нет - имя альбома передаём сами
        album=str(album if album is not None else data["album"]["name"]),
        duration_ms=int(data["duration_ms"]),
        explicit=bool(data.get("explicit", False)),
    )


class SpotifySource:
    """Достаёт треки плейлиста, альбома, одного трека или поиска."""

    def __init__(self, api: SpotifyApi) -> None:
        self._api = api

    def tracks(self, link: str) -> list[Track]:
        kind, spotify_id = parse_link(link)
        if kind == "playlist":
            return self.playlist(spotify_id)
        if kind == "album":
            return self.album(spotify_id)
        track = track_from_json(self._api.track(spotify_id))
        return [track] if track else []

    def playlist(self, playlist_id: str) -> list[Track]:
        page = self._api.playlist_items(playlist_id, limit=50, additional_types=("track",))
        if "items" not in page:
            raise ValueError(
                "Spotify hid the playlist contents: only its owner or collaborators can read it"
            )
        # С февраля 2026 трек лежит в поле "item", раньше было "track"
        found = (track_from_json(it.get("item") or it.get("track")) for it in self._pages(page))
        return [t for t in found if t is not None]

    def album(self, album_id: str) -> list[Track]:
        album = self._api.album(album_id)
        found = (track_from_json(t, album=album["name"]) for t in self._pages(album["tracks"]))
        return [t for t in found if t is not None]

    def search(self, query: str, limit: int = SEARCH_LIMIT) -> list[Track]:
        limit = max(1, min(limit, SEARCH_LIMIT))
        result = self._api.search(q=query, limit=limit, type="track")
        found = (track_from_json(t) for t in result["tracks"]["items"])
        return [t for t in found if t is not None]

    def _pages(self, page: JsonDict) -> Iterator[JsonDict]:
        """Элементы всех страниц: API отдаёт списки кусками по 50."""
        while True:
            yield from page["items"]
            if not page.get("next"):
                return
            page = self._api.next(page)
