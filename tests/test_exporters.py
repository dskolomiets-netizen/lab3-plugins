"""Позитивные тесты: каждый плагин даёт ожидаемый результат."""

import json
from pathlib import Path

from spotexport.core import export_with
from spotexport.loader import load_tracks_json
from spotexport.models import Track
from spotexport.plugins.csv_exporter import CsvExporter
from spotexport.plugins.json_exporter import JsonExporter
from spotexport.plugins.m3u_exporter import M3uExporter
from spotexport.protocols import TrackExporter

# Присваивание проверяет mypy: каждый плагин структурно подходит под протокол
_csv: TrackExporter = CsvExporter()
_json: TrackExporter = JsonExporter()
_m3u: TrackExporter = M3uExporter()


def test_csv_exporter(tracks: list[Track]) -> None:
    # Ядро транслитерирует кириллицу и снимает диакритику: вывод только ASCII
    assert export_with(CsvExporter(), tracks) == (
        "title,artists,album,duration,url\n"
        "Gruppa krovi,Kino,Gruppa krovi,4:44,"
        "https://open.spotify.com/track/4iRg9tHDgmRPvv56IC46Pl\n"
        'Numb / Encore,"JAY-Z, Linkin Park",Collision Course,3:25,'
        "https://open.spotify.com/track/5sNESr6pQfIhL3krM8CtZn"
    )


def test_json_exporter_round_trip(tracks: list[Track], tmp_path: Path) -> None:
    text = export_with(JsonExporter(), tracks)
    assert text.isascii()
    data = json.loads(text)
    assert data[1] == {
        "id": "5sNESr6pQfIhL3krM8CtZn",
        "title": "Numb / Encore",
        "artists": ["JA\u0178-Z", "Linkin Park"],
        "album": "Collision Course",
        "duration_ms": 205733,
        "explicit": True,
        "url": "https://open.spotify.com/track/5sNESr6pQfIhL3krM8CtZn",
    }
    # JSON хранит кириллицу как \uXXXX, поэтому читается обратно без потерь
    saved = tmp_path / "tracks.json"
    saved.write_text(text, encoding="ascii")
    assert load_tracks_json(saved) == tracks


def test_m3u_exporter(tracks: list[Track]) -> None:
    assert export_with(M3uExporter(), tracks).splitlines() == [
        "#EXTM3U",
        "#EXTINF:284,Kino - Gruppa krovi",
        "https://open.spotify.com/track/4iRg9tHDgmRPvv56IC46Pl",
        "#EXTINF:205,JAY-Z, Linkin Park - Numb / Encore",
        "https://open.spotify.com/track/5sNESr6pQfIhL3krM8CtZn",
    ]
