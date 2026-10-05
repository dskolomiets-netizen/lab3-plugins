"""Плагин: плейлист M3U со ссылками на треки."""

from collections.abc import Sequence

from spotexport.models import Track


class M3uExporter:
    description = "extended M3U playlist with open.spotify.com links"

    def export(self, tracks: Sequence[Track]) -> str:
        lines = ["#EXTM3U"]
        for t in tracks:
            lines.append(f"#EXTINF:{t.duration_ms // 1000},{', '.join(t.artists)} - {t.title}")
            lines.append(t.url)
        return "\n".join(lines)
