"""Контракт плагина-экспортёра."""

from collections.abc import Sequence
from typing import Protocol

from spotexport.models import Track


class TrackExporter(Protocol):
    """Плагин превращает список треков в текст (CSV, JSON, M3U...).

    Реализации НЕ наследуются от этого класса и НЕ импортируют его:
    совместимость проверяет mypy структурно, по набору атрибутов и методов.
    """

    @property
    def description(self) -> str:
        """Короткое описание для --list."""
        ...

    def export(self, tracks: Sequence[Track]) -> str:
        """Вернуть треки в виде текста без завершающего перевода строки."""
        ...
