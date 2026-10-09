"""Módulo de reproducción de video en terminal con renderizado Half-Block y A/V Sync."""

from __future__ import annotations

import os
import select
import shutil
import sys
import tempfile
import termios
import time
import tty
from pathlib import Path
from typing import Optional, Tuple

import av
import cv2
import numpy as np

from harmony_player.audio_engine import AudioEngine, PlaybackState
from harmony_player.metadata import format_duration

ASCII_RAMP = "@%#*+=-:. "


def extract_audio_track(video_path: Path, output_wav_path: Path) -> bool:
    """Extrae la pista de audio de un archivo de video a formato WAV estéreo PCM."""
    try:
        input_container = av.open(str(video_path))
        if not input_container.streams.audio:
            input_container.close()
            return False

        in_stream = input_container.streams.audio[0]
        output_container = av.open(str(output_wav_path), mode="w", format="wav")
        out_stream = output_container.add_stream("pcm_s16le", rate=44100, layout="stereo")

        for packet in input_container.demux(in_stream):
            for frame in packet.decode():
                for out_packet in out_stream.encode(frame):
                    output_container.mux(out_packet)

        for out_packet in out_stream.encode():
            output_container.mux(out_packet)

        output_container.close()
        input_container.close()
        return True
    except Exception:
        return False


def frame_to_halfblock_ansi(frame_rgb: np.ndarray, left_padding: int = 0) -> str:
    """Convierte una matriz RGB a caracteres Unicode Half-Block con colores TrueColor de 24 bits."""
    h, w, _ = frame_rgb.shape
    # Asegurar número par de filas
    if h % 2 != 0:
        frame_rgb = frame_rgb[: h - 1, :]
        h -= 1

    top = frame_rgb[0::2, :]
    bot = frame_rgb[1::2, :]
    rows, cols, _ = top.shape

    pad = " " * left_padding
    lines = []

    for r in range(rows):
        line = [pad]
        prev_fg = None
        prev_bg = None

        for c in range(cols):
            fg = (int(top[r, c, 0]), int(top[r, c, 1]), int(top[r, c, 2]))
            bg = (int(bot[r, c, 0]), int(bot[r, c, 1]), int(bot[r, c, 2]))

            if fg != prev_fg:
                line.append(f"\033[38;2;{fg[0]};{fg[1]};{fg[2]}m")
                prev_fg = fg
            if bg != prev_bg:
                line.append(f"\033[48;2;{bg[0]};{bg[1]};{bg[2]}m")
                prev_bg = bg

            line.append("▀")

        line.append("\033[0m")
        lines.append("".join(line))

    return "\n".join(lines)


def frame_to_ascii_grayscale(frame_rgb: np.ndarray, left_padding: int = 0) -> str:
    """Modo fallback monocromático usando rampa ASCII estándar."""
    gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    pad = " " * left_padding
    ramp_len = len(ASCII_RAMP)

    lines = []
    for r in range(h):
        row_chars = [pad]
        for c in range(w):
            val = gray[r, c]
            idx = int((val / 255.0) * (ramp_len - 1))
            row_chars.append(ASCII_RAMP[idx])
        lines.append("".join(row_chars))

    return "\n".join(lines)


class VideoPlayer:
    """Reproductor de video interactivo con soporte de cursor ANSI y A/V Sync."""

    def __init__(self, audio_engine: AudioEngine) -> None:
        self.audio_engine = audio_engine

    def play(self, video_path: Path, use_ascii_fallback: bool = False) -> None:
        """Inicia la reproducción de video en la terminal."""
        path = Path(video_path).resolve()
        if not path.is_file():
            return

        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            return

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or np.isnan(fps):
            fps = 30.0

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_secs = total_frames / fps if fps > 0 else 0.0

        # 1. Preparar audio
        temp_audio_file: Optional[Path] = None
        has_audio = False

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                temp_audio_file = Path(tmp.name)

            if extract_audio_track(path, temp_audio_file):
                has_audio = self.audio_engine.load_and_play(temp_audio_file)
            else:
                has_audio = False
        except Exception:
            has_audio = False

        # Configuración de terminal para lectura no bloqueante de teclado
        fd = sys.stdin.fileno()
        old_term_settings = None
        if os.isatty(fd):
            old_term_settings = termios.tcgetattr(fd)
            tty.setcbreak(fd)

        # Ocultar cursor y limpiar pantalla
        sys.stdout.write("\033[?25l\033[2J\033[H")
        sys.stdout.flush()

        # Reloj alternativo si no hay audio
        start_time = time.monotonic()
        paused_offset = 0.0
        pause_start = 0.0
        is_paused = False
        keep_aspect_ratio = True

        current_frame_idx = 0

        try:
            while cap.isOpened():
                # Procesar teclas de control (no bloqueante)
                if os.isatty(fd):
                    rlist, _, _ = select.select([sys.stdin], [], [], 0)
                    if rlist:
                        ch = sys.stdin.read(1)
                        if ch == " ":
                            is_paused = not is_paused
                            if has_audio:
                                self.audio_engine.toggle_pause()
                            if is_paused:
                                pause_start = time.monotonic()
                            else:
                                paused_offset += time.monotonic() - pause_start
                        elif ch in ("q", "\x1b"):  # q o ESC
                            break
                        elif ch == "m":
                            self.audio_engine.toggle_mute()
                        elif ch == "f":
                            keep_aspect_ratio = not keep_aspect_ratio

                if is_paused:
                    time.sleep(0.04)
                    continue

                # Calcular tiempo transcurrido (Master Clock)
                if has_audio:
                    elapsed = self.audio_engine.get_elapsed_seconds()
                else:
                    elapsed = (time.monotonic() - start_time) - paused_offset

                target_frame = int(elapsed * fps)

                if target_frame >= total_frames and total_frames > 0:
                    break

                # Compensación de reloj y descarte de fotogramas (Frame Dropping)
                if target_frame > current_frame_idx + 1:
                    while current_frame_idx < target_frame - 1:
                        cap.grab()
                        current_frame_idx += 1

                ret, frame_bgr = cap.read()
                if not ret:
                    break
                current_frame_idx += 1

                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                orig_h, orig_w, _ = frame_rgb.shape

                # Obtener dimensiones de terminal
                term_cols, term_lines = shutil.get_terminal_size((80, 24))
                # Reservar 2 líneas inferiores para la barra de estado y controles
                avail_lines = max(6, term_lines - 2)

                if use_ascii_fallback:
                    target_w = term_cols
                    target_h = avail_lines
                    left_pad = 0
                else:
                    pixel_avail_h = avail_lines * 2
                    if keep_aspect_ratio:
                        # Aspect ratio teniendo en cuenta pixel cuadrado de Half-Block
                        aspect = orig_w / max(1, orig_h)
                        # Calcular dimensiones manteniendo proporción
                        target_w = min(term_cols, int(pixel_avail_h * aspect))
                        target_h = min(pixel_avail_h, int(target_w / aspect))
                        target_h = max(2, (target_h // 2) * 2)  # Forzar número par
                        left_pad = max(0, (term_cols - target_w) // 2)
                    else:
                        target_w = term_cols
                        target_h = max(2, (pixel_avail_h // 2) * 2)
                        left_pad = 0

                # Redimensionar fotograma
                resized = cv2.resize(
                    frame_rgb, (target_w, target_h), interpolation=cv2.INTER_LINEAR
                )

                # Renderizar a cadena ANSI
                if use_ascii_fallback:
                    rendered_screen = frame_to_ascii_grayscale(resized, left_padding=left_pad)
                else:
                    rendered_screen = frame_to_halfblock_ansi(resized, left_padding=left_pad)

                # Barra de estado inferior
                elapsed_str = format_duration(elapsed)
                total_str = format_duration(duration_secs)
                pct = int((elapsed / duration_secs) * 100) if duration_secs > 0 else 0
                vol_pct = int(self.audio_engine.volume * 100)
                mute_str = "[MUTED]" if self.audio_engine.is_muted else f"{vol_pct}%"
                status_str = "⏸ PAUSADO" if is_paused else "▶ REPRODUCIENDO"
                mode_str = "Ajustado" if keep_aspect_ratio else "Estirado"

                status_line = (
                    f" \033[1;36m{status_str}\033[0m | "
                    f"[{elapsed_str} / {total_str}] ({pct}%) | "
                    f"Vol: {mute_str} | Modo: {mode_str} | "
                    f"\033[90m[Espacio: Pausa | q: Salir | m: Mute | f: Aspecto]\033[0m"
                )

                # Dibujar al inicio del búfer sin parpadeo (Double buffering ANSI)
                sys.stdout.write(f"\033[H{rendered_screen}\n\033[K{status_line}\033[K")
                sys.stdout.flush()

                # Control fino de framerate si vamos adelantados
                next_frame_time = (current_frame_idx + 1) / fps
                sleep_time = next_frame_time - elapsed
                if sleep_time > 0.005:
                    time.sleep(sleep_time)

        finally:
            cap.release()
            self.audio_engine.stop()

            # Restaurar terminal
            if old_term_settings and os.isatty(fd):
                termios.tcsetattr(fd, termios.TCSADRAIN, old_term_settings)

            sys.stdout.write("\033[0m\033[?25h\033[2J\033[H")
            sys.stdout.flush()

            # Eliminar archivo temporal de audio
            if temp_audio_file and temp_audio_file.exists():
                try:
                    temp_audio_file.unlink()
                except OSError:
                    pass
