"""Пример: свой плагин подключается снаружи, код ядра не меняется.

Выдаёт список "Исполнитель - Название" - удобно вставлять в сервисы
переноса плейлистов. Запуск из корня репозитория:
    python -m examples.txt_plugin examples/tracks.json
"""

import sys
from collections.abc import Sequence
from pathlib import Path

from spotexport.bootstrap import build_registry
from spotexport.core import Dispatcher
from spotexport.loader import load_tracks_json
from spotexport.models import Track


# Ни наследования, ни импорта TrackExporter - только нужная форма
class TxtExporter:
    description = "plain list: Artist - Title"

    def export(self, tracks: Sequence[Track]) -> str:
        return "\n".join(f"{', '.join(t.artists)} - {t.title}" for t in tracks)


def main(argv: Sequence[str]) -> int:
    if len(argv) != 1:
        print("usage: python -m examples.txt_plugin FILE.json", file=sys.stderr)
        return 2
    # Внешняя точка сборки: берём встроенные плагины и добавляем свой
    registry = build_registry()
    registry.register("txt", TxtExporter())
    dispatcher = Dispatcher(registry)
    print(dispatcher.export("txt", load_tracks_json(Path(argv[0]))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
