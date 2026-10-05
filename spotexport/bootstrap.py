"""Точка сборки: здесь плагины и клиент Spotify подключаются к ядру.

Это единственный модуль пакета, который знает и о протоколе, и о
конкретных плагинах. mypy проверяет каждый register(): объект должен
структурно соответствовать TrackExporter.
"""

import os
from pathlib import Path

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

from spotexport.plugins.csv_exporter import CsvExporter
from spotexport.plugins.json_exporter import JsonExporter
from spotexport.plugins.m3u_exporter import M3uExporter
from spotexport.protocols import TrackExporter
from spotexport.registry import Registry
from spotexport.spotify import SpotifyApi

DEFAULT_REDIRECT_URI = "http://127.0.0.1:8888/callback"
TOKEN_CACHE = ".spotifycache"
# Локальный файл с ключами (в .gitignore); образец - .env.example
ENV_FILE = ".env"


def build_registry() -> Registry[TrackExporter]:
    """Реестр со всеми встроенными экспортёрами."""
    registry: Registry[TrackExporter] = Registry()
    registry.register("csv", CsvExporter())
    registry.register("json", JsonExporter())
    registry.register("m3u", M3uExporter())
    return registry


def load_env_file(path: Path) -> None:
    """Прочитать строки KEY=VALUE в os.environ (уже заданные переменные важнее)."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def make_spotify_api(user_login: bool) -> SpotifyApi:
    """Клиент spotipy.

    Ключи приложения берутся из переменных окружения SPOTIPY_CLIENT_ID и
    SPOTIPY_CLIENT_SECRET или из файла .env.

    user_login=True - вход пользователя через браузер (OAuth). Нужен только
    для плейлистов: с февраля 2026 Spotify отдаёт их содержимое лишь владельцу
    или соавтору. Токен кэшируется в .spotifycache, браузер открывается один раз.
    user_login=False - только ключ приложения: хватает для альбомов, треков и поиска.
    """
    load_env_file(Path(ENV_FILE))
    auth: SpotifyOAuth | SpotifyClientCredentials
    if user_login:
        auth = SpotifyOAuth(
            redirect_uri=os.environ.get("SPOTIPY_REDIRECT_URI", DEFAULT_REDIRECT_URI),
            scope="playlist-read-private playlist-read-collaborative",
            cache_path=TOKEN_CACHE,
            open_browser=True,
        )
    else:
        auth = SpotifyClientCredentials()
    api: SpotifyApi = spotipy.Spotify(auth_manager=auth, requests_timeout=15)
    return api
