# DDR5 OC Calculator

Windows 本地 DDR5 内存超频计算器，面向 SK hynix DDR5 A-die / M-die。程序读取 Windows WMI/CIM 硬件信息，并把推荐 BIOS 参数直接填入可编辑输入框。

## 功能

- PySide6 桌面界面
- 启动后自动读取 CPU、主板、BIOS、内存容量和当前内存频率
- 支持导入 ZenTimings OCR 文本、TXT、CSV、JSON
- BIOS 参数编辑器布局，每个参数都可手动覆盖
- 主时序、副时序、三时序、电压建议
- 顶部风险状态条
- 底部简短测试建议
- 复制当前参数框
- 导出 TXT / JSON
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

运行回归测试：

```bat
python -m unittest discover -s tests -v
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

v0.4.0 发布包文件名为 `release\DDR5OCCalculator-v0.4.0-windows-x64.zip`。

## 自动读取

程序使用 PowerShell `Get-CimInstance` 读取：

- `Win32_Processor`
- `Win32_BaseBoard`
- `Win32_BIOS`
- `Win32_PhysicalMemory`

读取失败时，顶部字段会显示“自动读取失败，可手动填写”。平台、套条、目标频率和 IC Profile 均可手动选择。Part Number 推断失败会进入 `Unknown / Manual Selection`，人工确认 IC 后才允许计算专用 profile。

## ZenTimings 导入

“导入 ZenTimings”支持 OCR 文本、TXT、CSV、JSON 和图片。图片 OCR 需要安装 Pillow、pytesseract 与本机 Tesseract，并将导入值标记为 `ZenTimings` 来源。6200+ 的 2x32GB AM5 方案会把“散热已确认”纳入风险提示；该勾选表示人工确认风道和温度条件。

## 支持范围

- Hynix 16Gb A-die
- Hynix 16Gb A-die 2x32GB Dual Rank
- Hynix 16Gb M-die
- Hynix 24Gb M-die
- AMD AM5
- Intel DDR5

`2x32GB + 16Gb A-die` 会自动切换到 `Hynix 16Gb A-die 2x32GB Dual Rank` profile。AM5 2x32GB A-die 建议从 `6000 Daily` 开始测试。

## AM5 电压逻辑

AM5 CPU 相关电压会按目标频率、套条容量、Rank、散热和电压策略计算：

- 6000 Daily：VSOC 1.25V，CPU VDDIO 1.30V
- 6200 Performance：VSOC 1.25V，CPU VDDIO 1.35V
- 6400 High Risk：VSOC 1.28V，CPU VDDIO 1.38V
- VDDP 默认 `Auto / 1.05V`
- VDDG CCD / VDDG IOD 默认 `Auto`
- VSOC 程序硬上限为 1.30V

VSOC 高于 1.30V 会标红并提示高风险。无主动内存风扇时，DRAM VDD / VDDQ 不会自动推荐超过 1.40V。2x32GB A-die 推荐先测试 6000 Daily。

## 复制格式

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

## 使用建议

2x32GB Dual Rank 优先关注 tRFC、tREFI 和温度。6200 需要更好 IMC，6400 属于高风险。出错时优先回退 tRFC、tREFI、VDDIO、VSOC。

程序会区分 `requested_frequency` 与 `effective_frequency`。AM5 2x32GB 目标超过 6400 时，状态栏会显示实际回退目标，例如 `6600 -> 6200`。

导入的 ZenTimings 当前值会在“测试建议”页保留为只读对照区，计算出的 BIOS 推荐值继续显示在参数编辑框中。

## 作者

GitHub: [@oscar666123](https://github.com/oscar666123)
