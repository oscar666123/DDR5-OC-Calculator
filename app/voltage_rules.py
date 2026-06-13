from __future__ import annotations

from app.models import InputConfig, VoltageEntry


def _strategy_delta(strategy: str) -> float:
    return {"保守": -0.03, "正常": 0.0, "激进": 0.03}.get(strategy, 0.0)


def _style_delta(style: str) -> float:
    return {"Safe": -0.03, "Daily": 0.0, "Performance": 0.03, "Benchmark": 0.07}.get(style, 0.0)


def _format_v(value: float) -> str:
    return f"{value:.2f}V"


def _cooling_cap(config: InputConfig) -> float:
    if config.cooling == "无风扇":
        return 1.40
    if config.cooling == "机箱风道":
        return 1.45
    return 1.50


def apply_thermal_voltage_limit(config: InputConfig, voltage: float) -> tuple[float, list[str]]:
    warnings: list[str] = []
    cap = _cooling_cap(config)
    if config.cooling == "无风扇" and config.voltage_strategy == "激进":
        cap = min(cap, 1.40)
        warnings.append("无风扇搭配激进电压策略时，DRAM VDD/VDDQ 已按 1.40V 上限处理。")
    if config.temperature_limit > 55:
        cap = min(cap, 1.40)
        warnings.append("目标温度高于 55°C，DRAM VDD/VDDQ 已按更保守上限处理。")
    if voltage > cap:
        warnings.append(f"{config.cooling} 下 VDD/VDDQ 已按 {cap:.2f}V 上限回退。")
    return min(voltage, cap), warnings


def _dram_base(config: InputConfig) -> float:
    freq = config.target_frequency
    if config.platform == "AMD AM5":
        if freq <= 6000:
            base = 1.38
        elif freq <= 6200:
            base = 1.40
        elif freq <= 6400:
            base = 1.43
        elif freq <= 6800:
            base = 1.47
        else:
            base = 1.50
    else:
        if freq <= 6800:
            base = 1.38
        elif freq <= 7200:
            base = 1.42
        elif freq <= 7600:
            base = 1.45
        else:
            base = 1.50
    if config.die_type == "24Gb M-die":
        base += 0.02
    return base


def calculate_voltages(config: InputConfig) -> tuple[list[VoltageEntry], list[str]]:
    warnings: list[str] = []
    base = _dram_base(config) + _strategy_delta(config.voltage_strategy) + _style_delta(config.tuning_style)
    cap = _cooling_cap(config)
    raw_vdd = base
    vdd = min(raw_vdd, cap)
    if raw_vdd > cap:
        warnings.append(f"{config.cooling} 下 VDD/VDDQ 已按 {cap:.2f}V 上限回退。")

    vddq = vdd
    if config.target_frequency >= 7000 or config.voltage_strategy == "激进":
        vddq = min(vdd + 0.03, cap)

    entries = [
        VoltageEntry("DRAM VDD", _format_v(vdd), "内存核心电压。", "高风险" if vdd >= 1.50 else "偏高" if vdd > 1.45 else "正常"),
        VoltageEntry("DRAM VDDQ", _format_v(vddq), "内存 I/O 电压，高频可比 VDD 高 0.02-0.05V。", "高风险" if vddq >= 1.50 else "偏高" if vddq > 1.45 else "正常"),
        VoltageEntry("VPP", "Auto / 1.80V", "普通用户保持 Auto 或 1.80V。", "正常"),
    ]

    if config.platform == "AMD AM5":
        if config.target_frequency <= 6000:
            vsoc = 1.22
            vddio = 1.32
        elif config.target_frequency <= 6400:
            vsoc = 1.27
            vddio = 1.36
        else:
            vsoc = 1.30
            vddio = 1.40
        vsoc += max(0.0, _strategy_delta(config.voltage_strategy))
        if vsoc > 1.30:
            warnings.append("AM5 日用 VSOC 建议上限 1.30V，已按 1.30V 输出。")
            vsoc = 1.30
        entries.extend(
            [
                VoltageEntry("VSOC", _format_v(vsoc), "AM5 内存控制器相关电压，日用建议 <= 1.30V。", "偏高" if vsoc >= 1.30 else "正常"),
                VoltageEntry("CPU VDDIO / VDDIO MEM", _format_v(vddio), "6000 常见 1.25-1.35V，6200-6400 常见 1.30-1.40V。", "正常"),
                VoltageEntry("VDDP", "Auto / 1.05V", "普通用户保持 Auto 或 1.05V。", "正常"),
            ]
        )
    else:
        if config.target_frequency <= 7000:
            cpu_vddq = 1.25
            vccsa = 1.20
            vdd2 = 1.30
        elif config.target_frequency <= 7600:
            cpu_vddq = 1.32
            vccsa = 1.25
            vdd2 = 1.38
        else:
            cpu_vddq = 1.38
            vccsa = 1.32
            vdd2 = 1.43
        entries.extend(
            [
                VoltageEntry("CPU VDDQ", _format_v(cpu_vddq), "Intel CPU I/O 电压。", "正常"),
                VoltageEntry("VCCSA", _format_v(vccsa), "System Agent 电压。", "偏高" if vccsa > 1.30 else "正常"),
                VoltageEntry("CPU VDD2 / IMC Voltage", _format_v(vdd2), "内存控制器电压。", "偏高" if vdd2 > 1.40 else "正常"),
            ]
        )

    if config.temperature_limit > 55:
        warnings.append("目标温度高于 55°C，电压建议应配合更保守 refresh 参数使用。")
    return entries, warnings


def calculate_hynix_adie_2x32_voltages(config: InputConfig) -> tuple[list[VoltageEntry], list[str]]:
    warnings: list[str] = []
    freq = config.target_frequency

    if config.platform == "AMD AM5":
        if freq <= 5600:
            dram = 1.33
            vddio = 1.25
            vsoc = 1.18
            vddp = "Auto / 0.95-1.05V"
        elif freq <= 6000:
            dram = 1.38
            vddio = 1.32
            vsoc = 1.23
            vddp = "Auto / 1.00-1.05V"
        elif freq <= 6200:
            dram = 1.41
            vddio = 1.36
            vsoc = 1.28
            vddp = "Auto / 1.00-1.05V"
        else:
            dram = 1.44
            vddio = 1.40
            vsoc = 1.30
            vddp = "Auto / 1.05V"

        dram += _strategy_delta(config.voltage_strategy)
        if config.tuning_style == "Safe":
            dram -= 0.02
        if config.tuning_style == "Benchmark":
            dram += 0.02
        dram, thermal_warnings = apply_thermal_voltage_limit(config, dram)
        warnings.extend(thermal_warnings)
        if vsoc > 1.30:
            warnings.append("VSOC 高于 1.30V 会显著提高 AM5 日用风险。")

        entries = [
            VoltageEntry("DRAM VDD", _format_v(dram), "2x32GB A-die 专用 DRAM 核心电压。", "偏高" if dram > 1.40 else "正常"),
            VoltageEntry("DRAM VDDQ", _format_v(dram), "2x32GB A-die 专用 DRAM I/O 电压。", "偏高" if dram > 1.40 else "正常"),
            VoltageEntry("CPU VDDIO / VDDIO MEM", _format_v(vddio), "AM5 2x32GB 训练和 IMC 稳定相关电压。", "偏高" if vddio > 1.40 else "正常"),
            VoltageEntry("VSOC", _format_v(vsoc), "AM5 2x32GB 日用建议控制在 1.30V 以内。", "偏高" if vsoc >= 1.30 else "正常"),
            VoltageEntry("VDDP", vddp, "普通用户保持 Auto 或按区间低端开始。", "正常"),
            VoltageEntry("VPP", "Auto / 1.80V", "普通用户保持 Auto 或 1.80V。", "正常"),
        ]
        return entries, warnings

    if freq <= 6400:
        dram = 1.38
        cpu_vddq = 1.25
        vccsa = 1.20
        vdd2 = 1.32
    elif freq <= 6800:
        dram = 1.42
        cpu_vddq = 1.32
        vccsa = 1.25
        vdd2 = 1.38
    elif freq <= 7200:
        dram = 1.45
        cpu_vddq = 1.36
        vccsa = 1.30
        vdd2 = 1.42
    else:
        dram = 1.48
        cpu_vddq = 1.40
        vccsa = 1.34
        vdd2 = 1.45

    dram += _strategy_delta(config.voltage_strategy)
    dram, thermal_warnings = apply_thermal_voltage_limit(config, dram)
    warnings.extend(thermal_warnings)
    entries = [
        VoltageEntry("DRAM VDD", _format_v(dram), "Intel 2x32GB A-die DRAM 核心电压。", "高风险" if dram > 1.45 else "偏高" if dram > 1.40 else "正常"),
        VoltageEntry("DRAM VDDQ", _format_v(dram), "Intel 2x32GB A-die DRAM I/O 电压。", "高风险" if dram > 1.45 else "偏高" if dram > 1.40 else "正常"),
        VoltageEntry("CPU VDDQ", _format_v(cpu_vddq), "Intel CPU I/O 电压。", "正常"),
        VoltageEntry("VCCSA", _format_v(vccsa), "System Agent 电压。", "偏高" if vccsa > 1.30 else "正常"),
        VoltageEntry("CPU VDD2 / IMC Voltage", _format_v(vdd2), "内存控制器电压。", "偏高" if vdd2 > 1.40 else "正常"),
        VoltageEntry("VPP", "Auto / 1.80V", "普通用户保持 Auto 或 1.80V。", "正常"),
    ]
    return entries, warnings
