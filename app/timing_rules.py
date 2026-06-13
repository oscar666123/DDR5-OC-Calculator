from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from app.models import InputConfig, MemoryProfile, RecommendationResult, TimingEntry
from app.presets import BASE_TUNING_ADVICE, HYNIX_ADIE_2X32_AM5_PRESETS, HYNIX_ADIE_2X32_INTEL_PRESETS, STABILITY_STEPS
from app.reference_notes import get_reference_notes
from app.validators import (
    is_dual_rank,
    is_four_dimm,
    is_hynix_adie_2x32_profile,
    is_hynix_adie_4x32_profile,
    normalize_config,
    validate_config,
)
from app.voltage_rules import calculate_hynix_adie_2x32_voltages, calculate_voltages
from app.risk_engine import calculate_risk


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def tck_ns(mt_s: int) -> float:
    return 2000.0 / mt_s


def timing_ns(cycles: int, mt_s: int) -> float:
    return cycles * tck_ns(mt_s)


def cycles_from_ns(target_ns: float, mt_s: int) -> int:
    return int(math.ceil(target_ns / tck_ns(mt_s)))


def _load_json(name: str) -> dict[str, Any]:
    path = DATA_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def _ic_rule_file(config: InputConfig) -> str:
    if config.die_type == "16Gb A-die":
        return "hynix_adie.json"
    return "hynix_mdie.json"


def _range_mid(low: int, high: int) -> int:
    return int(round((low + high) / 2))


def _style_delta(style: str) -> int:
    return {
        "Safe": 2,
        "Daily": 0,
        "Performance": -1,
        "Benchmark": -2,
    }.get(style, 0)


def _primary_base(config: InputConfig) -> dict[str, int]:
    freq = config.target_frequency
    delta = _style_delta(config.tuning_style)

    if config.platform == "AMD AM5":
        if freq <= 6000:
            base = {"tCL": 30, "tRCD": 36, "tRP": 36, "tRAS": 36}
        elif freq <= 6200:
            base = {"tCL": 32, "tRCD": 38, "tRP": 38, "tRAS": 38}
        elif freq <= 6400:
            base = {"tCL": 34, "tRCD": 40, "tRP": 40, "tRAS": 42}
        elif freq <= 6800:
            base = {"tCL": 36, "tRCD": 44, "tRP": 44, "tRAS": 46}
        else:
            base = {"tCL": 38, "tRCD": 46, "tRP": 46, "tRAS": 48}
    else:
        if freq <= 6800:
            base = {"tCL": 34, "tRCD": 40, "tRP": 40, "tRAS": 40}
        elif freq <= 7200:
            base = {"tCL": 36, "tRCD": 44, "tRP": 44, "tRAS": 42}
        elif freq <= 7600:
            base = {"tCL": 38, "tRCD": 46, "tRP": 46, "tRAS": 46}
        else:
            base = {"tCL": 40, "tRCD": 48, "tRP": 48, "tRAS": 48}

    if config.die_type == "16Gb M-die":
        base["tRCD"] += 2
        base["tRP"] += 2
    if config.die_type == "24Gb M-die":
        base["tRCD"] += 4
        base["tRP"] += 4
        base["tRAS"] += 2

    if is_dual_rank(config):
        base["tRCD"] += 2
        base["tRP"] += 2
        base["tRAS"] += 2

    for key in base:
        if key == "tCL":
            base[key] = max(26, base[key] + delta)
        else:
            base[key] = max(30, base[key] + delta)
    return base


def _rfc_value(config: InputConfig, rules: dict[str, Any]) -> int:
    rfc_ranges = rules["tRFC_ranges"]
    low, high = rfc_ranges[config.die_type]
    value = _range_mid(low, high)

    if config.target_frequency >= 6400:
        value += 30
    if config.target_frequency >= 7200:
        value += 30
    if is_dual_rank(config):
        value += 90
    if is_four_dimm(config.kit):
        value += 80
    if config.temperature_limit > 50:
        value += 40
    if config.cooling == "内存直吹风扇" and config.temperature_limit <= 50:
        value -= 20

    if config.tuning_style == "Safe":
        value += 40
    elif config.tuning_style == "Performance":
        value -= 20
    elif config.tuning_style == "Benchmark":
        value -= 40

    return max(rules["safe_bounds"]["tRFC_min"], value)


def _refresh_value(config: InputConfig) -> int:
    if config.temperature_limit < 45:
        base = 65535
    elif config.temperature_limit <= 50:
        base = 50000 if config.tuning_style in {"Safe", "Daily"} else 65535
    elif config.temperature_limit <= 55:
        base = 32768
    else:
        base = 16384
    if config.cooling == "无风扇" and config.temperature_limit >= 50:
        base = min(base, 32768)
    return base


def _frequency_block(config: InputConfig) -> dict[str, str]:
    mclk = config.target_frequency // 2
    data = {
        "MT/s": f"{config.target_frequency} MT/s",
        "MCLK": f"{mclk} MHz",
        "tCK": f"{tck_ns(config.target_frequency):.3f} ns",
    }
    if config.platform == "AMD AM5":
        if config.target_frequency <= 6000:
            uclk = f"{mclk} MHz"
        elif config.target_frequency <= 6400:
            uclk = f"{mclk} MHz，优先尝试 UCLK=MCLK"
        else:
            uclk = f"{mclk // 2}-{mclk} MHz，可能需要 UCLK 分频"
        fclk = 2000 if config.target_frequency <= 6000 else 2066 if config.target_frequency <= 6200 else 2133
        data["UCLK"] = uclk
        data["FCLK"] = f"{fclk} MHz"
    else:
        data["Gear"] = "Gear 2"
        data["IMC"] = "6800-7200 日用区间，7600+ 依赖主板和 IMC 体质"
    return data


def _entry(name: str, cycles: int, mt_s: int, note: str, risk: str = "正常") -> TimingEntry:
    return TimingEntry(name=name, cycles=cycles, ns=timing_ns(cycles, mt_s), note=note, risk=risk)


def _hynix_adie_2x32_profile(config: InputConfig) -> MemoryProfile:
    return MemoryProfile(
        name="Hynix 16Gb A-die 2x32GB Dual Rank" if config.kit == "2x32GB" else "Hynix 16Gb A-die 4x32GB High Risk",
        platform_focus="AMD AM5 preferred, Intel DDR5 supported",
        total_capacity=config.total_capacity,
        module_capacity=config.module_capacity,
        rank=config.rank,
        side="Double Sided",
        ic_density=config.ic_density,
        profile_type=config.profile_type,
        daily_target=6000 if config.platform == "AMD AM5" else 6400,
        description="64GB Dual Rank A-die Profile" if config.kit == "2x32GB" else "128GB 4 DIMM A-die High Risk Profile",
    )


def _adie_2x32_preset_key(config: InputConfig) -> str:
    if config.platform == "AMD AM5":
        if config.target_frequency <= 5600:
            return "Safe"
        if config.target_frequency <= 6000:
            return "Daily"
        if config.target_frequency <= 6200:
            return "Performance"
        return "Benchmark"
    if config.target_frequency <= 6400:
        return "Daily"
    if config.target_frequency <= 6800:
        return "Performance"
    return "Benchmark"


def calculate_refresh_timings_for_2x32(config: InputConfig, preset_secondary: dict[str, int]) -> dict[str, int]:
    timings = dict(preset_secondary)
    if config.temperature_limit < 45:
        t_refi = 65535 if config.cooling == "内存直吹风扇" else 50000
    elif config.temperature_limit <= 50:
        t_refi = 65535 if config.cooling == "内存直吹风扇" and config.target_frequency <= 6200 else 50000
    elif config.temperature_limit <= 55:
        t_refi = 32768
        timings["tRFC"] += 60
    else:
        t_refi = 16384
        timings["tRFC"] += 100

    if config.cooling == "无风扇":
        t_refi = min(t_refi, 50000)
    if config.target_frequency >= 6400 and config.cooling != "内存直吹风扇":
        t_refi = min(t_refi, 50000)
    if is_hynix_adie_4x32_profile(config):
        t_refi = min(t_refi, 32768)
        timings["tRFC"] += 120
        timings["tRRD_L"] = max(timings["tRRD_L"], 14)
        timings["tFAW"] = max(timings["tFAW"], 40)

    timings["tREFI"] = t_refi
    timings["tRFC2"] = max(timings["tRFC2"], int(timings["tRFC"] * 0.72))
    timings["tRFCsb"] = max(timings["tRFCsb"], int(timings["tRFC"] * 0.55))
    return timings


def enforce_dual_rank_limits(config: InputConfig, secondary: dict[str, int], tertiary: dict[str, int]) -> None:
    if config.target_frequency <= 6000:
        secondary["tRFC"] = max(secondary["tRFC"], 520)
    elif config.target_frequency <= 6200:
        secondary["tRFC"] = max(secondary["tRFC"], 560)
    else:
        secondary["tRFC"] = max(secondary["tRFC"], 600)
    secondary["tRRD_L"] = max(secondary["tRRD_L"], 10)
    secondary["tFAW"] = max(secondary["tFAW"], 24)
    if config.target_frequency >= 6400 or config.tuning_style == "Safe":
        secondary["tRRD_S"] = max(secondary["tRRD_S"], 8)
        secondary["tRRD_L"] = max(secondary["tRRD_L"], 12)
        secondary["tFAW"] = max(secondary["tFAW"], 32)
    tertiary["tRDRDSCL"] = max(tertiary["tRDRDSCL"], 6)
    tertiary["tWRWRSCL"] = max(tertiary["tWRWRSCL"], 6)
    tertiary["tRDRDSD"] = max(tertiary["tRDRDSD"], 8)
    tertiary["tRDRDDD"] = max(tertiary["tRDRDDD"], 8)
    tertiary["tWRWRSD"] = max(tertiary["tWRWRSD"], 10)
    tertiary["tWRWRDD"] = max(tertiary["tWRWRDD"], 10)


def calculate_hynix_adie_2x32_timings(config: InputConfig) -> RecommendationResult:
    preset_key = _adie_2x32_preset_key(config)
    preset_map = HYNIX_ADIE_2X32_AM5_PRESETS if config.platform == "AMD AM5" else HYNIX_ADIE_2X32_INTEL_PRESETS
    preset = preset_map[preset_key]
    freq = config.target_frequency
    primary_values = dict(preset["primary"])
    secondary_values = calculate_refresh_timings_for_2x32(config, preset["secondary"])
    tertiary_values = dict(preset["tertiary"])
    enforce_dual_rank_limits(config, secondary_values, tertiary_values)

    primary_values["tRAS"] = max(primary_values["tRAS"], primary_values["tRCD"] + secondary_values["tRTP"])
    t_rc = max(primary_values["tRAS"] + primary_values["tRP"], 76)
    if freq >= 6200:
        t_rc = max(t_rc, 80)
    if freq >= 6400:
        t_rc = max(t_rc, 84)
    t_cwl = max(20, primary_values["tCL"] - 2)

    primary = [
        _entry("tCL", primary_values["tCL"], freq, "2x32GB A-die Dual Rank 专用 CAS 延迟。"),
        _entry("tRCD", primary_values["tRCD"], freq, "Dual Rank 大容量套条采用更保守 tRCD。"),
        _entry("tRP", primary_values["tRP"], freq, "Dual Rank 大容量套条采用更保守 tRP。"),
        _entry("tRAS", primary_values["tRAS"], freq, "已满足 tRAS >= tRCD + tRTP。"),
        _entry("tRC", t_rc, freq, "已满足 tRC >= tRAS + tRP。"),
        _entry("tCWL", t_cwl, freq, "写 CAS，按 tCL - 2 生成。"),
    ]
    secondary = [
        _entry("tWR", secondary_values["tWR"], freq, "写恢复时间，2x32GB 保持日用稳定优先。"),
        _entry("tRTP", secondary_values["tRTP"], freq, "读到预充电时间。"),
        _entry("tRFC", secondary_values["tRFC"], freq, "2x32GB A-die refresh 专用值，温度升高会自动放宽。"),
        _entry("tRFC2", secondary_values["tRFC2"], freq, "二级刷新恢复时间，随 tRFC 保守联动。"),
        _entry("tRFCsb", secondary_values["tRFCsb"], freq, "Same-bank 刷新恢复时间，随 tRFC 保守联动。"),
        _entry("tREFI", secondary_values["tREFI"], freq, "无主动风扇和高温场景会自动降低 tREFI。", "高温敏感" if secondary_values["tREFI"] > 50000 else "正常"),
        _entry("tRRD_S", secondary_values["tRRD_S"], freq, "Dual Rank 短行激活间隔。"),
        _entry("tRRD_L", secondary_values["tRRD_L"], freq, "Dual Rank 长行激活间隔，2x32GB 保守处理。"),
        _entry("tFAW", secondary_values["tFAW"], freq, "Dual Rank 四激活窗口，已保持 tFAW >= 4 x tRRD_S。"),
        _entry("tWTR_S", secondary_values["tWTR_S"], freq, "短写到读延迟。"),
        _entry("tWTR_L", secondary_values["tWTR_L"], freq, "长写到读延迟。"),
    ]
    tertiary = [
        _entry(name, value, freq, "2x32GB Dual Rank SD/DD 三时序保守值。")
        for name, value in tertiary_values.items()
    ]

    voltages, voltage_warnings = calculate_hynix_adie_2x32_voltages(config)
    risk_score, risk_level, risk_explanations = calculate_risk(config, voltages, secondary)
    if config.platform == "AMD AM5" and freq >= 6200 and risk_score < 51:
        risk_score = 51
        risk_level = "Performance"
        risk_explanations.append("AM5 2x32GB A-die 6200+ 风险等级按 Performance 起步。")
    if config.platform == "AMD AM5" and freq >= 6400 and risk_score < 76:
        risk_score = 76
        risk_level = "Benchmark / High Risk"
        risk_explanations.append("AM5 2x32GB A-die 6400 风险等级按 High Risk 起步。")
    if is_hynix_adie_4x32_profile(config) and risk_score < 76:
        risk_score = 76
        risk_level = "Benchmark / High Risk"
        risk_explanations.append("4x32GB A-die 风险等级按 High Risk 起步。")

    warnings = list(voltage_warnings)
    warnings.append("2x32GB Hynix A-die 是 Dual Rank 大容量套条，优先目标是 6000 MT/s 低延迟稳定。6200/6400 需要 IMC、主板 BIOS 和散热共同支持。建议从 6000 Daily profile 开始测试。")
    if config.platform == "AMD AM5" and freq >= 6400:
        warnings.append("需要测试 UCLK=MCLK，失败时降到 6200 或 6000。")
    if is_hynix_adie_4x32_profile(config):
        warnings.append("4x32GB 已按 5200-5600 Safe 思路降频，并使用更保守 refresh 与三时序。")
    if config.temperature_limit > 55:
        warnings.append("目标温度高于 55°C，建议加风扇、降压、降低 tREFI、提高 tRFC。")

    profile = _hynix_adie_2x32_profile(config)
    return RecommendationResult(
        config=config,
        frequency=_frequency_block(config),
        profile=profile,
        reference_notes=get_reference_notes(profile.name),
        primary=primary,
        secondary=secondary,
        tertiary=tertiary,
        voltages=voltages,
        risk_score=risk_score,
        risk_level=risk_level,
        risk_explanations=risk_explanations,
        stability_steps=STABILITY_STEPS,
        tuning_advice=BASE_TUNING_ADVICE,
        warnings=warnings,
    )


def calculate_recommendation(config: InputConfig) -> RecommendationResult:
    config = normalize_config(config)
    validate_config(config)

    if is_hynix_adie_2x32_profile(config) or is_hynix_adie_4x32_profile(config):
        return calculate_hynix_adie_2x32_timings(config)

    rules = _load_json(_ic_rule_file(config))
    freq = config.target_frequency
    primary_values = _primary_base(config)

    t_rtp = 12 if freq <= 6400 else 14
    t_wr = max(48 if freq <= 6400 else 52, 2 * t_rtp)
    primary_values["tRAS"] = max(primary_values["tRAS"], primary_values["tRCD"] + t_rtp)
    t_rc = max(primary_values["tRAS"] + primary_values["tRP"], 68)
    t_cwl = max(20, primary_values["tCL"] - 2)

    rrd_s = 4 if config.tuning_style in {"Performance", "Benchmark"} else 6
    rrd_l = 8 if not is_dual_rank(config) else 10
    if config.tuning_style == "Safe":
        rrd_l += 2
    t_faw = max(20 if config.platform == "AMD AM5" else 16, 4 * rrd_s)
    if is_dual_rank(config):
        t_faw += 4
    if is_four_dimm(config.kit):
        t_faw += 8

    t_rfc = _rfc_value(config, rules)
    t_refi = _refresh_value(config)
    t_rfc2 = max(320, int(t_rfc * 0.80))
    t_rfcsb = max(240, int(t_rfc * 0.60))

    primary = [
        _entry("tCL", primary_values["tCL"], freq, "CAS 延迟，越低延迟越好，受颗粒和电压影响大。"),
        _entry("tRCD", primary_values["tRCD"], freq, "行到列延迟，M-die 和高频时优先保证稳定。"),
        _entry("tRP", primary_values["tRP"], freq, "预充电延迟，通常跟随 tRCD 调整。"),
        _entry("tRAS", primary_values["tRAS"], freq, "已自动满足 tRAS >= tRCD + tRTP。"),
        _entry("tRC", t_rc, freq, "已自动满足 tRC >= tRAS + tRP。"),
        _entry("tCWL", t_cwl, freq, "写 CAS，默认按 tCL - 2 建议。"),
    ]

    secondary = [
        _entry("tWR", t_wr, freq, "写恢复时间，已满足 tWR >= 2 x tRTP。"),
        _entry("tRTP", t_rtp, freq, "读到预充电时间。"),
        _entry("tRFC", t_rfc, freq, "刷新恢复时间，低值提升延迟表现，高温风险上升。", "偏激进" if t_rfc < rules["recommended_tRFC_floor"] else "正常"),
        _entry("tRFC2", t_rfc2, freq, "二级刷新恢复时间。"),
        _entry("tRFCsb", t_rfcsb, freq, "Same-bank 刷新恢复时间。"),
        _entry("tREFI", t_refi, freq, "刷新间隔，高值提升延迟表现，高温风险上升。", "高温敏感" if t_refi > 50000 else "正常"),
        _entry("tRRD_S", rrd_s, freq, "短行激活间隔。", "激进" if rrd_s <= 4 else "正常"),
        _entry("tRRD_L", rrd_l, freq, "长行激活间隔，Dual Rank 自动放宽。"),
        _entry("tFAW", t_faw, freq, "四激活窗口，已满足 tFAW >= 4 x tRRD_S。"),
        _entry("tWTR_S", 6, freq, "短写到读延迟。"),
        _entry("tWTR_L", 16, freq, "长写到读延迟。"),
    ]

    tertiary = [
        _entry("tRDRDSCL", 4 if config.tuning_style in {"Performance", "Benchmark"} else 6, freq, "读 SCL，影响延迟和稳定。"),
        _entry("tWRWRSCL", 4 if config.tuning_style in {"Performance", "Benchmark"} else 6, freq, "写 SCL，影响延迟和稳定。"),
        _entry("tRDRDSD", 6 if is_dual_rank(config) else 4, freq, "读同 DIMM 不同 Rank，Dual Rank 自动放宽。"),
        _entry("tRDRDDD", 8 if is_four_dimm(config.kit) else 6, freq, "读不同 DIMM，4 DIMM 自动放宽。"),
        _entry("tWRWRSD", 6 if is_dual_rank(config) else 4, freq, "写同 DIMM 不同 Rank，Dual Rank 自动放宽。"),
        _entry("tWRWRDD", 8 if is_four_dimm(config.kit) else 6, freq, "写不同 DIMM，4 DIMM 自动放宽。"),
    ]

    voltages, voltage_warnings = calculate_voltages(config)
    risk_score, risk_level, risk_explanations = calculate_risk(config, voltages, secondary)

    warnings = list(voltage_warnings)
    if config.platform == "AMD AM5" and config.target_frequency >= 6400:
        warnings.append("AM5 6400+ 需要重点验证 UCLK=MCLK，失败时改用分频或降低频率。")
    if is_four_dimm(config.kit):
        warnings.append("4 DIMM 配置训练压力高，已自动提高风险并放宽部分时序。")
    if config.temperature_limit > 55:
        warnings.append("目标温度高于 55°C，建议优先降压、增加风扇、降低 tREFI。")

    return RecommendationResult(
        config=config,
        frequency=_frequency_block(config),
        primary=primary,
        secondary=secondary,
        tertiary=tertiary,
        voltages=voltages,
        risk_score=risk_score,
        risk_level=risk_level,
        risk_explanations=risk_explanations,
        stability_steps=STABILITY_STEPS,
        tuning_advice=BASE_TUNING_ADVICE,
        warnings=warnings,
    )


def recommendation_to_bios_fields(result: RecommendationResult) -> dict[str, str]:
    fields: dict[str, str] = {}
    config = result.config
    fields["Memory Frequency"] = str(config.target_frequency)
    fields["MCLK"] = str(config.target_frequency // 2)
    if config.platform == "AMD AM5":
        fields["UCLK"] = str(config.target_frequency // 2)
        fields["FCLK"] = "2000" if config.target_frequency <= 6000 else "2066" if config.target_frequency <= 6200 else "2133"
    else:
        fields["UCLK"] = "Auto"
        fields["FCLK"] = "Auto"

    for entry in result.primary + result.secondary + result.tertiary:
        fields[entry.name] = str(entry.cycles)
    for voltage in result.voltages:
        name = "CPU VDDIO" if voltage.name == "CPU VDDIO / VDDIO MEM" else voltage.name
        fields[name] = voltage.value

    fields.setdefault("tRDWR", "Auto")
    fields.setdefault("tWRRD", "Auto")
    fields.setdefault("VDDP", "Auto / 1.05V")
    fields.setdefault("VPP", "Auto / 1.80V")
    return fields


def calculate_bios_parameters(config: InputConfig) -> tuple[RecommendationResult, dict[str, str]]:
    result = calculate_recommendation(config)
    return result, recommendation_to_bios_fields(result)
