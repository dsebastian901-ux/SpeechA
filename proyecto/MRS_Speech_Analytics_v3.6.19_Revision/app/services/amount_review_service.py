"""Confirmaciones humanas de importes, vinculadas a una llamada y su evidencia."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from app.services.asr_amount_recovery import validated_entries


def evidence_digest(data):
    projection = {key: data.get(key) for key in ("archivo", "texto", "segmentos", "recuperacion_importes")}
    raw = json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def make_amount_review(data, confirmed_anchors, *, audio_verified):
    entries = validated_entries(data.get("texto", ""), data.get("segmentos", []), data.get("recuperacion_importes"))
    selected = set(confirmed_anchors)
    if selected-set(e["anchor_start"] for e in entries):
        raise ValueError("La confirmación no corresponde a evidencia recuperada válida.")
    if selected and audio_verified is not True:
        raise ValueError("Confirmar un importe requiere validación explícita del audio por el usuario.")
    return {"schema": 1, "source_sha256": evidence_digest(data),
            "reviewed_at": datetime.now(timezone.utc).isoformat(), "audio_verified": audio_verified is True,
            "scope": "RECOVERED_AMOUNTS_ONLY", "confirmed_entries": [
                {"anchor_start": e["anchor_start"], "amount": e["amount"]}
                for e in entries if e["anchor_start"] in selected]}


def amount_review_status(data, review):
    audit = data.get("recuperacion_importes") or {}
    pending = bool(isinstance(audit, dict) and audit.get("entries"))
    entries = validated_entries(data.get("texto", ""), data.get("segmentos", []), audit)
    valid = False
    if (isinstance(review, dict) and review.get("schema") == 1 and review.get("audio_verified") is True
            and review.get("scope") == "RECOVERED_AMOUNTS_ONLY"
            and review.get("source_sha256") == evidence_digest(data)):
        confirmed = review.get("confirmed_entries")
        expected = [{"anchor_start": e["anchor_start"], "amount": e["amount"]} for e in entries]
        valid = bool(expected and len(entries) == len(audit.get("entries", [])) and confirmed == expected)
    return {"entries": entries, "review_required": pending and not valid, "human_verified": valid,
            "human_review_record": review if valid else None}


class AmountReviewService:
    @staticmethod
    def _path(transcript):
        path = Path(transcript)
        return path.parent/".reviews"/(path.stem+".amounts.json")

    @classmethod
    def save(cls, transcript, anchors, *, audio_verified):
        source = Path(transcript)
        data = json.loads(source.read_text(encoding="utf-8"))
        review = make_amount_review(data, anchors, audio_verified=audio_verified)
        target = cls._path(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(target)
        return review

    @classmethod
    def load(cls, transcript):
        try:
            review = json.loads(cls._path(transcript).read_text(encoding="utf-8"))
            data = json.loads(Path(transcript).read_text(encoding="utf-8"))
            return review if amount_review_status(data, review)["human_verified"] else None
        except (OSError, ValueError, TypeError):
            return None
