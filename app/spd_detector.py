from __future__ import annotations

import json
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "part_number_db.json"


def infer_ic_profile(part_numbers: list[str]) -> str:
    try:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    normalized = [part.strip().upper() for part in part_numbers if part.strip()]
    for part in normalized:
        for key, profile in data.items():
            if key.upper() in part:
                return str(profile)
    return ""


def infer_ic_profile_info(part_numbers: list[str]) -> dict[str, str]:
    profile = infer_ic_profile(part_numbers)
    if profile:
        return {
            "profile": profile,
            "source": "Part Number DB",
            "confidence": "medium",
        }
    return {
        "profile": "",
        "source": "Manual Selection",
        "confidence": "unknown",
    }
