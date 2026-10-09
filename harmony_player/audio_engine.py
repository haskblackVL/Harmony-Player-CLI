"""Motor de reproducción de audio basado en pygame.mixer."""

from __future__ import annotations

import os
import time
from enum import Enum
from pathlib import Path
from typing import Optional

# Configurar variables de entorno antes de importar pygame
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame


class PlaybackState(str, Enum):
    """Estados posibles del reproductor."""

    STOPPED = "Detenido"
    PLAYING = "Reproduciendo"
    PAUSED = "Pausado"


class AudioEngine:
    """Controlador del motor de audio y volumen con pygame.mixer."""

    def __init__(self, default_volume: float = 0.70) -> None:
        self._initialized: bool = False
        self._current_track_path: Optional[Path] = None
        self._state: PlaybackState = PlaybackState.STOPPED
        self._volume: float = max(0.0, min(1.0, default_volume))
        self._is_muted: bool = False
        self._volume_before_mute: float = self._volume

        # Seguimiento temporal del progreso
        self._elapsed_offset: float = 0.0
        self._segment_start_time: float = 0.0

        self._init_mixer()

    def _init_mixer(self) -> None:
        """Inicializa pygame y el subsistema de audio mixer."""
        if not self._initialized:
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
                self._initialized = True
                self.set_volume(self._volume)
            except Exception as exc:
                self._initialized = False

    @property
    def state(self) -> PlaybackState:
        """Obtiene el estado actual, verificando si la canción terminó."""
        if self._state == PlaybackState.PLAYING:
            # Si estaba sonando pero pygame ya no está ocupado, la pista finalizó
            if not pygame.mixer.music.get_busy():
                self._state = PlaybackState.STOPPED
                self._elapsed_offset = 0.0
        return self._state

    @property
    def current_track_path(self) -> Optional[Path]:
        """Ruta de la pista actual."""
        return self._current_track_path

    @property
    def volume(self) -> float:
        """Nivel actual de volumen entre 0.0 y 1.0."""
        return self._volume

    @property
    def is_muted(self) -> bool:
        """Indica si el audio está silenciado."""
        return self._is_muted

    def load_and_play(self, file_path: str | Path) -> bool:
        """Carga y reproduce inmediatamente una pista de audio."""
        if not self._initialized:
            self._init_mixer()
            if not self._initialized:
                return False

        path = Path(file_path).resolve()
        if not path.is_file():
            return False

        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.play()

            self._current_track_path = path
            self._state = PlaybackState.PLAYING
            self._elapsed_offset = 0.0
            self._segment_start_time = time.monotonic()
            return True
        except Exception:
            self._state = PlaybackState.STOPPED
            self._current_track_path = None
            return False

    def pause(self) -> None:
        """Pausa la reproducción en curso."""
        if self.state == PlaybackState.PLAYING:
            pygame.mixer.music.pause()
            self._elapsed_offset += time.monotonic() - self._segment_start_time
            self._state = PlaybackState.PAUSED

    def unpause(self) -> None:
        """Reanuda la reproducción pausada."""
        if self.state == PlaybackState.PAUSED:
            pygame.mixer.music.unpause()
            self._segment_start_time = time.monotonic()
            self._state = PlaybackState.PLAYING

    def toggle_pause(self) -> PlaybackState:
        """Alterna entre reproducción y pausa."""
        cur = self.state
        if cur == PlaybackState.PLAYING:
            self.pause()
        elif cur == PlaybackState.PAUSED:
            self.unpause()
        return self.state

    def stop(self) -> None:
        """Detiene completamente la reproducción."""
        if self._initialized:
            pygame.mixer.music.stop()
        self._state = PlaybackState.STOPPED
        self._elapsed_offset = 0.0

    def set_volume(self, value: float) -> None:
        """Ajusta el volumen en el rango 0.0 a 1.0."""
        self._volume = max(0.0, min(1.0, value))
        if self._is_muted:
            self._is_muted = False
        if self._initialized:
            pygame.mixer.music.set_volume(self._volume)

    def volume_up(self, step: float = 0.05) -> float:
        """Incrementa el volumen."""
        self.set_volume(self._volume + step)
        return self._volume

    def volume_down(self, step: float = 0.05) -> float:
        """Reduce el volumen."""
        self.set_volume(self._volume - step)
        return self._volume

    def toggle_mute(self) -> bool:
        """Alterna el silencio de audio."""
        if not self._initialized:
            return False

        if self._is_muted:
            self._is_muted = False
            self.set_volume(self._volume_before_mute if self._volume_before_mute > 0 else 0.5)
        else:
            self._volume_before_mute = self._volume
            self._is_muted = True
            pygame.mixer.music.set_volume(0.0)

        return self._is_muted

    def get_elapsed_seconds(self) -> float:
        """Calcula el tiempo transcurrido en segundos."""
        if self.state == PlaybackState.STOPPED:
            return 0.0
        if self.state == PlaybackState.PAUSED:
            return max(0.0, self._elapsed_offset)
        # PLAYING
        return max(0.0, self._elapsed_offset + (time.monotonic() - self._segment_start_time))

    def shutdown(self) -> None:
        """Cierra de forma limpia el motor de audio."""
        if self._initialized:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
            except Exception:
                pass
            self._initialized = False
        self._state = PlaybackState.STOPPED
