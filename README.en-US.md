# DDR5 OC Calculator

A local Windows desktop DDR5 overclocking calculator for SK hynix DDR5 A-die / M-die. It reads Windows WMI/CIM hardware information and fills editable BIOS parameter fields directly.

## Features

- PySide6 desktop GUI
- Automatic CPU, motherboard, BIOS, memory capacity, and configured memory speed detection on startup
- ZenTimings OCR text, TXT, CSV, and JSON import
- BIOS parameter editor layout with manually editable fields
- Primary, secondary, and tertiary timing recommendations
- Voltage recommendations
- Compact top risk status bar
- Short bottom testing advice
- Copy current BIOS parameter fields
- Export TXT / JSON
- Save and load JSON configs
- PyInstaller Windows executable packaging

## Run From Source

```bat
cd ddr5_oc_calculator
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

Run regression tests:

```bat
python -m unittest discover -s tests -v
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

The v0.4.0 release package is `release\DDR5OCCalculator-v0.4.0-windows-x64.zip`.

## Automatic Detection

The app uses PowerShell `Get-CimInstance` to read:

- `Win32_Processor`
- `Win32_BaseBoard`
- `Win32_BIOS`
- `Win32_PhysicalMemory`

If detection fails, the top fields show fallback text and remain manually editable. Platform, kit type, target frequency, and IC profile can be selected manually. A Part Number miss enters `Unknown / Manual Selection`, and manual IC confirmation is required before a dedicated profile can be calculated.

## ZenTimings Import

The “Import ZenTimings” action accepts OCR text, TXT, CSV, JSON, and images. Image OCR requires Pillow, pytesseract, and a local Tesseract installation. Imported fields receive a `ZenTimings` source marker. For AM5 2x32GB targets at 6200+, the `Thermal confirmed` checkbox contributes to the risk notice and records manual confirmation of airflow and temperature conditions.

## Supported Scope

- Hynix 16Gb A-die
- Hynix 16Gb A-die 2x32GB Dual Rank
- Hynix 16Gb M-die
- Hynix 24Gb M-die
- AMD AM5
- Intel DDR5

`2x32GB + 16Gb A-die` automatically switches to the `Hynix 16Gb A-die 2x32GB Dual Rank` profile. For AM5 2x32GB A-die, start with `6000 Daily`.

## AM5 Voltage Logic

AM5 CPU-related voltages are calculated from target frequency, kit capacity, rank, cooling, and voltage policy:

- 6000 Daily: VSOC 1.25V, CPU VDDIO 1.30V
- 6200 Performance: VSOC 1.25V, CPU VDDIO 1.35V
- 6400 High Risk: VSOC 1.28V, CPU VDDIO 1.38V
- VDDP defaults to `Auto / 1.05V`
- VDDG CCD / VDDG IOD default to `Auto`
- VSOC has a program hard ceiling of 1.30V

VSOC above 1.30V is marked red as high risk. Without active DIMM airflow, DRAM VDD / VDDQ are capped at 1.40V for automatic recommendations. For 2x32GB A-die, start with 6000 Daily.

## Copy Format

```text
Memory Frequency = 6000
MCLK = 3000
UCLK = 3000
FCLK = 2000

tCL = 30
tRCD = 38
tRP = 38
tRAS = 50

DRAM VDD = 1.38V
VSOC = 1.25V
```

## Recommendation

For 2x32GB Dual Rank, focus on tRFC, tREFI, and DIMM temperature. 6200 requires a stronger IMC, and 6400 is high risk. Roll back tRFC, tREFI, VDDIO, and VSOC first when errors appear.

The application separates `requested_frequency` from `effective_frequency`. AM5 2x32GB targets above 6400 roll back to a supported target, and the status bar shows the transition such as `6600 -> 6200`.

Imported ZenTimings current values remain in a read-only comparison area on the Test Advice tab while calculated BIOS recommendations remain in the editable parameter fields.

## Author

GitHub: [@oscar666123](https://github.com/oscar666123)
