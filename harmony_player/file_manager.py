"""Módulo para exploración de archivos, filtrado de formatos de audio y navegación."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

SUPPORTED_AUDIO_EXTENSIONS: Tuple[str, ...] = (".mp3", ".flac", ".wav", ".ogg")
SUPPORTED_VIDEO_EXTENSIONS: Tuple[str, ...] = (".mp4", ".mkv", ".webm", ".avi")
SUPPORTED_MEDIA_EXTENSIONS: Tuple[str, ...] = SUPPORTED_AUDIO_EXTENSIONS + SUPPORTED_VIDEO_EXTENSIONS


@dataclass
class FileItem:
    """Representa un elemento en el explorador de archivos."""

    name: str
    path: Path
    is_dir: bool
    is_video: bool = False
    is_parent: bool = False

    @property
    def display_name(self) -> str:
        """Etiqueta visual del elemento."""
        if self.is_parent:
            return "📁 [..] Directorio superior"
        if self.is_dir:
            return f"📁 {self.name}/"
        if self.is_video:
            return f"🎬 {self.name}"
        return f"🎵 {self.name}"


class FileManager:
    """Manejador del estado de navegación de directorios."""

    def __init__(self, initial_path: str | Path | None = None) -> None:
        if initial_path:
            self._current_path = Path(initial_path).resolve()
            if not self._current_path.is_dir():
                self._current_path = self._current_path.parent
        else:
            self._current_path = Path.cwd().resolve()

    @property
    def current_path(self) -> Path:
        """Ruta del directorio actual."""
        return self._current_path

    @staticmethod
    def is_supported_audio(path: Path) -> bool:
        """Determina si un archivo tiene una extensión de audio compatible."""
        return path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS

    @staticmethod
    def is_supported_video(path: Path) -> bool:
        """Determina si un archivo tiene una extensión de video compatible."""
        return path.is_file() and path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS

    @staticmethod
    def is_supported_media(path: Path) -> bool:
        """Determina si un archivo es audio o video compatible."""
        return path.is_file() and path.suffix.lower() in SUPPORTED_MEDIA_EXTENSIONS

    def list_current_directory(self) -> List[FileItem]:
        """Obtiene la lista ordenada de elementos (carpetas, pistas y videos) en el directorio actual."""
        items: List[FileItem] = []

        # Agregar opción para subir si no estamos en la raíz del sistema de archivos
        if self._current_path.parent != self._current_path:
            items.append(
                FileItem(
                    name="..",
                    path=self._current_path.parent,
                    is_dir=True,
                    is_parent=True,
                )
            )

        try:
            entries = list(self._current_path.iterdir())
        except (PermissionError, OSError):
            return items

        dirs: List[FileItem] = []
        files: List[FileItem] = []

        for entry in entries:
            try:
                # Omitir archivos y carpetas ocultos
                if entry.name.startswith("."):
                    continue

                if entry.is_dir():
                    dirs.append(FileItem(name=entry.name, path=entry, is_dir=True))
                elif self.is_supported_video(entry):
                    files.append(FileItem(name=entry.name, path=entry, is_dir=False, is_video=True))
                elif self.is_supported_audio(entry):
                    files.append(FileItem(name=entry.name, path=entry, is_dir=False, is_video=False))
            except (PermissionError, OSError):
                continue

        # Ordenar alfabéticamente (case-insensitive)
        dirs.sort(key=lambda x: x.name.lower())
        files.sort(key=lambda x: x.name.lower())

        items.extend(dirs)
        items.extend(files)
        return items

    def navigate_to(self, target_path: Path) -> bool:
        """Cambia el directorio actual si la ruta objetivo es un directorio válido."""
        try:
            resolved = target_path.resolve()
            if resolved.is_dir():
                self._current_path = resolved
                return True
        except (PermissionError, OSError):
            return False
        return False

    def navigate_up(self) -> bool:
        """Sube un nivel en el árbol de directorios."""
        if self._current_path.parent != self._current_path:
            return self.navigate_to(self._current_path.parent)
        return False
