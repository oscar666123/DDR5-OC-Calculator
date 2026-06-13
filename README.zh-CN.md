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

## 自动读取

程序使用 PowerShell `Get-CimInstance` 读取：

- `Win32_Processor`
- `Win32_BaseBoard`
- `Win32_BIOS`
- `Win32_PhysicalMemory`

读取失败时，顶部字段会显示“自动读取失败，可手动填写”。平台、套条、目标频率和 IC Profile 均可手动选择。

## ZenTimings 导入

“导入 ZenTimings”支持 OCR 文本、TXT、CSV、JSON。程序会识别 MCLK、UCLK、FCLK、主时序、副时序和电压字段，并直接填入对应参数框。

## 支持范围

- Hynix 16Gb A-die
- Hynix 16Gb A-die 2x32GB Dual Rank
- Hynix 16Gb M-die
- Hynix 24Gb M-die
- AMD AM5
- Intel DDR5

`2x32GB + 16Gb A-die` 会自动切换到 `Hynix 16Gb A-die 2x32GB Dual Rank` profile。AM5 2x32GB A-die 建议从 `6000 Daily` 开始测试。

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
