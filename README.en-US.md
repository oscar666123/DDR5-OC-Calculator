# DDR5 OC Calculator

A local Windows desktop DDR5 overclocking calculator for SK hynix DDR5 A-die / M-die. It generates BIOS memory tuning suggestions from the selected platform, IC, capacity, rank, target frequency, cooling condition, and voltage strategy.

## Features

- PySide6 desktop GUI
- Primary, secondary, and tertiary timing recommendations
- Voltage recommendations
- Timing cycles and ns latency display
- Risk score, risk explanation, and stability test flow
- Copy BIOS parameters
- Export TXT result
- Save and load JSON profiles
- PyInstaller Windows executable packaging

## Run From Source

```bat
cd ddr5_oc_calculator
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

## Build

```bat
cd ddr5_oc_calculator
build_exe.bat
```

Build outputs:

```text
dist\DDR5OCCalculator\DDR5OCCalculator.exe
release\DDR5OCCalculator-windows-x64.zip
```

## Supported Scope

- Hynix 16Gb A-die
- Hynix 16Gb A-die 2x32GB Dual Rank
- Hynix 16Gb M-die
- Hynix 24Gb M-die
- AMD AM5
- Intel DDR5

4-DIMM, dual-rank, and double-sided configurations automatically increase risk and relax selected timings. High-temperature profiles reduce tREFI, increase tRFC, and emit warnings.

## 2x32GB A-die Profile

Selecting `Hynix 16Gb A-die 2x32GB Dual Rank`, or selecting `2x32GB + 16Gb A-die`, enables the dedicated profile:

- Total capacity: 64GB
- Module capacity: 32GB
- Rank: Dual Rank
- Side: Double Sided
- IC density: 16Gb
- Profile type: 1DPC 2 DIMM
- AM5 daily target: 6000 MT/s

This profile uses a dedicated tRFC, tREFI, tRRD_L, tFAW, and SD/DD tertiary timing model. AM5 6200/6400 are treated as advanced and high-risk profiles. AM5 targets above 6400 are automatically rolled back to 6200. `4x32GB + A-die` enters a high-risk profile and rolls back to a 5600 Safe-style target.

`app/reference_notes.py` stores reference notes and usage guidance for profiles. These notes are descriptive program context. Stability still depends on local CPU IMC quality, motherboard BIOS, memory cooling, and real stress testing.

## Recommendation

For AM5 2x32GB A-die, start with `6000 Daily`. Treat 6200/6400 as validation targets requiring CPU IMC, BIOS, and DIMM cooling support.
