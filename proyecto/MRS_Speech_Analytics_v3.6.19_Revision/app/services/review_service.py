"""Validaciones humanas separadas del JSON original de Whisper."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


class ReviewService:
    FLAGS = ("audio_verified", "interlocutor_hostile_or_lascivious", "prevented_script", "agent_professional")

    @staticmethod
    def _path(transcript):
        path = Path(transcript)
        return path.parent / ".reviews" / (path.stem + ".json")

    @staticmethod
    def _audio_digest(transcript):
        """Vincular también el audio si está disponible, sin enviar su contenido."""
        try:
            original=Path(transcript)
            data=json.loads(original.read_text(encoding='utf-8-sig'))
            source=data.get('audio_path') or data.get('ruta_audio')
            if not source:return None
            audio=Path(source)
            if not audio.is_absolute():audio=original.parent/audio
            if not audio.is_file():return None
            hasher=hashlib.sha256()
            with audio.open('rb') as handle:
                for block in iter(lambda:handle.read(1024*1024),b''):hasher.update(block)
            return hasher.hexdigest()
        except (OSError,ValueError,TypeError,AttributeError):
            return None

    @classmethod
    def save(cls, transcript, flags):
        original = Path(transcript)
        if not original.is_file():
            raise ValueError("Se requiere una transcripción JSON guardada.")
        path = cls._path(transcript)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"audio_sha256": cls._audio_digest(transcript), "reviewed_at": datetime.now(timezone.utc).isoformat(),
                   "transcript_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
                   "hostile_interlocutor_exception": {key: flags.get(key) is True for key in cls.FLAGS}}
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
        return payload["hostile_interlocutor_exception"]

    @classmethod
    def load(cls, transcript):
        path = cls._path(transcript)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None
        if not isinstance(payload, dict):
            return None
        if payload.get("transcript_sha256") != hashlib.sha256(Path(transcript).read_bytes()).hexdigest():
            return None  # Una revisión anterior no certifica una transcripción modificada.
        if payload.get("audio_sha256") is not None and payload["audio_sha256"] != cls._audio_digest(transcript):
            return None
        flags = payload.get("hostile_interlocutor_exception") or {}
        if not isinstance(flags, dict):
            return None
        return {key: flags.get(key) is True for key in cls.FLAGS}
