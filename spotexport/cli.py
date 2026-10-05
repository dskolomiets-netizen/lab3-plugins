"""Командная строка: python -m spotexport <ссылка> -f csv|json|m3u."""

import argparse
import io
import sys
from collections.abc import Sequence
from pathlib import Path

from spotipy.exceptions import SpotifyBaseException

from spotexport.bootstrap import build_registry, make_spotify_api
from spotexport.core import Dispatcher
from spotexport.loader import load_tracks_json
from spotexport.models import Track
from spotexport.spotify import SEARCH_LIMIT, NetworkError, SpotifySource, parse_link
from spotexport.text import to_ascii


def _force_ascii(stream: object) -> None:
    # Любой не-ASCII символ (например, из аргументов) печатается как \uXXXX
    if isinstance(stream, io.TextIOWrapper):
        stream.reconfigure(encoding="ascii", errors="backslashreplace")


def _load(args: argparse.Namespace) -> list[Track]:
    if args.from_json:
        return load_tracks_json(args.from_json)
    # Битая ссылка - ошибка ещё до обращения к Spotify
    kind = parse_link(args.link)[0] if args.link else None
    # Вход через браузер нужен только для плейлистов
    source = SpotifySource(make_spotify_api(user_login=kind == "playlist"))
    tracks = source.search(args.search, args.limit) if args.search else source.tracks(args.link)
    if source.skipped:
        details = ", ".join(f"{reason}: {n}" for reason, n in source.skipped.most_common())
        print(f"note: skipped {source.skipped.total()} items ({details})", file=sys.stderr)
    return tracks


def main(argv: Sequence[str] | None = None) -> int:
    _force_ascii(sys.stdout)
    _force_ascii(sys.stderr)
    dispatcher = Dispatcher(build_registry())

    parser = argparse.ArgumentParser(
        prog="spotexport",
        description="Export Spotify tracks (playlist, album, track or search) "
        "with pluggable exporters.",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("link", nargs="?", help="Spotify playlist, album or track link")
    source.add_argument("-s", "--search", metavar="QUERY", help="search tracks by text")
    source.add_argument(
        "--from-json", type=Path, metavar="FILE", help="read tracks saved earlier with -f json"
    )
    parser.add_argument(
        "-f", "--format", default="csv", choices=dispatcher.names(), help="default: csv"
    )
    parser.add_argument("-o", "--output", type=Path, metavar="FILE", help="write to FILE")
    parser.add_argument(
        "--limit", type=int, default=SEARCH_LIMIT, help=f"search results, 1..{SEARCH_LIMIT}"
    )
    parser.add_argument("--list", action="store_true", help="show exporters and exit")
    args = parser.parse_args(argv)

    if args.list:
        for name, description in dispatcher.available():
            print(f"{name:<6}{description}")
        return 0
    if not (args.link or args.search or args.from_json):
        parser.error("give a Spotify link, --search QUERY or --from-json FILE")

    try:
        tracks = _load(args)
        text = dispatcher.export(args.format, tracks)
        if args.output:
            args.output.write_text(text + "\n", encoding="ascii")
            print(f"saved {len(tracks)} tracks to {args.output}")
        else:
            print(text)
    except SpotifyBaseException as exc:
        print(f"error: Spotify: {to_ascii(str(exc))}", file=sys.stderr)
        return 1
    except NetworkError as exc:
        print(f"error: {to_ascii(str(exc))}", file=sys.stderr)
        print("hint: check the internet connection / VPN and run again", file=sys.stderr)
        return 1
    except (OSError, ValueError, LookupError) as exc:
        print(f"error: {to_ascii(str(exc))}", file=sys.stderr)
        return 1
    return 0
