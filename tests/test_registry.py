"""Registry[T]: тип T сохраняется, неверные имена отклоняются."""

from typing import assert_type

import pytest

from spotexport.bootstrap import build_registry
from spotexport.plugins.csv_exporter import CsvExporter
from spotexport.protocols import TrackExporter
from spotexport.registry import Registry, UnknownNameError


class NotAnExporter:
    description = "has no export() method"


def test_registry_keeps_type_and_checks_names() -> None:
    # assert_type проверяет mypy: если бы get() возвращал Any или object,
    # mypy --strict упал бы на этих строках
    numbers: Registry[int] = Registry()
    numbers.register("one", 1)
    assert_type(numbers.get("one"), int)
    assert_type(numbers.items(), list[tuple[str, int]])
    assert numbers.items() == [("one", 1)] and "one" in numbers

    exporters = build_registry()
    assert_type(exporters.get("csv"), TrackExporter)
    assert exporters.names() == ["csv", "json", "m3u"]

    with pytest.raises(ValueError, match="already registered"):
        exporters.register("csv", CsvExporter())
    with pytest.raises(ValueError, match="invalid name"):
        exporters.register("Bad Name", CsvExporter())
    with pytest.raises(UnknownNameError, match="known: csv, json, m3u"):
        exporters.get("xml")

    # strict включает warn_unused_ignores: если бы mypy НЕ считал эту строку
    # ошибкой, лишний ignore сам стал бы ошибкой. Значит, mypy отвергает
    # объект без export(). В рантайме проверки нет - это стирание типов.
    exporters.register("bad", NotAnExporter())  # type: ignore[arg-type]
    assert "bad" in exporters
