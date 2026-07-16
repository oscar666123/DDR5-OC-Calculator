from __future__ import annotations

from typing import Any

from app.models import InputConfig, RecommendationResult


FIELD_SECTIONS = {
    "Frequency": [
        "Memory Frequency",
        "MCLK",
        "UCLK",
        "FCLK",
        "Gear / Ratio",
    ],
    "CPU / DRAM Voltage": [
        "DRAM VDD",
        "DRAM VDDQ",
        "CPU VDDIO",
        "VSOC",
        "VDDP",
        "VDDG CCD",
        "VDDG IOD",
        "VPP",
    ],
    "Primary Timings": ["tCL", "tRCD", "tRP", "tRAS", "tRC", "tCWL"],
    "Secondary Timings": [
        "tWR",
        "tRTP",
        "tRFC",
        "tRFC2",
        "tRFCsb",
        "tREFI",
        "tRRD_S",
        "tRRD_L",
        "tFAW",
        "tWTR_S",
        "tWTR_L",
    ],
    "Tertiary Timings": [
        "tRDRDSCL",
        "tWRWRSCL",
        "tRDRDSC",
        "tWRWRSC",
        "tRDRDSD",
        "tRDRDDD",
        "tWRWRSD",
        "tWRWRDD",
        "tRDWR",
        "tWRRD",
    ],
}


def fields_to_text(fields: dict[str, str]) -> str:
    lines: list[str] = []
    for section, names in FIELD_SECTIONS.items():
        if lines:
            lines.append("")
        lines.append(f"[{section}]")
        for name in names:
            if name in fields:
                lines.append(f"{name} = {fields[name]}")
    return "\n".join(lines)


def fields_to_json_dict(
    config: InputConfig,
    fields: dict[str, str],
    result: RecommendationResult | None,
    suggestions: list[str],
    parameter_sources: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "config": config.to_dict(),
        "profile": result.profile.name if result and result.profile else config.memory_ic,
        "profile_display_name": result.profile.display_name if result and result.profile else config.profile_display_name or config.memory_ic,
        "ic_vendor": result.profile.ic_vendor if result and result.profile else config.ic_vendor,
        "ic_type": result.profile.ic_type if result and result.profile else config.ic_type,
        "ic_density": result.profile.ic_density if result and result.profile else config.ic_density,
        "risk": {
            "score": result.risk_score if result else 0,
            "level": result.risk_level if result else "Unknown",
            "reasons": result.risk_explanations[:5] if result else [],
        },
        "bios_parameters": fields,
        "current_parameters": config.current_parameters,
        "parameter_sources": parameter_sources or {},
        "suggestions": suggestions,
    }
