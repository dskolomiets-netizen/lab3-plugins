# spotexport

Выгрузка треков из Spotify (плейлист, альбом, отдельный трек или поиск) в
CSV, JSON или M3U. Форматы вывода - плагины, подключаемые через
`typing.Protocol`; реестр плагинов - обобщённый `Registry[T]` на `Generic[T]`;
трек - `@dataclass` с валидацией. Корректность типов подтверждает
`mypy --strict`. Лабораторная работа №3.

Ядро (`spotexport/core.py`) знает только протокол `TrackExporter` и реестр;
о конкретных плагинах знает лишь точка сборки `spotexport/bootstrap.py`.

## Структура пакета

```
spotexport/
  models.py          Track: @dataclass(frozen, slots) + проверки в __post_init__
  protocols.py       TrackExporter(Protocol): description + export(tracks) -> str
  registry.py        Registry[T](Generic[T]): register / get / names / items
  core.py            export_with() и Dispatcher - работают только через протокол
  text.py            to_ascii(): транслитерация, весь вывод - ASCII
  plugins/
    csv_exporter.py     CsvExporter   (csv)
    json_exporter.py    JsonExporter  (json)
    m3u_exporter.py     M3uExporter   (m3u)
  spotify.py         SpotifySource + протокол SpotifyApi (описывает spotipy)
  loader.py          чтение JSON, сохранённого через -f json (офлайн)
  bootstrap.py       точка сборки: плагины + клиент spotipy (ключи из .env)
  cli.py             командная строка (argparse)
examples/
  tracks.json        4 настоящих трека для офлайн-демонстрации
  txt_plugin.py      пример своего плагина, подключённого снаружи
tests/               pytest, 7 тестов, сеть не нужна
.env.example         образец файла с ключами Spotify
pyproject.toml       конфигурация mypy (strict = true) и pytest
requirements.txt     spotipy, pytest, mypy с точными версиями
```

Плагины не наследуются от общего класса и не импортируют
`spotexport.protocols`: под протокол они подходят структурно.

## Установка

Нужен Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

Пакет ставить не нужно: все команды запускаются из корня репозитория.

## Ключи Spotify

1. Зайдите на <https://developer.spotify.com/dashboard>, создайте приложение
   (Web API), в Redirect URIs добавьте `http://127.0.0.1:8888/callback`.
2. Скопируйте `.env.example` в `.env` и впишите Client ID и Client Secret.
   `.env` в `.gitignore` - ключи не попадают ни в код, ни в git. Вместо
   файла можно задать переменные окружения `SPOTIPY_CLIENT_ID` и
   `SPOTIPY_CLIENT_SECRET` - они важнее `.env`.

Альбомы, треки и поиск работают по одному ключу приложения. Для плейлиста
при первом запуске откроется браузер для входа в Spotify; токен сохранится
в `.spotifycache` (он тоже в `.gitignore`).

Ограничения API с февраля 2026: приложению в режиме разработки нужен
Spotify Premium у владельца; треки плейлиста отдаются только его владельцу
или соавтору (поэтому для плейлистов нужен вход пользователя); поиск
возвращает не больше 10 результатов.

## Запуск

```
python -m spotexport <ссылка>          [-f csv|json|m3u] [-o FILE]
python -m spotexport --search "ЗАПРОС" [--limit 1..10] [-f ...] [-o FILE]
python -m spotexport --from-json FILE  [-f ...] [-o FILE]
python -m spotexport --list
```

Ссылка - плейлист, альбом или трек: `https://open.spotify.com/playlist/...`,
`https://open.spotify.com/intl-ru/album/...?si=...`, `spotify:track:...`.

```bash
python -m spotexport https://open.spotify.com/playlist/<ID> -f csv -o my.csv
python -m spotexport --search "Linkin Park Numb" --limit 3
```

Без сети и ключей можно показать работу на сохранённых данных:

```bash
python -m spotexport --from-json examples/tracks.json
```

```
title,artists,album,duration,url
Gruppa krovi,Kino,Gruppa krovi,4:44,https://open.spotify.com/track/4iRg9tHDgmRPvv56IC46Pl
V nashikh glazakh,Kino,Gruppa krovi,3:34,https://open.spotify.com/track/4MmfVvY8YPf2eJfoSU6sld
Numb,Linkin Park,Meteora,3:07,https://open.spotify.com/track/2nLtzopw4rPReszdYBJU6h
Numb / Encore,"JAY-Z, Linkin Park",Numb / Encore: MTV Ultimate Mash-Ups Presents Collision Course,3:25,https://open.spotify.com/track/5sNESr6pQfIhL3krM8CtZn
```

```bash
python -m spotexport --from-json examples/tracks.json -f m3u
```

```
#EXTM3U
#EXTINF:284,Kino - Gruppa krovi
https://open.spotify.com/track/4iRg9tHDgmRPvv56IC46Pl
...
```

Весь вывод программы - ASCII. Ядро прогоняет результат любого плагина через
`to_ascii()`: кириллица транслитерируется (`Группа крови` -> `Gruppa krovi`),
у латиницы снимается диакритика (`JAY-Z`), остальное пишется как `\uXXXX`.
JSON хранит исходные названия без потерь (`\uXXXX`-экранирование).

## Проверка типов и тесты

```bash
python -m mypy          # strict, пакет + tests + examples (см. [tool.mypy])
python -m pytest        # 7 тестов, Spotify подменён фейком
```

`spotipy` не поставляет аннотаций типов, поэтому в `pyproject.toml` для него
стоит `ignore_missing_imports`, а форму клиента задаёт наш протокол
`SpotifyApi`. Под него структурно подходит и `spotipy.Spotify`, и фейк из
`tests/test_spotify.py`.

Чтобы увидеть, что реестр сохраняет тип, добавьте в любой файл
`reveal_type(build_registry().get("csv"))` - mypy покажет
`spotexport.protocols.TrackExporter`, а не `Any`. В тестах то же закреплено
через `typing.assert_type`.

## Как добавить свой плагин

1. Напишите класс с атрибутом `description: str` и методом
   `export(self, tracks: Sequence[Track]) -> str`. Наследоваться ни от чего не
   нужно, импортировать протокол тоже:

   ```python
   from collections.abc import Sequence
   from spotexport.models import Track

   class TxtExporter:
       description = "plain list: Artist - Title"

       def export(self, tracks: Sequence[Track]) -> str:
           return "\n".join(f"{', '.join(t.artists)} - {t.title}" for t in tracks)
   ```

2. Зарегистрируйте его во внешней точке сборки - код ядра не меняется:

   ```python
   from spotexport.bootstrap import build_registry
   from spotexport.core import Dispatcher

   registry = build_registry()
   registry.register("txt", TxtExporter())
   print(Dispatcher(registry).export("txt", tracks))
   ```

   Готовый пример: `python -m examples.txt_plugin examples/tracks.json`.
   Чтобы плагин появился в `python -m spotexport -f txt`, добавьте строку
   `registry.register(...)` в `spotexport/bootstrap.py`.

3. Запустите `python -m mypy`. Если класс не подходит под протокол
   (нет метода, другая сигнатура), mypy укажет, какого члена не хватает.

## Маршрут для защиты: Protocol -> реализация -> тест

| Шаг | Где смотреть |
|---|---|
| Контракт | `spotexport/protocols.py` - `TrackExporter` |
| Реализации (3 шт., без наследования) | `spotexport/plugins/*_exporter.py` |
| Ядро знает только протокол | `spotexport/core.py` - `export_with`, `Dispatcher` |
| Точка сборки | `spotexport/bootstrap.py` - `build_registry()` |
| Обобщённый реестр | `spotexport/registry.py` - `Registry(Generic[T])` |
| Модель с валидацией | `spotexport/models.py` - `Track.__post_init__` |
| Тест каждого плагина | `tests/test_exporters.py` (3 теста) |
| Негативные тесты валидации | `tests/test_models.py` |
| Сохранение типа T | `tests/test_registry.py` - `assert_type` |
| Новый плагин без правки ядра | `tests/test_extension.py` |
| Spotify без сети (фейк по протоколу) | `tests/test_spotify.py` |
