import pytest

from spotexport.models import Track


@pytest.fixture
def tracks() -> list[Track]:
    return [
        # Кино - Группа крови: название и альбом кириллицей
        Track(
            id="4iRg9tHDgmRPvv56IC46Pl",
            title="\u0413\u0440\u0443\u043f\u043f\u0430 \u043a\u0440\u043e\u0432\u0438",
            artists=("Kino",),
            album="\u0413\u0440\u0443\u043f\u043f\u0430 \u043a\u0440\u043e\u0432\u0438",
            duration_ms=284002,
        ),
        # JAŸ-Z с диакритикой, два исполнителя
        Track(
            id="5sNESr6pQfIhL3krM8CtZn",
            title="Numb / Encore",
            artists=("JA\u0178-Z", "Linkin Park"),
            album="Collision Course",
            duration_ms=205733,
            explicit=True,
        ),
    ]
