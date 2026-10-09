"""Aplicación principal Textual para Harmony-Player CLI."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Label, OptionList
from textual.widgets.option_list import Option

from harmony_player.audio_engine import AudioEngine, PlaybackState
from harmony_player.file_manager import FileItem, FileManager
from harmony_player.metadata import TrackMetadata, extract_metadata
from harmony_player.ui.widgets import MetadataCard, PlayerControlCard, VisualizerCard
from harmony_player.video_engine import VideoPlayer


class HarmonyPlayerApp(App[None]):
    """Aplicación TUI de reproducción de música Harmony-Player."""

    CSS_PATH = "styles.tcss"
    TITLE = "Harmony-Player CLI"

    BINDINGS = [
        Binding("space", "toggle_play", "Play/Pausa", priority=True),
        Binding("s", "stop_play", "Detener", priority=True),
        Binding("v", "cycle_visualizer", "Gráfica", priority=True),
        Binding("+", "volume_up", "Vol +5%", priority=True),
        Binding("=", "volume_up", "Vol +5%", show=False, priority=True),
        Binding("-", "volume_down", "Vol -5%", priority=True),
        Binding("m", "toggle_mute", "Mute", priority=True),
        Binding("h", "navigate_parent", "Carpeta anterior", priority=True),
        Binding("backspace", "navigate_parent", "Carpeta anterior", show=False, priority=True),
        Binding("k", "nav_up", "Subir", show=False, priority=True),
        Binding("j", "nav_down", "Bajar", show=False, priority=True),
        Binding("q", "quit_clean", "Salir", priority=True),
    ]

    def __init__(self, initial_directory: Optional[Path | str] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.file_manager = FileManager(initial_directory)
        self.audio_engine = AudioEngine()
        self.current_metadata: Optional[TrackMetadata] = None
        self._current_items: List[FileItem] = []

    def compose(self) -> ComposeResult:
        with Container(id="header-container"):
            yield Label("🎵 HARMONY-PLAYER CLI — Reproductor de Audio TUI", id="header-title")

        yield Label(f"📂 Ruta: {self.file_manager.current_path}", id="path-bar")

        with Horizontal(id="main-content"):
            with Vertical(id="browser-container"):
                yield Label("Explorador de Archivos (Vim: j/k, Enter: abrir/reproducir, h: subir)", id="browser-title")
                yield OptionList(id="file-list")

            with Vertical(id="panel-right"):
                yield MetadataCard()
                yield VisualizerCard()
                yield PlayerControlCard()

        yield Footer()

    def on_mount(self) -> None:
        """Inicializa la lista de archivos, estado inicial y temporizador de progreso."""
        self._refresh_file_list()
        file_list = self.query_one("#file-list", OptionList)
        file_list.focus()

        control_card = self.query_one(PlayerControlCard)
        control_card.update_status(self.audio_engine.state)
        control_card.update_volume(self.audio_engine.volume, self.audio_engine.is_muted)
        control_card.update_progress(0.0, 0.0)

        # Timer periódico para actualizar la barra de progreso y gráfica de audio (~12 FPS)
        self.set_interval(0.08, self._tick_playback)

    def _refresh_file_list(self) -> None:
        """Recarga la lista de elementos del explorador en base al directorio actual."""
        file_list = self.query_one("#file-list", OptionList)
        path_label = self.query_one("#path-bar", Label)

        self._current_items = self.file_manager.list_current_directory()
        path_label.update(Text(f"📂 Ruta: {self.file_manager.current_path}"))

        file_list.clear_options()

        if not self._current_items:
            file_list.add_option(Option(Text("  (Carpeta vacía o sin archivos compatibles)"), disabled=True))
            return

        for idx, item in enumerate(self._current_items):
            file_list.add_option(Option(Text(f" {item.display_name}"), id=str(idx)))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Maneja la selección al pulsar Enter sobre una carpeta, audio o video."""
        idx = event.option_index
        if idx is None or idx < 0 or idx >= len(self._current_items):
            return

        selected_item = self._current_items[idx]

        if selected_item.is_dir:
            # Navegar hacia la carpeta seleccionada
            if self.file_manager.navigate_to(selected_item.path):
                self._refresh_file_list()
        elif selected_item.is_video:
            # Reproducir video suspendiendo temporalmente la TUI
            self._play_video(selected_item.path)
        else:
            # Reproducir la pista de audio seleccionada
            self._play_track(selected_item.path)

    def _play_video(self, video_path: Path) -> None:
        """Reproduce un video en modo terminal suspendiendo temporalmente la TUI."""
        # Detener audio previo
        self.audio_engine.stop()
        control_card = self.query_one(PlayerControlCard)
        control_card.update_status(PlaybackState.STOPPED)

        with self.suspend():
            player = VideoPlayer(self.audio_engine)
            player.play(video_path)

        # Al volver a la TUI, actualizar lista y estado
        self._refresh_file_list()
        control_card.update_status(PlaybackState.STOPPED)

    def _play_track(self, track_path: Path) -> None:
        """Extrae metadatos y reproduce el archivo indicado."""
        self.current_metadata = extract_metadata(track_path)
        meta_card = self.query_one(MetadataCard)
        meta_card.update_metadata(self.current_metadata)

        success = self.audio_engine.load_and_play(track_path)
        control_card = self.query_one(PlayerControlCard)

        if success:
            control_card.update_status(self.audio_engine.state)
            control_card.update_progress(0.0, self.current_metadata.duration_seconds)
        else:
            control_card.update_status(PlaybackState.STOPPED)

    def _tick_playback(self) -> None:
        """Tick periódico para actualizar barra de tiempo, estado y gráfica de audio."""
        state = self.audio_engine.state
        control_card = self.query_one(PlayerControlCard)
        control_card.update_status(state)

        total_duration = self.current_metadata.duration_seconds if self.current_metadata else 0.0
        elapsed = self.audio_engine.get_elapsed_seconds()

        control_card.update_progress(elapsed, total_duration)

        # Actualizar gráfica de sonido
        visualizer = self.query_one(VisualizerCard)
        visualizer.update_audio(state, self.audio_engine.volume, self.audio_engine.is_muted, elapsed)

    # --- Acciones de bindings ---

    def action_cycle_visualizer(self) -> None:
        """Alterna el modo de visualización gráfica (espectro, osciloscopio, vúmetro)."""
        mode_name = self.query_one(VisualizerCard).cycle_mode()
        self.notify(f"Gráfica: {mode_name}", timeout=1.5)

    def action_toggle_play(self) -> None:
        """Pausa o reanuda la pista actual."""
        self.audio_engine.toggle_pause()
        control_card = self.query_one(PlayerControlCard)
        control_card.update_status(self.audio_engine.state)

    def action_stop_play(self) -> None:
        """Detiene la reproducción."""
        self.audio_engine.stop()
        control_card = self.query_one(PlayerControlCard)
        control_card.update_status(PlaybackState.STOPPED)
        control_card.update_progress(0.0, self.current_metadata.duration_seconds if self.current_metadata else 0.0)

    def action_volume_up(self) -> None:
        """Sube el volumen en +5%."""
        vol = self.audio_engine.volume_up(0.05)
        self.query_one(PlayerControlCard).update_volume(vol, self.audio_engine.is_muted)

    def action_volume_down(self) -> None:
        """Baja el volumen en -5%."""
        vol = self.audio_engine.volume_down(0.05)
        self.query_one(PlayerControlCard).update_volume(vol, self.audio_engine.is_muted)

    def action_toggle_mute(self) -> None:
        """Alterna el silencio de audio."""
        self.audio_engine.toggle_mute()
        self.query_one(PlayerControlCard).update_volume(
            self.audio_engine.volume, self.audio_engine.is_muted
        )

    def action_navigate_parent(self) -> None:
        """Sube al directorio superior."""
        if self.file_manager.navigate_up():
            self._refresh_file_list()

    def action_nav_up(self) -> None:
        """Navega hacia arriba en el listado (tecla k)."""
        file_list = self.query_one("#file-list", OptionList)
        file_list.action_cursor_up()

    def action_nav_down(self) -> None:
        """Navega hacia abajo en el listado (tecla j)."""
        file_list = self.query_one("#file-list", OptionList)
        file_list.action_cursor_down()

    def action_quit_clean(self) -> None:
        """Cierra el motor de audio y finaliza la app limpiamente."""
        self.audio_engine.shutdown()
        self.exit()
