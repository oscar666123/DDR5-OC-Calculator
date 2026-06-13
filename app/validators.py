from __future__ import annotations

from app.models import InputConfig


class ValidationError(ValueError):
    pass


def parse_frequency(value: str) -> int:
    clean = str(value).strip().replace("MT/s", "").replace("+", "")
    try:
        frequency = int(clean)
    except ValueError as exc:
        raise ValidationError("频率必须是数字，例如 6000 或 8000+。") from exc
    if frequency < 4000 or frequency > 9000:
        raise ValidationError("目标频率需在 4000-9000 MT/s 范围内。")
    return frequency


def normalize_config(config: InputConfig) -> InputConfig:
    if config.memory_ic == "Hynix 16Gb A-die 2x32GB Dual Rank" and config.kit != "4x32GB":
        config.die_type = "16Gb A-die"
        config.kit = "2x32GB"
        config.dimm_capacity = "32GB"

    if config.sides == "双面":
        config.rank = "Dual Rank"

    if config.kit in {"2x32GB", "4x32GB"}:
        config.rank = "Dual Rank"
        config.sides = "双面"

    if is_hynix_adie_2x32_profile(config):
        config.memory_ic = "Hynix 16Gb A-die 2x32GB Dual Rank"
        config.die_type = "16Gb A-die"
        config.dimm_capacity = "32GB"
        config.rank = "Dual Rank"
        config.sides = "双面"
        config.total_capacity = "64GB"
        config.module_capacity = "32GB"
        config.ic_density = "16Gb"
        config.profile_type = "1DPC 2 DIMM"
        if config.platform == "AMD AM5" and config.target_frequency > 6400:
            config.target_frequency = 6200

    if "24" in config.kit or config.dimm_capacity == "24GB":
        config.die_type = "24Gb M-die"
        config.memory_ic = "Hynix M-die"

    if config.die_type == "16Gb A-die" and config.memory_ic != "Hynix 16Gb A-die 2x32GB Dual Rank":
        config.memory_ic = "Hynix A-die"

    if config.die_type in {"16Gb M-die", "24Gb M-die"}:
        config.memory_ic = "Hynix M-die"

    if is_hynix_adie_4x32_profile(config):
        config.die_type = "16Gb A-die"
        config.dimm_capacity = "32GB"
        config.rank = "Dual Rank"
        config.sides = "双面"
        config.total_capacity = "128GB"
        config.module_capacity = "32GB"
        config.ic_density = "16Gb"
        config.profile_type = "2DPC 4 DIMM"
        config.target_frequency = min(config.target_frequency, 5600)

    return config


def validate_config(config: InputConfig) -> None:
    integer_fields = {
        "当前 XMP/EXPO 频率": config.xmp_frequency,
        "XMP tCL": config.xmp_tcl,
        "XMP tRCD": config.xmp_trcd,
        "XMP tRP": config.xmp_trp,
        "XMP tRAS": config.xmp_tras,
        "目标频率": config.target_frequency,
        "目标温度上限": config.temperature_limit,
    }
    for label, value in integer_fields.items():
        if not isinstance(value, int) or value <= 0:
            raise ValidationError(f"{label} 必须是正整数。")

    if config.temperature_limit < 35 or config.temperature_limit > 80:
        raise ValidationError("目标温度上限需在 35-80°C 范围内。")

    if config.die_type == "24Gb M-die" and config.dimm_capacity == "16GB":
        raise ValidationError("24Gb M-die 通常对应 24GB 单条或 2x24GB 套条。")

    if config.memory_ic == "Hynix A-die" and config.die_type != "16Gb A-die":
        raise ValidationError("Hynix A-die 当前只支持 16Gb A-die。")


def is_hynix_adie_2x32_profile(config: InputConfig) -> bool:
    return (
        config.kit == "2x32GB"
        and config.die_type == "16Gb A-die"
        and config.memory_ic in {"Hynix A-die", "Hynix 16Gb A-die 2x32GB Dual Rank"}
    )


def is_hynix_adie_4x32_profile(config: InputConfig) -> bool:
    return (
        config.kit == "4x32GB"
        and config.die_type == "16Gb A-die"
        and config.memory_ic in {"Hynix A-die", "Hynix 16Gb A-die 2x32GB Dual Rank"}
    )


def is_four_dimm(kit: str) -> bool:
    return kit.startswith("4x")


def is_dual_rank(config: InputConfig) -> bool:
    return config.rank == "Dual Rank" or config.sides == "双面" or config.kit in {"2x32GB", "4x32GB"}
