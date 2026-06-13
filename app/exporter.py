from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.models import RecommendationResult, TimingEntry, VoltageEntry


def _timing_lines(items: list[TimingEntry]) -> list[str]:
    return [f"{item.name}: {item.cycles} cycles | {item.ns:.2f} ns | {item.note} | 风险: {item.risk}" for item in items]


def _voltage_lines(items: list[VoltageEntry]) -> list[str]:
    return [f"{item.name}: {item.value} | {item.note} | 风险: {item.risk}" for item in items]


def result_to_text(result: RecommendationResult) -> str:
    config = result.config
    lines: list[str] = [
        "DDR5 OC Calculator Result",
        f"Platform: {config.platform}",
        f"CPU: {config.cpu_model or '-'}",
        f"Motherboard: {config.motherboard_model or '-'}",
        f"BIOS: {config.bios_version or '-'}",
        f"IC: {config.memory_ic}",
        f"Die: {config.die_type}",
        f"Kit: {config.kit} {config.rank} {config.sides}",
        f"Target Frequency: {config.target_frequency} MT/s",
        f"Profile: {config.tuning_style}",
    ]
    if result.profile is not None:
        lines.extend(
            [
                f"Profile Name: {result.profile.name}",
                f"Profile Description: {result.profile.description}",
                f"Total Capacity: {result.profile.total_capacity}",
                f"Module Capacity: {result.profile.module_capacity}",
                f"Rank: {result.profile.rank}",
                f"Side: {result.profile.side}",
                f"IC Density: {result.profile.ic_density}",
                f"Profile Type: {result.profile.profile_type}",
                f"Daily Target: {result.profile.daily_target} MT/s",
            ]
        )
    lines.extend(["", "Frequency:"])
    lines.extend(f"{key}: {value}" for key, value in result.frequency.items())
    lines.extend(["", "Primary Timings:"])
    lines.extend(_timing_lines(result.primary))
    lines.extend(["", "Secondary Timings:"])
    lines.extend(_timing_lines(result.secondary))
    lines.extend(["", "Tertiary Timings:"])
    lines.extend(_timing_lines(result.tertiary))
    lines.extend(["", "Voltages:"])
    lines.extend(_voltage_lines(result.voltages))
    lines.extend(
        [
            "",
            f"Risk Score: {result.risk_score} / 100",
            f"Risk Level: {result.risk_level}",
            "",
            "Risk Explanation:",
        ]
    )
    lines.extend(f"- {item}" for item in result.risk_explanations)
    if result.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {item}" for item in result.warnings)
    if result.reference_notes:
        lines.extend(["", "Reference Notes:"])
        lines.extend(f"- {item}" for item in result.reference_notes)
    lines.extend(["", "Stability Test Flow:"])
    lines.extend(f"{index}. {item}" for index, item in enumerate(result.stability_steps, start=1))
    lines.extend(["", "Tuning Advice:"])
    lines.extend(f"- {item}" for item in result.tuning_advice)
    return "\n".join(lines)


def result_to_json_dict(result: RecommendationResult) -> dict[str, Any]:
    return {
        "config": result.config.to_dict(),
        "profile": asdict(result.profile) if result.profile is not None else None,
        "frequency": result.frequency,
        "primary": [asdict(item) for item in result.primary],
        "secondary": [asdict(item) for item in result.secondary],
        "tertiary": [asdict(item) for item in result.tertiary],
        "voltages": [asdict(item) for item in result.voltages],
        "risk_score": result.risk_score,
        "risk_level": result.risk_level,
        "risk_explanations": result.risk_explanations,
        "warnings": result.warnings,
        "reference_notes": result.reference_notes,
        "stability_steps": result.stability_steps,
        "tuning_advice": result.tuning_advice,
    }


def result_to_html(result: RecommendationResult) -> str:
    risk_color = "#16833a"
    if result.risk_score > 75:
        risk_color = "#b00020"
    elif result.risk_score > 50:
        risk_color = "#b86400"
    elif result.risk_score > 25:
        risk_color = "#8a6d00"

    text = result_to_text(result)
    escaped = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>")
    )
    return (
        "<html><body style='font-family: Consolas, Microsoft YaHei, sans-serif; font-size: 12px;'>"
        f"<div style='padding:8px;background:{risk_color};color:white;font-weight:bold;'>"
        f"Risk Score: {result.risk_score} / 100 | {result.risk_level}"
        "</div>"
        f"<div style='margin-top:10px;'>{escaped}</div>"
        "</body></html>"
    )
