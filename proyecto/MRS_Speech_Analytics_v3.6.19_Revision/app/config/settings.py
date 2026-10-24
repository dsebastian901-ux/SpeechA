"""
============================================================
MRS Speech Analytics Professional
Configuración general de la aplicación
============================================================
"""

from pathlib import Path


# -----------------------------------------------------------
# Información de la aplicación
# -----------------------------------------------------------

APP_NAME = "MRS Speech Analytics Professional"
APP_VERSION = "1.0.0"


# -----------------------------------------------------------
# Apariencia de la interfaz
# -----------------------------------------------------------

# Valores válidos de CustomTkinter:
# "System", "Light" o "Dark"
THEME = "System"

# Temas incluidos en CustomTkinter:
# "blue", "green" o "dark-blue"
COLOR_THEME = "blue"


# -----------------------------------------------------------
# Tamaño de la ventana principal
# -----------------------------------------------------------

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 760

WINDOW_MIN_WIDTH = 1024
WINDOW_MIN_HEIGHT = 650


# -----------------------------------------------------------
# Directorios principales
# -----------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
REPORTS_DIR = PROJECT_ROOT / "reports"

AUDIOS_DIR = DATA_DIR / "audios"
TRANSCRIPTIONS_DIR = DATA_DIR / "transcriptions"
RESULTS_DIR = DATA_DIR / "results"
EXPORTS_DIR = DATA_DIR / "exports"
PROJECTS_DIR = DATA_DIR / "projects"


# -----------------------------------------------------------
# Formatos de audio compatibles
# -----------------------------------------------------------

SUPPORTED_AUDIO_FORMATS = (
    ".wav",
    ".mp3",
    ".m4a",
    ".ogg",
    ".flac",
    ".aac",
    ".wma",
)


# -----------------------------------------------------------
# Configuración de Faster-Whisper
# -----------------------------------------------------------

WHISPER_MODEL = "small"
WHISPER_LANGUAGE = "es"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"

WHISPER_BEAM_SIZE = 5
WHISPER_VAD_FILTER = True
WHISPER_WORD_TIMESTAMPS = False


# -----------------------------------------------------------
# Procesamiento
# -----------------------------------------------------------

MAX_WORKERS = 2
PROCESS_BATCH_SIZE = 10


# -----------------------------------------------------------
# Calidad y calificación
# -----------------------------------------------------------

MINIMUM_SCORE = 80


# -----------------------------------------------------------
# Crear automáticamente las carpetas necesarias
# -----------------------------------------------------------

REQUIRED_DIRECTORIES = (
    DATA_DIR,
    LOGS_DIR,
    REPORTS_DIR,
    AUDIOS_DIR,
    TRANSCRIPTIONS_DIR,
    RESULTS_DIR,
    EXPORTS_DIR,
    PROJECTS_DIR,
)

for folder in REQUIRED_DIRECTORIES:
    folder.mkdir(parents=True, exist_ok=True)
