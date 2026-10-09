"""Punto de entrada principal para ejecutar Harmony-Player CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from harmony_player.ui.app import HarmonyPlayerApp


def parse_args() -> argparse.Namespace:
    """Parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        prog="harmony-player",
        description="Reproductor de música interactivo TUI para Linux.",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directorio inicial para explorar música (por defecto: actual)",
    )
    return parser.parse_args()


def main() -> None:
    """Función de arranque de la aplicación."""
    args = parse_args()
    initial_dir = Path(args.directory).resolve()

    if not initial_dir.exists() or not initial_dir.is_dir():
        print(f"Error: La ruta especificada no existe o no es un directorio: {initial_dir}", file=sys.stderr)
        sys.exit(1)

    app = HarmonyPlayerApp(initial_directory=initial_dir)
    try:
        app.run()
    except KeyboardInterrupt:
        # Salida limpia al pulsar Ctrl+C
        if hasattr(app, "audio_engine"):
            app.audio_engine.shutdown()
        sys.exit(0)


if __name__ == "__main__":
    main()
