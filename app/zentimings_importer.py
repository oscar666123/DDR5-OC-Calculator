from __future__ import annotations

import json
import re
from pathlib import Path


FIELD_ALIASES = {
    "MCLK": "MCLK",
    "UCLK": "UCLK",
    "FCLK": "FCLK",
    "tCL": "tCL",
    "CL": "tCL",
    "tRCDRD": "tRCD",
    "tRCDWR": "tRCDWR",
    "tRCD": "tRCD",
    "tRP": "tRP",
    "tRAS": "tRAS",
    "tRC": "tRC",
    "tWR": "tWR",
    "tRFC": "tRFC",
    "tRFC2": "tRFC2",
    "tRFCsb": "tRFCsb",
    "tREFI": "tREFI",
    "tRRDS": "tRRD_S",
    "tRRD_S": "tRRD_S",
    "tRRDL": "tRRD_L",
    "tRRD_L": "tRRD_L",
    "tFAW": "tFAW",
    "VSOC": "VSOC",
    "VDDCR_SOC": "VSOC",
    "VDD": "DRAM VDD",
    "VDDQ": "DRAM VDDQ",
    "VDDIO": "CPU VDDIO",
    "CPUVDDIO": "CPU VDDIO",
    "VDDGCCD": "VDDG CCD",
    "VDDG_CCD": "VDDG CCD",
    "VDDGIOD": "VDDG IOD",
    "VDDG_IOD": "VDDG IOD",
}


def _clean_value(value: object) -> str:
    text = str(value).strip()
    text = text.replace("MHz", "").replace("mV", "").strip()
    if re.fullmatch(r"\d{4,}", text) and text.startswith("1") and len(text) == 4:
        return f"{int(text) / 1000:.2f}V"
    return text


def parse_zentimings_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict):
        for key, value in data.items():
            canonical = FIELD_ALIASES.get(str(key).strip())
            if canonical:
                values[canonical] = _clean_value(value)
        return values

    pattern = re.compile(r"\b([A-Za-z0-9_]+)\b\s*[:=,;\t ]+\s*([A-Za-z0-9./+-]+)")
    for key, value in pattern.findall(text):
        canonical = FIELD_ALIASES.get(key.strip())
        if canonical:
            values[canonical] = _clean_value(value)
    return values


def import_zentimings_file(path: str | Path) -> dict[str, str]:
    return parse_zentimings_text(Path(path).read_text(encoding="utf-8", errors="ignore"))
