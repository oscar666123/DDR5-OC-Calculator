from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class InputConfig:
    platform: str = "AMD AM5"
    cpu_model: str = ""
    motherboard_model: str = ""
    bios_version: str = ""
    memory_ic: str = "Hynix A-die"
    die_type: str = "16Gb A-die"
    kit: str = "2x16GB"
    dimm_capacity: str = "16GB"
    rank: str = "Single Rank"
    sides: str = "单面"
    xmp_frequency: int = 6000
    xmp_tcl: int = 36
    xmp_trcd: int = 36
    xmp_trp: int = 36
    xmp_tras: int = 76
    target_frequency: int = 6000
    tuning_style: str = "Daily"
    cooling: str = "机箱风道"
    temperature_limit: int = 50
    voltage_strategy: str = "正常"
    total_capacity: str = "32GB"
    module_capacity: str = "16GB"
    ic_density: str = "16Gb"
    profile_type: str = "1DPC 2 DIMM"
    rgb_memory: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InputConfig":
        allowed = set(cls.__dataclass_fields__.keys())
        clean = {key: value for key, value in data.items() if key in allowed}
        return cls(**clean)


@dataclass(slots=True)
class MemoryProfile:
    name: str
    platform_focus: str
    total_capacity: str
    module_capacity: str
    rank: str
    side: str
    ic_density: str
    profile_type: str
    daily_target: int
    description: str


@dataclass(slots=True)
class TimingEntry:
    name: str
    cycles: int
    ns: float
    note: str
    risk: str = "正常"


@dataclass(slots=True)
class VoltageEntry:
    name: str
    value: str
    note: str
    risk: str = "正常"


@dataclass(slots=True)
class RecommendationResult:
    config: InputConfig
    frequency: dict[str, str]
    profile: MemoryProfile | None = None
    reference_notes: list[str] = field(default_factory=list)
    primary: list[TimingEntry] = field(default_factory=list)
    secondary: list[TimingEntry] = field(default_factory=list)
    tertiary: list[TimingEntry] = field(default_factory=list)
    voltages: list[VoltageEntry] = field(default_factory=list)
    risk_score: int = 0
    risk_level: str = "Safe"
    risk_explanations: list[str] = field(default_factory=list)
    stability_steps: list[str] = field(default_factory=list)
    tuning_advice: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
