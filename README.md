# Harmony-Player CLI 🎵

Un reproductor de música interactivo para la terminal (TUI) diseñado para sistemas Debian/Linux, desarrollado con **Python**, **Textual**, **Pygame** y **Mutagen**.

---

## ✨ Características

- 📁 **Explorador de Archivos:** Navegación por carpetas con filtrado de audio (`.mp3`, `.flac`, `.wav`, `.ogg`) y video (`.mp4`, `.mkv`, `.webm`, `.avi`).
- 🎬 **Reproducción de Video en Terminal:** Decodificación fluida con OpenCV y renderizado de alta densidad en colores TrueColor de 24 bits usando medios bloques Unicode (`▀`), con sincronización A/V estricta y compensación de retraso (*frame dropping*).
- 🧭 **Atajos estilo Vim:** Movimiento ágil con `j`, `k`, `h` o flechas de dirección.
- 🎚️ **Gráfica de Sonido Dinámica:** Ecualizador visual interactivo con 3 modos conmutables (`v`): Espectro de barras con picos de caída por gravedad, Osciloscopio y Vúmetro Estéreo.
- ⏱️ **Barra de Progreso en Tiempo Real:** Visualización fluida del tiempo transcurrido y total `[MM:SS / MM:SS]` sin parpadeos.
- 🏷️ **Metadatos ID3 / Vorbis:** Extracción de título, artista y álbum mediante `mutagen`.
- 🔊 **Control de Volumen:** Ajustes en pasos de ±5% e indicador de silencio (Mute).
- 🛡️ **Arquitectura Modular y Segura:** Compatible con PipeWire/PulseAudio/ALSA e inicialización headless segura para terminales.

---

## 🚀 Requisitos e Instalación

### Requisitos previos
- Linux (Debian, Ubuntu u otras distribuciones)
- Python 3.10+

### Instalación
```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio>
cd Harmony-Player-CLI

# 2. Crear y activar el entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# 3. Instalar la aplicación como comando de terminal
pip install .
```

---

## 🎮 Uso

Una vez instalado, puedes invocar directamente el comando:
```bash
harmony-player
```

O indicar una ruta específica para explorar audio y video:
```bash
harmony-player ~/Música
```

*(También disponible sin instalación global mediante `python3 -m harmony_player.main`)*.

---

## ⌨️ Atajos de Teclado

### En el Explorador / Reproductor de Audio:
| Tecla | Acción |
| :--- | :--- |
| `Enter` | Reproducir audio/video seleccionado o entrar a la carpeta |
| `Espacio` | Alternar Reproducir / Pausar (`Play/Pause`) |
| `s` | Detener reproducción (`Stop`) |
| `v` | Alternar modo de gráfica (Espectro / Osciloscopio / Vúmetro) |
| `+` / `=` | Subir volumen (+5%) |
| `-` | Bajar volumen (-5%) |
| `m` | Alternar Silencio (`Mute`) |
| `k` o `↑` | Mover cursor hacia arriba |
| `j` o `↓` | Mover cursor hacia abajo |
| `h` o `Backspace` | Subir al directorio anterior (`..`) |
| `q` o `Ctrl+C` | Salir limpiamente de la aplicación |

### Durante la Reproducción de Video (Pantalla Completa ANSI):
| Tecla | Acción |
| :--- | :--- |
| `Espacio` | Pausar / Reanudar video y audio en simultáneo |
| `m` | Alternar silencio (Mute) |
| `f` | Alternar relación de aspecto (Ajustado centrado vs Estirado) |
| `q` o `ESC` | Detener video y regresar al explorador de archivos |

---

## 📂 Arquitectura del Proyecto

```text
Harmony-Player-CLI/
├── .vscode/
│   ├── launch.json
│   └── settings.json
├── harmony_player/
│   ├── __init__.py
│   ├── main.py              # Punto de entrada CLI
│   ├── audio_engine.py      # Motor de audio con pygame.mixer y Master Clock
│   ├── video_engine.py      # Motor de decodificación de video, Half-Block ANSI y A/V Sync
│   ├── file_manager.py      # Navegación y filtrado de audio y video
│   ├── metadata.py          # Extracción de metadatos con mutagen
│   └── ui/
│       ├── __init__.py
│       ├── app.py           # Aplicación Textual y enrutamiento Audio/Video
│       ├── widgets.py       # Widgets interactivos y visualizador de espectro
│       └── styles.tcss      # Estilos Textual CSS
├── requirements.txt
├── README.md
├── Desarrollo.md
└── Desarrollo Video.md
```

