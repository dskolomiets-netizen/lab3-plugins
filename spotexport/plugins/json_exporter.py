"""Плагин: JSON-массив (его же читает --from-json)."""

import json
from collections.abc import Sequence
from dataclasses import asdict

from spotexport.models import Track


class JsonExporter:
    description = "JSON array, can be read back with --from-json"

    def export(self, tracks: Sequence[Track]) -> str:
        data = [asdict(t) | {"url": t.url} for t in tracks]
        # ensure_ascii=True: кириллица сохраняется как \uXXXX и читается обратно без потерь
        return json.dumps(data, indent=2, ensure_ascii=True)
