"""Ядро: вызывает экспортёры только через протокол TrackExporter.

Конкретные плагины сюда не импортируются. Они подключаются во внешней
точке сборки (spotexport/bootstrap.py или любой ваш скрипт), поэтому
новый плагин не требует правки этого файла.
"""

from collections.abc import Sequence

from spotexport.models import Track
from spotexport.protocols import TrackExporter
from spotexport.registry import Registry
from spotexport.text import to_ascii


def export_with(exporter: TrackExporter, tracks: Sequence[Track]) -> str:
    """Вызвать любой объект, подходящий под протокол.

    Плагин может вернуть кириллицу; ядро в одном месте приводит
    результат к ASCII, так что ни один плагин об этом не заботится.
    """
    return to_ascii(exporter.export(tracks))


class Dispatcher:
    """Выбирает экспортёр по имени из реестра и запускает его."""

    def __init__(self, exporters: Registry[TrackExporter]) -> None:
        self._exporters = exporters

    def names(self) -> list[str]:
        return self._exporters.names()

    def available(self) -> list[tuple[str, str]]:
        """Пары (имя, описание) всех подключённых плагинов."""
        return [(name, e.description) for name, e in self._exporters.items()]

    def export(self, name: str, tracks: Sequence[Track]) -> str:
        """Выгрузить треки плагином с именем name."""
        return export_with(self._exporters.get(name), tracks)
