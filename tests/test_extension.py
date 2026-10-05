"""Сценарий расширения: новый плагин подключается без правки ядра."""

import ast
from collections.abc import Sequence
from pathlib import Path

import spotexport
from spotexport.bootstrap import build_registry
from spotexport.core import Dispatcher
from spotexport.models import Track

PACKAGE = Path(spotexport.__file__).parent


# Новый плагин: ни от чего не наследуется и не импортирует протокол
class TxtExporter:
    description = "plain list: Artist - Title"

    def export(self, tracks: Sequence[Track]) -> str:
        return "\n".join(f"{', '.join(t.artists)} - {t.title}" for t in tracks)


def _imports(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_new_plugin_works_without_core_changes(tracks: list[Track]) -> None:
    # Внешняя точка сборки: встроенные плагины + новый
    registry = build_registry()
    registry.register("txt", TxtExporter())
    dispatcher = Dispatcher(registry)

    assert ("txt", "plain list: Artist - Title") in dispatcher.available()
    assert dispatcher.export("txt", tracks) == (
        "Kino - Gruppa krovi\nJAY-Z, Linkin Park - Numb / Encore"
    )

    # Доказательство по исходникам: ядро не импортирует ни плагины,
    # ни точку сборки, ни spotipy - значит, его не нужно править
    for module in ("core.py", "registry.py", "protocols.py", "models.py"):
        imports = _imports(PACKAGE / module)
        assert not any(
            m.startswith(("spotexport.plugins", "spotexport.bootstrap", "spotipy"))
            for m in imports
        ), module

    # А плагины не импортируют протокол и ни от чего не наследуются
    plugin_files = sorted((PACKAGE / "plugins").glob("*_exporter.py"))
    assert len(plugin_files) >= 3
    for path in plugin_files:
        assert "spotexport.protocols" not in _imports(path), path.name
        tree = ast.parse(path.read_text(encoding="utf-8"))
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert classes and all(not c.bases for c in classes), path.name
