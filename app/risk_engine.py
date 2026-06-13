from __future__ import annotations

import re

from app.models import InputConfig, TimingEntry, VoltageEntry
from app.validators import is_dual_rank, is_four_dimm, is_hynix_adie_2x32_profile, is_hynix_adie_4x32_profile


def _voltage_float(value: str) -> float | None:
    match = re.search(r"(\d+\.\d+)", value)
    if match:
        return float(match.group(1))
    return None


def _risk_level(score: int) -> str:
    if score <= 25:
        return "Safe"
    if score <= 50:
        return "Daily"
    if score <= 75:
        return "Performance"
    return "Benchmark / High Risk"


def _timing_value(timings: list[TimingEntry], name: str) -> int | None:
    for timing in timings:
        if timing.name == name:
            return timing.cycles
    return None


def dual_rank_capacity_risk(config: InputConfig) -> tuple[int, list[str]]:
    score = 0
    explanations: list[str] = []
    if is_hynix_adie_2x32_profile(config):
        score += 10
        explanations.append("2x32GB A-die Dual Rank 按大容量日用验证 profile 计入基础风险。")
        score += 8
        explanations.append("64GB 2x32GB 容量增加训练压力和 refresh 敏感度。")
        if config.target_frequency >= 6200:
            score += 10
            explanations.append("2x32GB A-die 6200+ 属于进阶调校区间。")
        if config.target_frequency >= 6400:
            score += 25
            explanations.append("AM5 2x32GB A-die 6400 属于高风险区间，需要 IMC、BIOS 和主动散热共同支持。")
    if is_hynix_adie_4x32_profile(config):
        score += 30
        explanations.append("4x32GB 配置属于高训练压力 profile，推荐 5200-5600 Safe 区间。")
    if config.rgb_memory and (is_hynix_adie_2x32_profile(config) or is_hynix_adie_4x32_profile(config)):
        score += 5
        explanations.append("RGB 内存通常带来更高温度和 refresh 风险。")
    return score, explanations


def thermal_refresh_risk(
    config: InputConfig,
    voltages: list[VoltageEntry],
    secondary_timings: list[TimingEntry],
) -> tuple[int, list[str]]:
    score = 0
    explanations: list[str] = []
    t_refi = _timing_value(secondary_timings, "tREFI")
    t_rfc = _timing_value(secondary_timings, "tRFC")
    t_faw = _timing_value(secondary_timings, "tFAW")
    t_rrd_l = _timing_value(secondary_timings, "tRRD_L")
    dram_vdd = None
    for voltage in voltages:
        if voltage.name == "DRAM VDD":
            dram_vdd = _voltage_float(voltage.value)

    if dram_vdd is not None and dram_vdd > 1.40 and config.cooling == "无风扇":
        score += 10
        explanations.append("无风扇且 DRAM VDD 高于 1.40V，温度和 refresh 风险上升。")
    if dram_vdd is not None and dram_vdd > 1.45:
        score += 20
        explanations.append("DRAM VDD 高于 1.45V，2x32GB A-die 日用风险显著上升。")
    if t_refi == 65535 and config.temperature_limit > 50:
        score += 15
        explanations.append("tREFI 65535 搭配 50°C 以上目标温度，热稳定风险显著上升。")
    if t_rfc is not None and config.target_frequency <= 6000 and t_rfc < 520:
        score += 15
        explanations.append("6000 MT/s 下 tRFC 低于 520，2x32GB A-die refresh 风险上升。")
    if t_rfc is not None and config.target_frequency == 6200 and t_rfc < 560:
        score += 15
        explanations.append("6200 MT/s 下 tRFC 低于 560，2x32GB A-die refresh 风险上升。")
    if t_faw is not None and t_faw < 24:
        score += 10
        explanations.append("tFAW 低于 24，Dual Rank 行激活风险上升。")
    if t_rrd_l is not None and t_rrd_l < 10:
        score += 10
        explanations.append("tRRD_L 低于 10，Dual Rank 长行激活风险上升。")
    return score, explanations


def cpu_voltage_risk(config: InputConfig, voltages: list[VoltageEntry]) -> tuple[int, list[str]]:
    score = 0
    explanations: list[str] = []
    values = {voltage.name: _voltage_float(voltage.value) for voltage in voltages}
    vddio = values.get("CPU VDDIO / VDDIO MEM") or values.get("CPU VDDIO")
    vsoc = values.get("VSOC")
    vddp = values.get("VDDP")
    vddg_ccd = values.get("VDDG CCD")
    vddg_iod = values.get("VDDG IOD")
    dram_vdd = values.get("DRAM VDD")

    if vsoc is not None and vsoc > 1.25:
        score += 8
        explanations.append("VSOC 高于 1.25V，AM5 日用风险上升。")
    if vsoc is not None and vsoc > 1.30:
        score += 30
        explanations.append("VSOC above 1.30V is high risk on AM5. Use 1.20-1.25V for daily.")
    if vddio is not None and vddio > 1.35:
        score += 10
        explanations.append("CPU VDDIO 高于 1.35V，IMC 和温度风险上升。")
    if vddio is not None and vddio > 1.40:
        score += 20
        explanations.append("CPU VDDIO 高于 1.40V，属于高风险范围。")
    if vddp is not None and vddp > 1.10:
        score += 10
        explanations.append("VDDP 高于 1.10V，建议回到 Auto 或 0.95-1.05V。")
    if vddg_ccd is not None and vddg_ccd > 1.10:
        score += 10
        explanations.append("VDDG CCD 高于 1.10V，Fabric 稳定风险上升。")
    if vddg_iod is not None and vddg_iod > 1.10:
        score += 10
        explanations.append("VDDG IOD 高于 1.10V，IOD 稳定风险上升。")
    if config.target_frequency >= 6400 and is_dual_rank(config) and config.kit == "2x32GB":
        score += 25
        explanations.append("Target 6400 + 2x32GB Dual Rank 需要更强 IMC、BIOS 和散热。")
    elif config.target_frequency >= 6200 and is_dual_rank(config) and config.kit == "2x32GB":
        score += 10
        explanations.append("Target 6200 + 2x32GB Dual Rank 属于进阶验证。")
    if dram_vdd is not None and config.cooling == "无风扇" and dram_vdd > 1.40:
        score += 10
        explanations.append("无主动内存风扇且 DRAM VDD 高于 1.40V。")
    return score, explanations


def calculate_risk(
    config: InputConfig,
    voltages: list[VoltageEntry],
    secondary_timings: list[TimingEntry],
) -> tuple[int, str, list[str]]:
    score = 0
    explanations: list[str] = []

    if config.platform == "AMD AM5":
        score += max(0, int((config.target_frequency - 5600) / 50))
        if config.target_frequency >= 6400:
            explanations.append("AM5 6400+ 对 IMC、主板布线和 UCLK 稳定性要求更高。")
        if config.target_frequency >= 6600:
            score += 15
            explanations.append("AM5 6600+ 可能需要 UCLK 分频。")
    else:
        score += max(0, int((config.target_frequency - 6000) / 55))
        if config.target_frequency >= 7600:
            explanations.append("Intel 7600+ 更依赖高端主板和 IMC 体质。")
        if config.target_frequency >= 8000:
            score += 15
            explanations.append("8000+ 属于 Benchmark 高风险区间。")

    style_risk = {"Safe": -10, "Daily": 0, "Performance": 10, "Benchmark": 25}.get(config.tuning_style, 0)
    score += style_risk
    if config.tuning_style in {"Performance", "Benchmark"}:
        explanations.append(f"{config.tuning_style} 风格会采用更紧时序和更高电压。")

    if is_dual_rank(config):
        score += 10
        explanations.append("Dual Rank 已增加刷新、行激活和三时序风险权重。")
    if is_four_dimm(config.kit):
        score += 25
        explanations.append("4 DIMM 配置训练和高频稳定性压力显著上升。")

    for voltage in voltages:
        value = _voltage_float(voltage.value)
        if value is None:
            continue
        if voltage.name in {"DRAM VDD", "DRAM VDDQ"} and value > 1.45:
            score += 15
            explanations.append(f"{voltage.name} 高于 1.45V。")
        if voltage.name == "VSOC" and value > 1.30:
            score += 20
            explanations.append("VSOC 高于 1.30V。")

    voltage_score, voltage_explanations = cpu_voltage_risk(config, voltages)
    score += voltage_score
    explanations.extend(voltage_explanations)

    if config.temperature_limit > 50:
        score += 15
        explanations.append("目标温度高于 50°C，refresh 稳定性风险上升。")

    for timing in secondary_timings:
        if timing.name == "tRFC" and timing.risk == "偏激进":
            score += 10
            explanations.append("tRFC 低于当前颗粒推荐保守下限。")
        if timing.name == "tREFI" and timing.cycles > 50000 and config.temperature_limit >= 50:
            score += 10
            explanations.append("tREFI 高且温度目标偏高。")
        if timing.name in {"tRRD_S", "tFAW"} and timing.risk == "激进":
            score += 10
            explanations.append("tRRD/tFAW 设置偏激进。")

    if is_hynix_adie_2x32_profile(config) or is_hynix_adie_4x32_profile(config):
        extra_score, extra_explanations = dual_rank_capacity_risk(config)
        score += extra_score
        explanations.extend(extra_explanations)
        refresh_score, refresh_explanations = thermal_refresh_risk(config, voltages, secondary_timings)
        score += refresh_score
        explanations.extend(refresh_explanations)

    score = max(0, min(100, score))
    if not explanations:
        explanations.append("频率、电压、温度和 Rank 组合处于低风险区间。")
    return score, _risk_level(score), explanations


def summarize_risk(score: int, level: str, explanations: list[str]) -> dict[str, object]:
    return {
        "score": score,
        "level": level,
        "reason": explanations[0] if explanations else "当前参数处于可测试区间。",
        "reasons": explanations[:5],
    }
