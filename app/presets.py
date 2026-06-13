from __future__ import annotations

PLATFORMS = ["AMD AM5", "Intel DDR5"]
MEMORY_ICS = ["Hynix A-die", "Hynix 16Gb A-die 2x32GB Dual Rank", "Hynix M-die"]
DIE_TYPES = ["16Gb A-die", "16Gb M-die", "24Gb M-die"]
KITS = ["2x16GB", "2x24GB", "2x32GB", "4x16GB", "4x24GB", "4x32GB"]
DIMM_CAPACITIES = ["16GB", "24GB", "32GB"]
RANKS = ["Single Rank", "Dual Rank"]
SIDES = ["单面", "双面"]
TARGET_FREQUENCIES = ["5600", "6000", "6200", "6400", "6600", "6800", "7000", "7200", "7600", "8000+"]
TUNING_STYLES = ["Safe", "Daily", "Performance", "Benchmark"]
COOLING_OPTIONS = ["无风扇", "机箱风道", "内存直吹风扇"]
VOLTAGE_STRATEGIES = ["保守", "正常", "激进"]

STABILITY_STEPS = [
    "保存 BIOS Profile。",
    "进入系统后运行 OCCT Memory 30 分钟。",
    "运行 TM5 anta777 Extreme 或 1usmus。",
    "运行 y-cruncher VT3 / VST。",
    "运行 Karhu RAM Test 或 HCI Memtest。",
    "关机断电冷启动测试 3 次。",
    "运行游戏或实际负载 1-2 小时。",
]

BASE_TUNING_ADVICE = [
    "快速报错：提高 VDD/VDDQ，或放宽 tCL/tRCD/tRP。",
    "TM5 报错：放宽 tRFC、tRRD、tFAW。",
    "y-cruncher 报错：检查 VDDIO、VSOC、IMC 电压。",
    "冷启动失败：降低频率，放宽训练相关参数，提高 VDDIO 或 VSOC。",
    "高温后报错：降低 tREFI，提高 tRFC，降低电压，增加内存风扇。",
]

HYNIX_ADIE_2X32_AM5_PRESETS = {
    "Safe": {
        "frequency": 5600,
        "primary": {"tCL": 32, "tRCD": 38, "tRP": 38, "tRAS": 44},
        "secondary": {"tWR": 48, "tRTP": 12, "tRFC": 620, "tRFC2": 480, "tRFCsb": 380, "tRRD_S": 8, "tRRD_L": 12, "tFAW": 32, "tWTR_S": 6, "tWTR_L": 16},
        "tertiary": {"tRDRDSCL": 6, "tWRWRSCL": 6, "tRDRDSC": 1, "tWRWRSC": 1, "tRDRDSD": 8, "tRDRDDD": 8, "tWRWRSD": 10, "tWRWRDD": 10},
    },
    "Daily": {
        "frequency": 6000,
        "primary": {"tCL": 30, "tRCD": 38, "tRP": 38, "tRAS": 44},
        "secondary": {"tWR": 48, "tRTP": 12, "tRFC": 580, "tRFC2": 460, "tRFCsb": 360, "tRRD_S": 6, "tRRD_L": 10, "tFAW": 28, "tWTR_S": 6, "tWTR_L": 16},
        "tertiary": {"tRDRDSCL": 6, "tWRWRSCL": 6, "tRDRDSC": 1, "tWRWRSC": 1, "tRDRDSD": 8, "tRDRDDD": 8, "tWRWRSD": 10, "tWRWRDD": 10},
    },
    "Performance": {
        "frequency": 6200,
        "primary": {"tCL": 32, "tRCD": 40, "tRP": 40, "tRAS": 46},
        "secondary": {"tWR": 52, "tRTP": 12, "tRFC": 620, "tRFC2": 480, "tRFCsb": 380, "tRRD_S": 8, "tRRD_L": 12, "tFAW": 32, "tWTR_S": 6, "tWTR_L": 16},
        "tertiary": {"tRDRDSCL": 6, "tWRWRSCL": 6, "tRDRDSC": 1, "tWRWRSC": 1, "tRDRDSD": 8, "tRDRDDD": 8, "tWRWRSD": 10, "tWRWRDD": 10},
    },
    "Benchmark": {
        "frequency": 6400,
        "primary": {"tCL": 34, "tRCD": 42, "tRP": 42, "tRAS": 50},
        "secondary": {"tWR": 56, "tRTP": 12, "tRFC": 660, "tRFC2": 520, "tRFCsb": 420, "tRRD_S": 8, "tRRD_L": 12, "tFAW": 32, "tWTR_S": 6, "tWTR_L": 16},
        "tertiary": {"tRDRDSCL": 8, "tWRWRSCL": 8, "tRDRDSC": 1, "tWRWRSC": 1, "tRDRDSD": 8, "tRDRDDD": 8, "tWRWRSD": 10, "tWRWRDD": 10},
    },
}

HYNIX_ADIE_2X32_INTEL_PRESETS = {
    "Safe": {
        "frequency": 6400,
        "primary": {"tCL": 32, "tRCD": 40, "tRP": 40, "tRAS": 48},
        "secondary": {"tWR": 52, "tRTP": 12, "tRFC": 600, "tRFC2": 460, "tRFCsb": 360, "tRRD_S": 6, "tRRD_L": 10, "tFAW": 28, "tWTR_S": 6, "tWTR_L": 16},
        "tertiary": {"tRDRDSCL": 6, "tWRWRSCL": 6, "tRDRDSC": 1, "tWRWRSC": 1, "tRDRDSD": 8, "tRDRDDD": 8, "tWRWRSD": 10, "tWRWRDD": 10},
    },
    "Daily": {
        "frequency": 6400,
        "primary": {"tCL": 34, "tRCD": 42, "tRP": 42, "tRAS": 48},
        "secondary": {"tWR": 52, "tRTP": 12, "tRFC": 620, "tRFC2": 480, "tRFCsb": 380, "tRRD_S": 6, "tRRD_L": 10, "tFAW": 28, "tWTR_S": 6, "tWTR_L": 16},
        "tertiary": {"tRDRDSCL": 6, "tWRWRSCL": 6, "tRDRDSC": 1, "tWRWRSC": 1, "tRDRDSD": 8, "tRDRDDD": 8, "tWRWRSD": 10, "tWRWRDD": 10},
    },
    "Performance": {
        "frequency": 6800,
        "primary": {"tCL": 36, "tRCD": 44, "tRP": 44, "tRAS": 50},
        "secondary": {"tWR": 56, "tRTP": 12, "tRFC": 660, "tRFC2": 520, "tRFCsb": 420, "tRRD_S": 8, "tRRD_L": 12, "tFAW": 32, "tWTR_S": 6, "tWTR_L": 16},
        "tertiary": {"tRDRDSCL": 8, "tWRWRSCL": 8, "tRDRDSC": 1, "tWRWRSC": 1, "tRDRDSD": 8, "tRDRDDD": 8, "tWRWRSD": 10, "tWRWRDD": 10},
    },
    "Benchmark": {
        "frequency": 7200,
        "primary": {"tCL": 38, "tRCD": 46, "tRP": 46, "tRAS": 52},
        "secondary": {"tWR": 56, "tRTP": 12, "tRFC": 700, "tRFC2": 560, "tRFCsb": 440, "tRRD_S": 8, "tRRD_L": 12, "tFAW": 32, "tWTR_S": 6, "tWTR_L": 16},
        "tertiary": {"tRDRDSCL": 8, "tWRWRSCL": 8, "tRDRDSC": 1, "tWRWRSC": 1, "tRDRDSD": 10, "tRDRDDD": 10, "tWRWRSD": 12, "tWRWRDD": 12},
    },
}
