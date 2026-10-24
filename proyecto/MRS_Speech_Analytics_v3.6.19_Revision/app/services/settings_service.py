"""
============================================================
MRS Speech Analytics Professional
Servicio: Configuración
============================================================
"""

import json
from pathlib import Path

from app.config import settings


class SettingsService:
    """
    Gestiona la configuración editable de la aplicación.

    Los valores originales de app/config/settings.py
    permanecen como valores predeterminados.

    Las preferencias del usuario se guardan en:

        data/app_settings.json
    """

    SETTINGS_FILE = (
        Path(settings.DATA_DIR)
        / "app_settings.json"
    )

    APPEARANCE_MODES = [
        "System",
        "Light",
        "Dark",
    ]

    WHISPER_MODELS = [
        "tiny",
        "base",
        "small",
        "medium",
        "large-v2",
        "large-v3",
    ]

    WHISPER_LANGUAGES = [
        "es",
        "en",
        "auto",
    ]

    WHISPER_DEVICES = [
        "cpu",
        "cuda",
    ]

    COMPUTE_TYPES = [
        "int8",
        "int8_float16",
        "float16",
        "float32",
    ]

    # =========================================================
    # VALORES PREDETERMINADOS
    # =========================================================

    @classmethod
    def get_defaults(cls):
        return {
            "appearance": str(
                getattr(
                    settings,
                    "THEME",
                    "System",
                )
            ),

            "color_theme": str(
                getattr(
                    settings,
                    "COLOR_THEME",
                    "blue",
                )
            ),

            "whisper_model": str(
                getattr(
                    settings,
                    "WHISPER_MODEL",
                    "small",
                )
            ),

            "whisper_language": str(
                getattr(
                    settings,
                    "WHISPER_LANGUAGE",
                    "es",
                )
            ),

            "whisper_device": str(
                getattr(
                    settings,
                    "WHISPER_DEVICE",
                    "cpu",
                )
            ),

            "whisper_compute_type": str(
                getattr(
                    settings,
                    "WHISPER_COMPUTE_TYPE",
                    "int8",
                )
            ),

            "whisper_beam_size": cls._safe_int(
                getattr(
                    settings,
                    "WHISPER_BEAM_SIZE",
                    1,
                ),
                default=1,
                minimum=1,
                maximum=20,
            ),

            "whisper_vad_filter": cls._safe_bool(
                getattr(
                    settings,
                    "WHISPER_VAD_FILTER",
                    True,
                )
            ),

            "whisper_word_timestamps": cls._safe_bool(
                getattr(
                    settings,
                    "WHISPER_WORD_TIMESTAMPS",
                    False,
                )
            ),

            "max_workers": cls._safe_int(
                getattr(
                    settings,
                    "MAX_WORKERS",
                    2,
                ),
                default=2,
                minimum=1,
                maximum=16,
            ),

            "process_batch_size": cls._safe_int(
                getattr(
                    settings,
                    "PROCESS_BATCH_SIZE",
                    10,
                ),
                default=10,
                minimum=1,
                maximum=1000,
            ),

            "minimum_score": cls._safe_int(
                getattr(
                    settings,
                    "MINIMUM_SCORE",
                    80,
                ),
                default=80,
                minimum=0,
                maximum=100,
            ),
        }

    # =========================================================
    # CARGAR
    # =========================================================

    @classmethod
    def load(cls):
        defaults = cls.get_defaults()

        if not cls.SETTINGS_FILE.exists():
            return defaults

        try:
            with cls.SETTINGS_FILE.open(
                "r",
                encoding="utf-8",
            ) as file:
                stored = json.load(file)

        except (
            OSError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ):
            return defaults

        if not isinstance(stored, dict):
            return defaults

        merged = defaults.copy()

        for key in defaults:
            if key in stored:
                merged[key] = stored[key]

        return cls.validate(
            merged
        )

    # =========================================================
    # GUARDAR
    # =========================================================

    @classmethod
    def save(
        cls,
        configuration,
    ):
        validated = cls.validate(
            configuration
        )

        cls.SETTINGS_FILE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with cls.SETTINGS_FILE.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                validated,
                file,
                ensure_ascii=False,
                indent=4,
            )

        return cls.SETTINGS_FILE

    # =========================================================
    # RESTABLECER
    # =========================================================

    @classmethod
    def reset(cls):
        try:
            if cls.SETTINGS_FILE.exists():
                cls.SETTINGS_FILE.unlink()

        except OSError:
            pass

        return cls.get_defaults()

    # =========================================================
    # VALIDAR
    # =========================================================

    @classmethod
    def validate(
        cls,
        configuration,
    ):
        defaults = cls.get_defaults()

        if not isinstance(
            configuration,
            dict,
        ):
            return defaults

        # -----------------------------------------------------
        # APARIENCIA
        # -----------------------------------------------------

        appearance = str(
            configuration.get(
                "appearance",
                defaults["appearance"],
            )
        )

        if appearance not in cls.APPEARANCE_MODES:
            appearance = defaults[
                "appearance"
            ]

        # -----------------------------------------------------
        # MODELO WHISPER
        # -----------------------------------------------------

        whisper_model = str(
            configuration.get(
                "whisper_model",
                defaults["whisper_model"],
            )
        ).strip()

        if whisper_model not in cls.WHISPER_MODELS:
            whisper_model = defaults[
                "whisper_model"
            ]

        # -----------------------------------------------------
        # IDIOMA
        # -----------------------------------------------------

        whisper_language = str(
            configuration.get(
                "whisper_language",
                defaults["whisper_language"],
            )
        ).strip().lower()

        if whisper_language not in cls.WHISPER_LANGUAGES:
            whisper_language = defaults[
                "whisper_language"
            ]

        # -----------------------------------------------------
        # DISPOSITIVO
        # -----------------------------------------------------

        whisper_device = str(
            configuration.get(
                "whisper_device",
                defaults["whisper_device"],
            )
        ).strip().lower()

        if whisper_device not in cls.WHISPER_DEVICES:
            whisper_device = defaults[
                "whisper_device"
            ]

        # -----------------------------------------------------
        # CÁLCULO
        # -----------------------------------------------------

        compute_type = str(
            configuration.get(
                "whisper_compute_type",
                defaults[
                    "whisper_compute_type"
                ],
            )
        ).strip()

        if compute_type not in cls.COMPUTE_TYPES:
            compute_type = defaults[
                "whisper_compute_type"
            ]

        # -----------------------------------------------------
        # RESULTADO
        # -----------------------------------------------------

        return {
            "appearance": appearance,

            "color_theme": str(
                configuration.get(
                    "color_theme",
                    defaults["color_theme"],
                )
                or defaults["color_theme"]
            ),

            "whisper_model": whisper_model,

            "whisper_language": whisper_language,

            "whisper_device": whisper_device,

            "whisper_compute_type": compute_type,

            "whisper_beam_size": cls._safe_int(
                configuration.get(
                    "whisper_beam_size",
                    defaults[
                        "whisper_beam_size"
                    ],
                ),
                default=defaults[
                    "whisper_beam_size"
                ],
                minimum=1,
                maximum=20,
            ),

            "whisper_vad_filter": cls._safe_bool(
                configuration.get(
                    "whisper_vad_filter",
                    defaults[
                        "whisper_vad_filter"
                    ],
                )
            ),

            "whisper_word_timestamps": cls._safe_bool(
                configuration.get(
                    "whisper_word_timestamps",
                    defaults[
                        "whisper_word_timestamps"
                    ],
                )
            ),

            "max_workers": cls._safe_int(
                configuration.get(
                    "max_workers",
                    defaults[
                        "max_workers"
                    ],
                ),
                default=defaults[
                    "max_workers"
                ],
                minimum=1,
                maximum=16,
            ),

            "process_batch_size": cls._safe_int(
                configuration.get(
                    "process_batch_size",
                    defaults[
                        "process_batch_size"
                    ],
                ),
                default=defaults[
                    "process_batch_size"
                ],
                minimum=1,
                maximum=1000,
            ),

            "minimum_score": cls._safe_int(
                configuration.get(
                    "minimum_score",
                    defaults[
                        "minimum_score"
                    ],
                ),
                default=defaults[
                    "minimum_score"
                ],
                minimum=0,
                maximum=100,
            ),
        }

    # =========================================================
    # OBTENER VALOR
    # =========================================================

    @classmethod
    def get(
        cls,
        key,
        default=None,
    ):
        configuration = cls.load()

        return configuration.get(
            key,
            default,
        )

    # =========================================================
    # BOOLEANO SEGURO
    # =========================================================

    @staticmethod
    def _safe_bool(value):
        if isinstance(
            value,
            bool,
        ):
            return value

        if isinstance(
            value,
            str,
        ):
            normalized = (
                value
                .strip()
                .lower()
            )

            if normalized in {
                "true",
                "1",
                "yes",
                "si",
                "sí",
                "on",
            }:
                return True

            if normalized in {
                "false",
                "0",
                "no",
                "off",
            }:
                return False

        return bool(value)

    # =========================================================
    # ENTERO SEGURO
    # =========================================================

    @staticmethod
    def _safe_int(
        value,
        default=0,
        minimum=None,
        maximum=None,
    ):
        try:
            number = int(value)

        except (
            TypeError,
            ValueError,
        ):
            number = int(default)

        if (
            minimum is not None
            and number < minimum
        ):
            number = minimum

        if (
            maximum is not None
            and number > maximum
        ):
            number = maximum

        return number
