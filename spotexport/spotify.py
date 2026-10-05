"""Получение треков из Spotify Web API.

Сам HTTP и вход через OAuth делает библиотека spotipy. Здесь она описана
протоколом SpotifyApi: spotipy.Spotify подходит под него структурно, а в
тестах его заменяет фейк без сети.
"""

import re
import time
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from functools import partial
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
# Сеть до Spotify бывает нестабильной (VPN): запрос повторяем с паузой 2, 4 с
ATTEMPTS = 3
RETRY_DELAY = 2.0


class NetworkError(ConnectionError):
    """Spotify не ответил даже после повторных попыток."""


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


def skip_reason(data: JsonDict) -> str | None:
    """Почему элемент нельзя выгрузить как трек Spotify; None - можно."""
    if data.get("is_local"):
        return "local file"
    if data.get("type", "track") != "track":
        return "podcast episode"
    if not data.get("id"):
        return "no spotify id"
    if not data.get("name"):
        # Недоступный в стране аккаунта трек приходит с пустыми полями
        reason = (data.get("restrictions") or {}).get("reason")
        return "unavailable in your region" if reason == "market" else "empty track data"
    return None


def track_from_json(data: JsonDict, album: str | None = None) -> Track:
    """Объект трека из API -> Track; испорченные данные отвергнет __post_init__."""
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
    """Достаёт треки плейлиста, альбома, одного трека или поиска.

    Элементы, которые не являются доступными треками (локальные файлы,
    подкасты, недоступные в регионе), пропускаются и считаются в skipped.
    Каждый запрос при сбое сети повторяется (см. ATTEMPTS).
    """

    def __init__(self, api: SpotifyApi, retry_delay: float = RETRY_DELAY) -> None:
        self._api = api
        self._retry_delay = retry_delay
        self.skipped: Counter[str] = Counter()

    def tracks(self, link: str) -> list[Track]:
        kind, spotify_id = parse_link(link)
        if kind == "playlist":
            return self.playlist(spotify_id)
        if kind == "album":
            return self.album(spotify_id)
        return self._collect([self._call(partial(self._api.track, spotify_id))])

    def playlist(self, playlist_id: str) -> list[Track]:
        page = self._call(
            partial(self._api.playlist_items, playlist_id, limit=50, additional_types=("track",))
        )
        if "items" not in page:
            raise ValueError(
                "Spotify hid the playlist contents: only its owner or collaborators can read it"
            )
        # С февраля 2026 трек лежит в поле "item", раньше было "track"
        return self._collect(it.get("item") or it.get("track") for it in self._pages(page))

    def album(self, album_id: str) -> list[Track]:
        album = self._call(partial(self._api.album, album_id))
        return self._collect(self._pages(album["tracks"]), album=album["name"])

    def search(self, query: str, limit: int = SEARCH_LIMIT) -> list[Track]:
        limit = max(1, min(limit, SEARCH_LIMIT))
        result = self._call(partial(self._api.search, q=query, limit=limit, type="track"))
        return self._collect(result["tracks"]["items"])

    def _call(self, request: Callable[[], JsonDict]) -> JsonDict:
        """Выполнить запрос к API, при сбое сети повторив его с паузой."""
        for attempt in range(1, ATTEMPTS + 1):
            try:
                return request()
            except OSError as exc:
                # Таймауты и обрывы requests - подклассы OSError; ответы
                # Spotify с ошибкой (SpotifyException) сюда не попадают
                if attempt == ATTEMPTS:
                    raise NetworkError(
                        f"Spotify did not respond after {ATTEMPTS} attempts ({exc})"
                    ) from exc
                time.sleep(self._retry_delay * attempt)
        raise AssertionError("unreachable")

    def _collect(self, raw: Iterable[JsonDict | None], album: str | None = None) -> list[Track]:
        """Превратить объекты API в Track, пропуская и подсчитывая негодные."""
        tracks: list[Track] = []
        for data in raw:
            if not data:
                # "item": null - обычно трек удалён из каталога Spotify
                self.skipped["no data from Spotify"] += 1
                continue
            reason = skip_reason(data)
            if reason is None:
                try:
                    tracks.append(track_from_json(data, album))
                    continue
                except (KeyError, TypeError, ValueError):
                    # Валидация Track отсеяла испорченный ответ API
                    reason = "invalid track data"
            self.skipped[reason] += 1
        return tracks

    def _pages(self, page: JsonDict) -> Iterator[JsonDict]:
        """Элементы всех страниц: API отдаёт списки кусками по 50."""
        while True:
            yield from page["items"]
            if not page.get("next"):
                return
            page = self._call(partial(self._api.next, page))
