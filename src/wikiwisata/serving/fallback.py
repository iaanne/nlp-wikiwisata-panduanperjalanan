"""Mode jawaban terbatas (fallback) dan redaksi PII untuk serving Wikiwisata."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

# Pola NIK Indonesia (16 digit angka yang berdiri sendiri)
_NIK_PATTERN = re.compile(r"\b\d{16}\b")

# Pola nomor telepon kantor/area lokal Indonesia, mis. (0274) 562000, 021-5551234, +62 274 562000
_OFFICE_PHONE_PATTERN = re.compile(
    r"(?:\(\s*0[2-9]\d{1,3}\s*\)[\s\-]?|(?:\+?62[\s\-]?|0)[2-79]\d{1,2}[\s\-]?)\d{5,8}\b"
)

# Pola nomor ponsel pribadi Indonesia (08xx / +628xx)
_PERSONAL_MOBILE_PATTERN = re.compile(
    r"(?:\+?62[\s\-]?8\d{2}|08\d{2})[\s\-]?\d{3,4}[\s\-]?\d{3,5}\b"
)

# Pola email pribadi / umum
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Kata kunci permintaan data pribadi / PII eksplisit
_PERSONAL_PII_QUERY_PATTERNS = (
    re.compile(r"\b(?:nik|ktp|no\.?\s*ktp|nomor\s+induk\s+kependudukan)\b", re.I),
    re.compile(r"\b(?:nomor|no\.?)\s*(?:hp|wa|whatsapp|telepon|ponsel)\s+pribadi\b", re.I),
    re.compile(r"\b(?:alamat\s+rumah\s+pribadi|alamat\s+pribadi)\b", re.I),
    re.compile(r"\b(?:email\s+pribadi|paspor|nomor\s+rekening|rekening\s+pribadi)\b", re.I),
    re.compile(
        r"\b(?:pemilik|kontributor|penulis|manajer|pemandu)\b.*\b(?:pribadi|nik|ktp|wa|hp)\b",
        re.I,
    ),
)

# Kata kunci permintaan keselamatan mutlak / medis darurat / jalur ilegal
_SAFETY_ABSTAIN_PATTERNS = (
    re.compile(r"\b(?:dijamin|jaminan|pastikan)\s+(?:100%\s+)?aman\b", re.I),
    re.compile(r"\b(?:jalur\s+tikus|jalur\s+ilegal|tanpa\s+tiket\s+dan\s+tanpa\s+lapor)\b", re.I),
    re.compile(r"\b(?:dosis\s+obat|suntikkan\s+sendiri|tanpa\s+ke\s+rumah\s+sakit)\b", re.I),
)


def is_personal_pii_request(question: str) -> bool:
    """Deteksi apakah pertanyaan secara eksplisit meminta data pribadi/kontak personal."""
    return any(pattern.search(question) for pattern in _PERSONAL_PII_QUERY_PATTERNS)


def is_unsafe_guarantee_request(question: str) -> bool:
    """Deteksi apakah pertanyaan meminta jaminan keselamatan mutlak atau instruksi berbahaya."""
    return any(pattern.search(question) for pattern in _SAFETY_ABSTAIN_PATTERNS)


def redact_pii(text: str, *, force_personal_contact_redaction: bool = False) -> tuple[str, bool]:
    """Sensor PII sesuai aturan tim:
    - Selalu sensor NIK 16 digit -> [REDACTED_NIK].
    - Nomor telepon kantor berkode area lokal seperti (0274) tetap dibiarkan.
    - Jika teks mencantumkan kontak kantor SEKALIGUS kontak pribadi (HP/email),
      ambil yang kantor saja dan sensor kontak pribadi -> [REDACTED_PII].
    - Jika suatu tempat hanya mencantumkan kontak pribadi/email sebagai satu-satunya kontak
      resmi usaha, tetap biarkan kecuali force_personal_contact_redaction=True.
    """
    if not text:
        return text, False

    redacted = text
    changed = False

    if _NIK_PATTERN.search(redacted):
        redacted = _NIK_PATTERN.sub("[REDACTED_NIK]", redacted)
        changed = True

    has_office_phone = bool(_OFFICE_PHONE_PATTERN.search(redacted))
    should_redact_personal = force_personal_contact_redaction or has_office_phone

    if should_redact_personal:
        if _PERSONAL_MOBILE_PATTERN.search(redacted):
            redacted = _PERSONAL_MOBILE_PATTERN.sub("[REDACTED_PII]", redacted)
            changed = True
        if _EMAIL_PATTERN.search(redacted):
            redacted = _EMAIL_PATTERN.sub("[REDACTED_PII]", redacted)
            changed = True

    return redacted, changed


def build_fallback_response(
    *,
    reason: str,
    config_id: str,
    prompt_id: str = "fallback",
    prompt_version: str = "1.0.0",
    user_message: str | None = None,
    extra_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bangun respons mode terbatas (abstain) yang valid terhadap schemas/answer.schema.json."""
    message = user_message or (
        "Maaf, sistem belum dapat memberikan jawaban terverifikasi saat ini "
        f"({reason})."
    )
    meta: dict[str, Any] = {
        "config_id": config_id,
        "prompt_id": prompt_id,
        "prompt_version": prompt_version,
        "fallback": True,
        "fallback_reason": reason,
    }
    if extra_meta:
        meta.update(extra_meta)

    return {
        "answer": message,
        "claims": [],
        "citations": [],
        "verdict": "abstain",
        "abstain_reason": reason,
        "tool_calls": [],
        "meta": meta,
    }


def sanitize_output(
    output: dict[str, Any],
    *,
    force_personal_contact_redaction: bool = False,
) -> tuple[dict[str, Any], bool]:
    """Terapkan redaksi PII pada seluruh teks di output JSON tanpa merusak skema."""
    cleaned = deepcopy(output)
    any_redacted = False

    answer_text, changed = redact_pii(
        str(cleaned.get("answer", "")),
        force_personal_contact_redaction=force_personal_contact_redaction,
    )
    cleaned["answer"] = answer_text
    any_redacted = any_redacted or changed

    for claim in cleaned.get("claims", []):
        if isinstance(claim, dict) and "text" in claim:
            claim_text, claim_changed = redact_pii(
                str(claim["text"]),
                force_personal_contact_redaction=force_personal_contact_redaction,
            )
            claim["text"] = claim_text
            any_redacted = any_redacted or claim_changed

    if cleaned.get("abstain_reason"):
        reason_text, reason_changed = redact_pii(
            str(cleaned["abstain_reason"]),
            force_personal_contact_redaction=force_personal_contact_redaction,
        )
        cleaned["abstain_reason"] = reason_text
        any_redacted = any_redacted or reason_changed

    return cleaned, any_redacted
