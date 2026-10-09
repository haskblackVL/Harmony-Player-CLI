"""Widgets personalizados para la interfaz de Textual de Harmony-Player."""

from __future__ import annotations

from typing import Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Label, OptionList, ProgressBar, Static

from harmony_player.audio_engine import PlaybackState
from harmony_player.metadata import TrackMetadata, format_duration


class MetadataCard(Container):
    """Tarjeta informativa con los metadatos de la pista actual."""

    DEFAULT_CSS = """
    MetadataCard {
        height: auto;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(id="metadata-card", **kwargs)
        self._title_label = Label("---", classes="meta-value", id="track-title")
        self._artist_label = Label("---", classes="meta-value", id="track-artist")
        self._album_label = Label("---", classes="meta-value", id="track-album")

    def compose(self) -> ComposeResult:
        yield Label("🎵 PISTA ACTUAL", classes="meta-label")
        yield self._title_label
        yield Label("👤 ARTISTA", classes="meta-label")
        yield self._artist_label
        yield Label("💿 ÁLBUM", classes="meta-label")
        yield self._album_label

    def update_metadata(self, meta: Optional[TrackMetadata]) -> None:
        """Actualiza los valores de metadatos mostrados."""
        if not self.is_mounted:
            return
        if meta:
            self._title_label.update(Text(meta.title))
            self._artist_label.update(Text(meta.artist))
            self._album_label.update(Text(meta.album))
        else:
            self._title_label.update(Text("Sin reproducción activa"))
            self._artist_label.update(Text("---"))
            self._album_label.update(Text("---"))


class PlayerControlCard(Container):
    """Panel con barra de progreso, estado de reproducción y volumen."""

    DEFAULT_CSS = """
    PlayerControlCard {
        height: auto;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(id="player-controls-card", **kwargs)
        self._status_label = Label("[Detenido]", id="status-indicator")
        self._progress_bar = ProgressBar(total=100, show_eta=False, id="progress-bar")
        self._time_label = Label("[00:00 / 00:00]", id="time-label")
        self._volume_label = Label("🔊 Vol: 70%", id="volume-indicator")

    def compose(self) -> ComposeResult:
        yield self._status_label
        yield self._progress_bar
        yield self._time_label
        yield self._volume_label

    def update_status(self, state: PlaybackState) -> None:
        """Actualiza el indicador visual de estado."""
        if not self.is_mounted:
            return
        if state == PlaybackState.PLAYING:
            text = Text("▶ [Reproduciendo]", style="bold green")
        elif state == PlaybackState.PAUSED:
            text = Text("⏸ [Pausado]", style="bold yellow")
        else:
            text = Text("⏹ [Detenido]", style="bold bright_black")
        self._status_label.update(text)

    def update_progress(self, elapsed: float, total: float) -> None:
        """Actualiza el tiempo y el porcentaje de la barra de progreso."""
        if not self.is_mounted:
            return
        elapsed_str = format_duration(elapsed)
        total_str = format_duration(total)
        self._time_label.update(f"[{elapsed_str} / {total_str}]")

        if total > 0:
            percentage = min(100.0, max(0.0, (elapsed / total) * 100))
            self._progress_bar.update(total=100, progress=percentage)
        else:
            self._progress_bar.update(total=100, progress=0)

    def update_volume(self, volume: float, is_muted: bool) -> None:
        """Actualiza el nivel de volumen mostrado."""
        if not self.is_mounted:
            return
        if is_muted:
            self._volume_label.update(Text("🔇 [MUTED]", style="bold red"))
        else:
            pct = int(round(volume * 100))
            self._volume_label.update(Text(f"🔊 Vol: {pct}%", style="bold cyan"))


class VisualizerCard(Container):
    """Tarjeta con visualización gráfica de sonido interactiva."""

    DEFAULT_CSS = """
    VisualizerCard {
        height: auto;
    }
    """

    MODES = ("Espectro (Bares)", "Osciloscopio", "Vúmetro Estéreo")
    ROW_COLORS = ("#3b82f6", "#06b6d4", "#10b981", "#eab308", "#f97316", "#ef4444")
    BLOCK_CHARS = (" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█")

    def __init__(self, num_bars: int = 18, max_height: int = 6, **kwargs) -> None:
        super().__init__(id="visualizer-card", **kwargs)
        self.num_bars = num_bars
        self.max_height = max_height
        self._mode_idx = 0

        # Estado físico para simulación del espectro
        self._levels = [0.0] * self.num_bars
        self._peaks = [0.0] * self.num_bars

        # Niveles para vúmetro
        self._vu_l = 0.0
        self._vu_r = 0.0

        self._title_label = Label("🎚️ GRÁFICA DE AUDIO", id="visualizer-title")
        self._mode_badge = Label(f"[{self.MODES[self._mode_idx]}]", id="visualizer-mode-badge")
        self._canvas = Static("", id="visualizer-canvas")
        self._legend = Label(" 32Hz  125Hz  500Hz  2kHz  8kHz  16k", classes="freq-legend")

    def compose(self) -> ComposeResult:
        with Container(id="visualizer-header"):
            yield self._title_label
            yield self._mode_badge
        yield self._canvas
        yield self._legend

    def cycle_mode(self) -> str:
        """Avanza al siguiente modo de visualización."""
        self._mode_idx = (self._mode_idx + 1) % len(self.MODES)
        current_name = self.MODES[self._mode_idx]
        if self.is_mounted:
            self._mode_badge.update(f"[{current_name}]")
            if self._mode_idx == 0:
                self._legend.update(" 32Hz  125Hz  500Hz  2kHz  8kHz  16k")
            elif self._mode_idx == 1:
                self._legend.update(" - - - - - [FORMA DE ONDA] - - - - -")
            else:
                self._legend.update(" -24dB   -18dB   -12dB   -6dB   0dB")
        return current_name

    def update_audio(
        self, state: PlaybackState, volume: float, is_muted: bool, elapsed: float
    ) -> None:
        """Actualiza la gráfica de audio según el estado de reproducción."""
        if not self.is_mounted:
            return
        import math

        active = (state == PlaybackState.PLAYING) and (not is_muted) and (volume > 0.0)
        vol_factor = volume if active else 0.0

        # 1. Modo Espectro por bandas
        if self._mode_idx == 0:
            for i in range(self.num_bars):
                if active:
                    if i < 4:
                        # Rango de graves (bajos pulsantes)
                        pulse = (math.sin(elapsed * 6.5) ** 4) * 4.2
                        raw = pulse + (math.sin(elapsed * 2.2 + i * 0.9) + 1.0) * 0.9
                    elif i < 11:
                        # Rango medio (ritmo melódico)
                        raw = (math.sin(elapsed * 4.2 + i * 0.8) + 1.0) * 2.3
                    else:
                        # Rango agudo (armónicos rápidos)
                        raw = (math.sin(elapsed * 8.5 + i * 1.4) + 1.0) * 1.9

                    target = min(float(self.max_height), max(0.0, raw * vol_factor))
                    self._levels[i] = self._levels[i] * 0.35 + target * 0.65
                else:
                    decay = 0.85 if state == PlaybackState.PAUSED else 0.65
                    self._levels[i] = max(0.0, self._levels[i] * decay)

                # Física de picos (peak hold & gravity decay)
                if self._levels[i] >= self._peaks[i]:
                    self._peaks[i] = self._levels[i]
                else:
                    self._peaks[i] = max(0.0, self._peaks[i] - 0.22)

            self._render_spectrum()

        # 2. Modo Osciloscopio
        elif self._mode_idx == 1:
            self._render_oscilloscope(active, elapsed, vol_factor)

        # 3. Modo Vúmetro Estéreo
        else:
            if active:
                target_l = min(1.0, max(0.0, (math.sin(elapsed * 5.0) ** 2 * 0.7 + 0.2) * vol_factor))
                target_r = min(1.0, max(0.0, (math.cos(elapsed * 5.3) ** 2 * 0.75 + 0.18) * vol_factor))
                self._vu_l = self._vu_l * 0.4 + target_l * 0.6
                self._vu_r = self._vu_r * 0.4 + target_r * 0.6
            else:
                self._vu_l = max(0.0, self._vu_l * 0.7)
                self._vu_r = max(0.0, self._vu_r * 0.7)
            self._render_vu()

    def _render_spectrum(self) -> None:
        """Renderiza las barras de espectro vertical."""
        lines = []
        for r in reversed(range(self.max_height)):
            line = Text()
            for i in range(self.num_bars):
                val = self._levels[i]
                peak = self._peaks[i]
                if val >= r + 1:
                    line.append("█ ", style=self.ROW_COLORS[r])
                elif val > r:
                    frac = val - r
                    idx = min(8, max(0, int(frac * 8)))
                    line.append(f"{self.BLOCK_CHARS[idx]} ", style=self.ROW_COLORS[r])
                elif int(peak) == r and peak > 0.4:
                    line.append("▔ ", style="bold #f8fafc")
                else:
                    line.append("  ")
            lines.append(line)
        self._canvas.update(Text("\n").join(lines))

    def _render_oscilloscope(self, active: bool, elapsed: float, vol: float) -> None:
        """Renderiza una forma de onda simulada."""
        import math

        cols = self.num_bars * 2
        mid = (self.max_height - 1) / 2.0
        grid = [[" " for _ in range(cols)] for _ in range(self.max_height)]

        if active:
            for x in range(cols):
                freq1 = math.sin((x * 0.4) + elapsed * 8.0)
                freq2 = math.sin((x * 0.8) - elapsed * 5.0) * 0.5
                wave = (freq1 + freq2) * (vol * (mid - 0.2))
                y = int(round(mid + wave))
                y = min(self.max_height - 1, max(0, y))
                grid[y][x] = "━"
        else:
            for x in range(cols):
                grid[int(mid)][x] = "─"

        lines = []
        for r in reversed(range(self.max_height)):
            line = Text("".join(grid[r]), style=self.ROW_COLORS[r])
            lines.append(line)
        self._canvas.update(Text("\n").join(lines))

    def _render_vu(self) -> None:
        """Renderiza los vúmetros de canales estéreo."""
        width = 24
        colors = ["#10b981"] * 14 + ["#eab308"] * 6 + ["#ef4444"] * 4

        lines = [Text(""), Text("")]  # Espacio superior para centrar
        for label, lvl in (("L", self._vu_l), ("R", self._vu_r)):
            t = Text(f" Canal {label} [")
            num_lit = min(width, int(round(lvl * width)))
            for i in range(width):
                if i < num_lit:
                    t.append("█", style=colors[i])
                else:
                    t.append("░", style="#334155")
            t.append("] ")
            db = int((lvl - 1.0) * 24)
            db_str = f"{db:+3d} dB" if lvl > 0.05 else "-inf dB"
            t.append(db_str, style="bold #f8fafc")
            lines.append(t)
        lines.append(Text(""))
        lines.append(Text(""))
        self._canvas.update(Text("\n").join(lines))
