"""Обобщённый реестр: имя -> объект типа T."""

import re
from collections.abc import Iterator
from typing import Generic, TypeVar

T = TypeVar("T")

# Имя в реестре: латиница в нижнем регистре, цифры, "-" и "_"
NAME_RE = re.compile(r"[a-z][a-z0-9_-]*")


class UnknownNameError(LookupError):
    """Запрошено имя, которого нет в реестре."""


class Registry(Generic[T]):
    """Хранит объекты одного типа T под строковыми именами.

    Все методы возвращают именно T, а не Any: если реестр объявлен как
    Registry[TrackExporter], то get() для mypy вернёт TrackExporter.
    """

    def __init__(self) -> None:
        self._items: dict[str, T] = {}

    def register(self, name: str, item: T) -> None:
        """Добавить объект под именем name; повторное имя - ошибка."""
        if not NAME_RE.fullmatch(name):
            raise ValueError(f"invalid name {ascii(name)}: use [a-z][a-z0-9_-]*")
        if name in self._items:
            raise ValueError(f"name {name!r} is already registered")
        self._items[name] = item

    def get(self, name: str) -> T:
        """Вернуть объект по имени или UnknownNameError."""
        try:
            return self._items[name]
        except KeyError:
            known = ", ".join(self.names()) or "<none>"
            raise UnknownNameError(f"unknown name {ascii(name)}, known: {known}") from None

    def names(self) -> list[str]:
        """Имена в алфавитном порядке."""
        return sorted(self._items)

    def items(self) -> list[tuple[str, T]]:
        """Пары (имя, объект) в алфавитном порядке имён."""
        return [(name, self._items[name]) for name in self.names()]

    def __contains__(self, name: object) -> bool:
        return name in self._items

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[str]:
        return iter(self.names())
