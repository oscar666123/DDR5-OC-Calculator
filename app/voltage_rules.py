from __future__ import annotations

from app.models import InputConfig, VoltageEntry


def _strategy_delta(strategy: str) -> float:
    return {"保守": -0.03, "正常": 0.0, "激进": 0.03}.get(strategy, 0.0)


def _style_delta(style: str) -> float:
    return {"Safe": -0.03, "Daily": 0.0, "Performance": 0.03, "Benchmark": 0.07}.get(style, 0.0)


def _format_v(value: float) -> str:
    return f"{value:.2f}V"


def _voltage_risk(value: float, warning: float, high: float) -> str:
    if value > high:
        return "高风险"
    if value > warning:
        return "偏高"
    return "正常"


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


def calculate_am5_cpu_voltages(
    cpu_name: str,
    target_frequency: int,
    kit: str,
    rank: str,
    cooling: str,
    voltage_policy: str,
) -> dict[str, object]:
    if target_frequency <= 5600:
        vsoc = 1.15
        vddio = 1.23
    elif target_frequency <= 6000:
        vsoc = 1.25 if "9700X" in cpu_name.upper() and kit == "2x32GB" else 1.22
        vddio = 1.30 if kit == "2x32GB" else 1.28
    elif target_frequency <= 6200:
        vsoc = 1.25
        vddio = 1.35 if kit == "2x32GB" else 1.32
    elif target_frequency <= 6400:
        vsoc = 1.28
        vddio = 1.38 if kit == "2x32GB" else 1.36
    else:
        vsoc = 1.30
        vddio = 1.40

    if kit == "2x32GB" and rank == "Dual Rank" and target_frequency < 6000:
        vddio += 0.03
    if voltage_policy == "保守":
        vddio -= 0.03
    elif voltage_policy == "激进":
        vddio += 0.02
        if target_frequency >= 6400:
            vsoc = 1.30

    if cooling == "无风扇":
        vddio = min(vddio, 1.35)
    vsoc = min(vsoc, 1.30)

    risk = {
        "VSOC": _voltage_risk(vsoc, 1.25, 1.30),
        "CPU VDDIO": _voltage_risk(vddio, 1.35, 1.40),
        "VDDP": "正常",
        "VDDG CCD": "正常",
        "VDDG IOD": "正常",
    }
    reasons: list[str] = []
    if vsoc >= 1.30:
        reasons.append("VSOC at 1.30V is the AM5 hard ceiling.")
    if target_frequency >= 6600 and kit == "2x32GB":
        reasons.append("6600+ is high risk for AM5 2x32GB daily use.")
    return {
        "VSOC": _format_v(vsoc),
        "CPU VDDIO": _format_v(vddio),
        "VDDP": "Auto / 1.05V",
        "VDDG CCD": "Auto",
        "VDDG IOD": "Auto",
        "risk": risk,
        "reasons": reasons,
    }


def calculate_hynix_adie_2x32_voltages(config: InputConfig) -> tuple[list[VoltageEntry], list[str]]:
    warnings: list[str] = []
    freq = config.target_frequency

    if config.platform == "AMD AM5":
        if freq <= 5600:
            dram = 1.33
        elif freq <= 6000:
            dram = 1.38
        elif freq <= 6200:
            dram = 1.40
        else:
            dram = 1.42

        if config.voltage_strategy == "保守":
            dram -= 0.02
        elif config.voltage_strategy == "激进" and freq >= 6400:
            dram += 0.03
        if config.tuning_style == "Safe":
            dram -= 0.02
        if config.cooling == "无风扇":
            dram = min(dram, 1.40)
        elif config.cooling == "机箱风道":
            dram = min(dram, 1.42 if freq >= 6400 else 1.40)
        else:
            dram = min(dram, 1.45)

        cpu_voltages = calculate_am5_cpu_voltages(
            config.cpu_model,
            freq,
            config.kit,
            config.rank,
            config.cooling,
            config.voltage_strategy,
        )
        warnings.extend(str(reason) for reason in cpu_voltages["reasons"])
        cpu_risk = cpu_voltages["risk"]

        entries = [
            VoltageEntry("DRAM VDD", _format_v(dram), "2x32GB A-die：6000 1.38V，6200 1.40V，6400 1.42V 起步。", _voltage_risk(dram, 1.40, 1.45)),
            VoltageEntry("DRAM VDDQ", _format_v(dram), "通常跟随 DRAM VDD。", _voltage_risk(dram, 1.40, 1.45)),
            VoltageEntry("CPU VDDIO / VDDIO MEM", str(cpu_voltages["CPU VDDIO"]), "影响 CPU 内存 I/O 和训练稳定性。", str(cpu_risk["CPU VDDIO"])),
            VoltageEntry("VSOC", str(cpu_voltages["VSOC"]), "AM5 日用推荐 1.20-1.25V，程序硬上限 1.30V。", str(cpu_risk["VSOC"])),
            VoltageEntry("VDDP", str(cpu_voltages["VDDP"]), "PHY / 内存训练相关电压，默认 Auto / 1.05V。", str(cpu_risk["VDDP"])),
            VoltageEntry("VDDG CCD", str(cpu_voltages["VDDG CCD"]), "Fabric / CCD 相关电压，新手优先 Auto。", str(cpu_risk["VDDG CCD"])),
            VoltageEntry("VDDG IOD", str(cpu_voltages["VDDG IOD"]), "Fabric / IOD 相关电压，新手优先 Auto。", str(cpu_risk["VDDG IOD"])),
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
