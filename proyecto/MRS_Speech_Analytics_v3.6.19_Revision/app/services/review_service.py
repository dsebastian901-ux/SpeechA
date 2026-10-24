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

    @classmethod
    def save(cls, transcript, flags):
        original = Path(transcript)
        if not original.is_file():
            raise ValueError("Se requiere una transcripción JSON guardada.")
        path = cls._path(transcript)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"reviewed_at": datetime.now(timezone.utc).isoformat(),
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
        flags = payload.get("hostile_interlocutor_exception") or {}
        if not isinstance(flags, dict):
            return None
        return {key: flags.get(key) is True for key in cls.FLAGS}
