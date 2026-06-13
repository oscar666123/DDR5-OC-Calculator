from __future__ import annotations

import json
import subprocess
from typing import Any

from app.models import HardwareInfo, MemoryModuleInfo


def _run_powershell(script: str) -> tuple[Any | None, str]:
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        f"{script} | ConvertTo-Json -Depth 4",
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=12, check=False)
    except Exception as exc:
        return None, str(exc)
    if completed.returncode != 0:
        return None, completed.stderr.strip() or "PowerShell command failed"
    text = completed.stdout.strip()
    if not text:
        return None, "PowerShell returned empty output"
    try:
        return json.loads(text), ""
    except json.JSONDecodeError as exc:
        return None, str(exc)


def _listify(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _capacity_gb(bytes_value: Any) -> int:
    value = _int_value(bytes_value)
    if value <= 0:
        return 0
    return round(value / 1024 / 1024 / 1024)


def _memory_type_name(value: Any) -> str:
    code = _int_value(value)
    if code == 34:
        return "DDR5"
    if code == 26:
        return "DDR4"
    return str(value or "")


def _summarize_memory(modules: list[MemoryModuleInfo]) -> tuple[int, int, int, str, bool]:
    count = len([module for module in modules if module.capacity_gb > 0])
    total = sum(module.capacity_gb for module in modules)
    module_capacity = modules[0].capacity_gb if modules else 0
    configured = max((module.configured_speed for module in modules), default=0)
    kit = f"{count}x{module_capacity}GB" if count and module_capacity else ""
    is_ddr5 = any(module.memory_type == "DDR5" for module in modules)
    return count, total, module_capacity, kit, is_ddr5 if modules else False


def read_system_hardware() -> HardwareInfo:
    info = HardwareInfo()
    errors: list[str] = []

    cpu_data, error = _run_powershell(
        "Get-CimInstance Win32_Processor | Select-Object Name,Manufacturer,MaxClockSpeed,NumberOfCores,NumberOfLogicalProcessors"
    )
    if error:
        errors.append(f"CPU: {error}")
    elif cpu_data:
        cpu = _listify(cpu_data)[0]
        info.cpu_name = str(cpu.get("Name", "")).strip()
        info.cpu_vendor = str(cpu.get("Manufacturer", "")).strip()
        info.cpu_max_clock = _int_value(cpu.get("MaxClockSpeed"))
        info.cpu_cores = _int_value(cpu.get("NumberOfCores"))
        info.cpu_threads = _int_value(cpu.get("NumberOfLogicalProcessors"))

    board_data, error = _run_powershell(
        "Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer,Product,Version,SerialNumber"
    )
    if error:
        errors.append(f"Board: {error}")
    elif board_data:
        board = _listify(board_data)[0]
        info.motherboard_manufacturer = str(board.get("Manufacturer", "")).strip()
        info.motherboard_product = str(board.get("Product", "")).strip()
        info.motherboard_version = str(board.get("Version", "")).strip()

    bios_data, error = _run_powershell(
        "Get-CimInstance Win32_BIOS | Select-Object Manufacturer,SMBIOSBIOSVersion,ReleaseDate"
    )
    if error:
        errors.append(f"BIOS: {error}")
    elif bios_data:
        bios = _listify(bios_data)[0]
        info.bios_manufacturer = str(bios.get("Manufacturer", "")).strip()
        info.bios_version = str(bios.get("SMBIOSBIOSVersion", "")).strip()
        info.bios_release_date = str(bios.get("ReleaseDate", "")).strip()

    memory_data, error = _run_powershell(
        "Get-CimInstance Win32_PhysicalMemory | Select-Object BankLabel,DeviceLocator,Manufacturer,PartNumber,Capacity,Speed,ConfiguredClockSpeed,SMBIOSMemoryType,FormFactor,DataWidth,TotalWidth,SerialNumber"
    )
    if error:
        errors.append(f"Memory: {error}")
    else:
        modules: list[MemoryModuleInfo] = []
        for item in _listify(memory_data):
            modules.append(
                MemoryModuleInfo(
                    slot=str(item.get("DeviceLocator", "")).strip(),
                    bank=str(item.get("BankLabel", "")).strip(),
                    memory_manufacturer=str(item.get("Manufacturer", "")).strip(),
                    part_number=str(item.get("PartNumber", "")).strip(),
                    capacity_gb=_capacity_gb(item.get("Capacity")),
                    speed=_int_value(item.get("Speed")),
                    configured_speed=_int_value(item.get("ConfiguredClockSpeed")),
                    memory_type=_memory_type_name(item.get("SMBIOSMemoryType")),
                    form_factor=str(item.get("FormFactor", "")).strip(),
                    data_width=_int_value(item.get("DataWidth")),
                    total_width=_int_value(item.get("TotalWidth")),
                    serial_number=str(item.get("SerialNumber", "")).strip(),
                )
            )
        info.memory_modules = modules
        count, total, module_capacity, kit, is_ddr5 = _summarize_memory(modules)
        info.memory_module_count = count
        info.total_capacity_gb = total
        info.module_capacity_gb = module_capacity
        info.configured_speed = max((module.configured_speed for module in modules), default=0)
        info.kit_type = kit
        info.is_ddr5 = is_ddr5

    info.detection_error = "; ".join(errors)
    return info
