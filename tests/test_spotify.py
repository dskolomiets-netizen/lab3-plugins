"""Источник треков Spotify на фейковом API: без сети и без ключей."""

import pytest

from spotexport.spotify import JsonDict, SpotifySource, parse_link


def track_json(spotify_id: str | None, name: str, album: str | None = None) -> JsonDict:
    """Объект трека в формате Spotify Web API."""
    data: JsonDict = {
        "type": "track",
        "id": spotify_id,
        "name": name,
        "artists": [{"name": "Linkin Park"}],
        "duration_ms": 187520,
        "explicit": False,
    }
    if album is not None:
        data["album"] = {"name": album}
    return data


NUMB = track_json("2nLtzopw4rPReszdYBJU6h", "Numb", "Meteora")
FAINT = track_json("4WmrBYIxDqZ3DJNwKuWU4b", "Faint", "Meteora")
# Локальный файл: id нет
LOCAL_FILE = track_json(None, "my_demo.mp3", "") | {"is_local": True}
EPISODE = {"type": "episode", "id": "5mP2Wrzp9ZPCBoAXMIJ0MM", "name": "Podcast"}
# Трек, недоступный в стране аккаунта: Spotify присылает его с пустыми полями
UNAVAILABLE = track_json("5owX8aH0A5ODOmFmD32NQe", "", "") | {
    "artists": [{"name": ""}], "duration_ms": 0, "restrictions": {"reason": "market"}
}


class FakeSpotify:
    """Отвечает как spotipy.Spotify, но из памяти."""

    def __init__(self) -> None:
        self.search_limit = 0

    def track(self, track_id: str) -> JsonDict:
        return NUMB

    def album(self, album_id: str) -> JsonDict:
        # У треков внутри альбома поля album нет
        return {"name": "Meteora", "tracks": {"items": [track_json(NUMB["id"], "Numb")],
                                              "next": None}}

    def playlist_items(
        self, playlist_id: str, *, limit: int, additional_types: tuple[str, ...]
    ) -> JsonDict:
        # Страница 1 в новом формате ("item"), есть ссылка на страницу 2
        return {"items": [{"item": NUMB}, {"item": LOCAL_FILE}], "next": "page-2"}

    def next(self, result: JsonDict) -> JsonDict:
        # Страница 2: старый формат ("track"), подкаст и недоступный трек
        return {"items": [{"track": FAINT}, {"item": EPISODE}, {"item": UNAVAILABLE}],
                "next": None}

    def search(self, q: str, *, limit: int, type: str) -> JsonDict:
        self.search_limit = limit
        return {"tracks": {"items": [NUMB, FAINT], "next": None}}


def test_spotify_source_with_fake_api() -> None:
    assert parse_link(
        "https://open.spotify.com/intl-ru/playlist/1xcEiU8kWoQN3O825U31bl?si=abc"
    ) == ("playlist", "1xcEiU8kWoQN3O825U31bl")
    assert parse_link("spotify:album:4Gfnly5CzMJQqkUFfoHaP3") == (
        "album", "4Gfnly5CzMJQqkUFfoHaP3"
    )
    with pytest.raises(ValueError, match="not a Spotify"):
        parse_link("https://music.yandex.ru/album/1")

    fake = FakeSpotify()
    source = SpotifySource(fake)  # mypy проверяет, что фейк подходит под SpotifyApi

    # Плейлист: две страницы; негодные элементы пропущены и посчитаны,
    # а не роняют всю выгрузку
    playlist = source.tracks("https://open.spotify.com/playlist/1xcEiU8kWoQN3O825U31bl")
    assert [t.title for t in playlist] == ["Numb", "Faint"]
    assert source.skipped == {
        "local file": 1, "podcast episode": 1, "unavailable in your region": 1
    }
    # Альбом: имя альбома берётся из самого альбома
    album = source.tracks("https://open.spotify.com/album/4Gfnly5CzMJQqkUFfoHaP3")
    assert [(t.title, t.album) for t in album] == [("Numb", "Meteora")]
    # Один трек
    [numb] = source.tracks("https://open.spotify.com/track/2nLtzopw4rPReszdYBJU6h")
    assert numb.url == "https://open.spotify.com/track/2nLtzopw4rPReszdYBJU6h"
    # Поиск: лимит урезается до 10 - максимум API с февраля 2026
    assert len(source.search("numb", limit=50)) == 2
    assert fake.search_limit == 10
