"""Módulo para la extracción y formato de metadatos de audio utilizando Mutagen."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import mutagen


@dataclass
class TrackMetadata:
    """Contenedor de metadatos de una pista de audio."""

    path: str
    filename: str
    title: str
    artist: str
    album: str
    duration_seconds: float

    @property
    def duration_formatted(self) -> str:
        """Devuelve la duración formateada en MM:SS o HH:MM:SS."""
        return format_duration(self.duration_seconds)


def format_duration(seconds: float) -> str:
    """Formatea una cantidad de segundos a formato MM:SS o HH:MM:SS."""
    if seconds < 0:
        return "00:00"

    total_secs = int(round(seconds))
    hours = total_secs // 3600
    minutes = (total_secs % 3600) // 60
    secs = total_secs % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def extract_metadata(file_path: str | Path) -> TrackMetadata:
    """Extrae metadatos y duración de un archivo de audio.

    Args:
        file_path: Ruta al archivo de audio.

    Returns:
        TrackMetadata con la información encontrada o valores por defecto.
    """
    path_obj = Path(file_path).resolve()
    filename = path_obj.name
    fallback_title = path_obj.stem

    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    duration: float = 0.0

    if not path_obj.exists() or not path_obj.is_file():
        return TrackMetadata(
            path=str(path_obj),
            filename=filename,
            title=fallback_title,
            artist="Desconocido",
            album="Desconocido",
            duration_seconds=0.0,
        )

    try:
        audio = mutagen.File(str(path_obj), easy=True)
        if audio is not None:
            if audio.tags:
                title = _first_tag_value(audio.tags.get("title"))
                artist = _first_tag_value(audio.tags.get("artist"))
                album = _first_tag_value(audio.tags.get("album"))

            if audio.info and hasattr(audio.info, "length"):
                duration = float(audio.info.length)
        else:
            # Intento alternativo sin easy=True si fallara
            raw_audio = mutagen.File(str(path_obj))
            if raw_audio is not None and raw_audio.info and hasattr(raw_audio.info, "length"):
                duration = float(raw_audio.info.length)
    except Exception:
        # En caso de error o archivo no soportado/corrupto, mantener fallbacks
        pass

    return TrackMetadata(
        path=str(path_obj),
        filename=filename,
        title=title.strip() if title else fallback_title,
        artist=artist.strip() if artist else "Artista Desconocido",
        album=album.strip() if album else "Álbum Desconocido",
        duration_seconds=duration,
    )


def _first_tag_value(val: object) -> Optional[str]:
    """Obtiene el primer valor como string de una etiqueta de mutagen."""
    if not val:
        return None
    if isinstance(val, (list, tuple)) and len(val) > 0:
        return str(val[0])
    return str(val)
