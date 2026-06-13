# DDR5 OC Calculator

Windows 本地 DDR5 内存超频计算器，面向 SK hynix DDR5 A-die / M-die。程序根据平台、颗粒、容量、Rank、目标频率、散热和电压策略生成 BIOS 参数建议。

## 功能

- PySide6 桌面界面
- 主时序、副时序、三时序、电压建议
- cycles 与 ns 延迟同时显示
- 风险评分、风险解释、稳定性测试流程
- 复制 BIOS 参数
- 导出 TXT
- 保存 / 读取 JSON 配置
- PyInstaller 打包 Windows 可执行程序

## 运行源码

```bat
cd ddr5_oc_calculator
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

## 打包

```bat
cd ddr5_oc_calculator
build_exe.bat
```

打包产物：

```text
dist\DDR5OCCalculator\DDR5OCCalculator.exe
release\DDR5OCCalculator-windows-x64.zip
```

## 支持范围

- Hynix 16Gb A-die
- Hynix 16Gb A-die 2x32GB Dual Rank
- Hynix 16Gb M-die
- Hynix 24Gb M-die
- AMD AM5
- Intel DDR5

4 DIMM、Dual Rank、双面内存会自动提高风险并放宽部分参数。AM5 6400+ 会提示验证 UCLK=MCLK，6600+ 会提高分频风险。高温场景会降低 tREFI、提高 tRFC，并在输出中给出警告。

## 2x32GB A-die Profile

选择 `Hynix 16Gb A-die 2x32GB Dual Rank`，或选择 `2x32GB + 16Gb A-die`，程序会自动切换到专用 profile：

- Total capacity: 64GB
- Module capacity: 32GB
- Rank: Dual Rank
- Side: Double Sided
- IC density: 16Gb
- Profile type: 1DPC 2 DIMM
- AM5 daily target: 6000 MT/s

该 profile 使用独立的 tRFC、tREFI、tRRD_L、tFAW 和 SD/DD 三时序模型。AM5 6200/6400 会按进阶和高风险路径处理，AM5 高于 6400 会自动回退到 6200。`4x32GB + A-die` 会进入高风险 profile，并自动降到 5600 Safe 思路。

`app/reference_notes.py` 记录每个 profile 的资料来源和使用说明。这些 notes 是程序说明资料，稳定性仍需按本机 CPU IMC、主板 BIOS、内存散热和实际测试结果验证。

## 使用建议

AM5 2x32GB A-die 建议从 `6000 Daily` 开始测试。6200/6400 需要 IMC、主板 BIOS 和内存散热共同支持。
