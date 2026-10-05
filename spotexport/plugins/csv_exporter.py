"""Плагин: CSV-таблица (открывается в Excel)."""

import csv
import io
from collections.abc import Sequence

from spotexport.models import Track


class CsvExporter:
    description = "table: title, artists, album, duration, url"

    def __init__(self, delimiter: str = ",") -> None:
        self._delimiter = delimiter

    def export(self, tracks: Sequence[Track]) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=self._delimiter, lineterminator="\n")
        writer.writerow(["title", "artists", "album", "duration", "url"])
        for t in tracks:
            writer.writerow([t.title, ", ".join(t.artists), t.album, t.duration, t.url])
        return buf.getvalue().rstrip("\n")
