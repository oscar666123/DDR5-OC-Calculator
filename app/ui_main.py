from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.exporter import result_to_html, result_to_json_dict, result_to_text
from app.models import InputConfig, RecommendationResult
from app.presets import (
    COOLING_OPTIONS,
    DIE_TYPES,
    DIMM_CAPACITIES,
    KITS,
    MEMORY_ICS,
    PLATFORMS,
    RANKS,
    SIDES,
    TARGET_FREQUENCIES,
    TUNING_STYLES,
    VOLTAGE_STRATEGIES,
)
from app.timing_rules import calculate_recommendation
from app.validators import ValidationError, parse_frequency


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DDR5 内存超频计算器")
        self.resize(1180, 760)
        self.current_result: RecommendationResult | None = None
        self._build_ui()
        self.reset_inputs()

    def _combo(self, items: list[str]) -> QComboBox:
        combo = QComboBox()
        combo.addItems(items)
        return combo

    def _spin(self, minimum: int, maximum: int, value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setSingleStep(1)
        return spin

    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)

        left_panel = self._build_input_panel()
        right_panel = self._build_output_panel()
        root.addWidget(left_panel, 0)
        root.addWidget(right_panel, 1)

        self.setCentralWidget(central)

    def _build_input_panel(self) -> QWidget:
        self.platform = self._combo(PLATFORMS)
        self.cpu_model = QLineEdit()
        self.motherboard_model = QLineEdit()
        self.bios_version = QLineEdit()
        self.memory_ic = self._combo(MEMORY_ICS)
        self.die_type = self._combo(DIE_TYPES)
        self.kit = self._combo(KITS)
        self.dimm_capacity = self._combo(DIMM_CAPACITIES)
        self.rank = self._combo(RANKS)
        self.sides = self._combo(SIDES)
        self.xmp_frequency = self._spin(4000, 9000, 6000)
        self.xmp_tcl = self._spin(20, 80, 36)
        self.xmp_trcd = self._spin(20, 100, 36)
        self.xmp_trp = self._spin(20, 100, 36)
        self.xmp_tras = self._spin(20, 160, 76)
        self.target_frequency = self._combo(TARGET_FREQUENCIES)
        self.tuning_style = self._combo(TUNING_STYLES)
        self.cooling = self._combo(COOLING_OPTIONS)
        self.temperature_limit = self._spin(35, 80, 50)
        self.voltage_strategy = self._combo(VOLTAGE_STRATEGIES)
        self.rgb_memory = QCheckBox("RGB 内存")
        self.profile_label = QLabel("通用 DDR5 profile")
        self.profile_label.setStyleSheet("padding: 6px; background: #eef3f8; border: 1px solid #c8d3df;")

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.addRow("平台", self.platform)
        form.addRow("CPU 型号", self.cpu_model)
        form.addRow("主板型号", self.motherboard_model)
        form.addRow("BIOS 版本", self.bios_version)
        form.addRow("内存颗粒", self.memory_ic)
        form.addRow("颗粒容量类型", self.die_type)
        form.addRow("套条组合", self.kit)
        form.addRow("单条容量", self.dimm_capacity)
        form.addRow("Rank", self.rank)
        form.addRow("面数", self.sides)
        form.addRow("当前 XMP/EXPO 频率", self.xmp_frequency)
        form.addRow("XMP tCL", self.xmp_tcl)
        form.addRow("XMP tRCD", self.xmp_trcd)
        form.addRow("XMP tRP", self.xmp_trp)
        form.addRow("XMP tRAS", self.xmp_tras)
        form.addRow("目标频率", self.target_frequency)
        form.addRow("调校风格", self.tuning_style)
        form.addRow("散热条件", self.cooling)
        form.addRow("目标温度上限 °C", self.temperature_limit)
        form.addRow("电压策略", self.voltage_strategy)
        form.addRow("灯效/散热", self.rgb_memory)
        form.addRow("Profile", self.profile_label)

        buttons = QGridLayout()
        self.calculate_button = QPushButton("计算参数")
        self.copy_button = QPushButton("复制 BIOS 参数")
        self.export_button = QPushButton("导出 TXT")
        self.save_button = QPushButton("保存配置 JSON")
        self.load_button = QPushButton("读取配置 JSON")
        self.reset_button = QPushButton("重置输入")
        self.safe_button = QPushButton("一键安全回退")
        buttons.addWidget(self.calculate_button, 0, 0)
        buttons.addWidget(self.copy_button, 0, 1)
        buttons.addWidget(self.export_button, 1, 0)
        buttons.addWidget(self.save_button, 1, 1)
        buttons.addWidget(self.load_button, 2, 0)
        buttons.addWidget(self.reset_button, 2, 1)
        buttons.addWidget(self.safe_button, 3, 0, 1, 2)

        box = QGroupBox("输入参数")
        layout = QVBoxLayout(box)
        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(410)
        scroll.setWidget(box)

        self.calculate_button.clicked.connect(self.calculate)
        self.copy_button.clicked.connect(self.copy_result)
        self.export_button.clicked.connect(self.export_txt)
        self.save_button.clicked.connect(self.save_config)
        self.load_button.clicked.connect(self.load_config)
        self.reset_button.clicked.connect(self.reset_inputs)
        self.safe_button.clicked.connect(self.safe_rollback)
        self.memory_ic.currentTextChanged.connect(self._update_profile_hint)
        self.die_type.currentTextChanged.connect(self._update_profile_hint)
        self.kit.currentTextChanged.connect(self._update_profile_hint)
        self.dimm_capacity.currentTextChanged.connect(self._update_profile_hint)
        return scroll

    def _build_output_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        title = QLabel("推荐 BIOS 参数")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("点击“计算参数”后显示主时序、副时序、三时序、电压、风险和测试流程。")
        layout.addWidget(title)
        layout.addWidget(self.output, 1)
        return panel

    def _read_config(self) -> InputConfig:
        return InputConfig(
            platform=self.platform.currentText(),
            cpu_model=self.cpu_model.text().strip(),
            motherboard_model=self.motherboard_model.text().strip(),
            bios_version=self.bios_version.text().strip(),
            memory_ic=self.memory_ic.currentText(),
            die_type=self.die_type.currentText(),
            kit=self.kit.currentText(),
            dimm_capacity=self.dimm_capacity.currentText(),
            rank=self.rank.currentText(),
            sides=self.sides.currentText(),
            xmp_frequency=self.xmp_frequency.value(),
            xmp_tcl=self.xmp_tcl.value(),
            xmp_trcd=self.xmp_trcd.value(),
            xmp_trp=self.xmp_trp.value(),
            xmp_tras=self.xmp_tras.value(),
            target_frequency=parse_frequency(self.target_frequency.currentText()),
            tuning_style=self.tuning_style.currentText(),
            cooling=self.cooling.currentText(),
            temperature_limit=self.temperature_limit.value(),
            voltage_strategy=self.voltage_strategy.currentText(),
            total_capacity="128GB" if self.kit.currentText() == "4x32GB" else "64GB" if self.kit.currentText() == "2x32GB" else "32GB",
            module_capacity=self.dimm_capacity.currentText(),
            ic_density="16Gb" if self.die_type.currentText() == "16Gb A-die" else self.die_type.currentText().split()[0],
            profile_type="2DPC 4 DIMM" if self.kit.currentText().startswith("4x") else "1DPC 2 DIMM",
            rgb_memory=self.rgb_memory.isChecked(),
        )

    def _apply_config(self, config: InputConfig) -> None:
        self._set_combo(self.platform, config.platform)
        self.cpu_model.setText(config.cpu_model)
        self.motherboard_model.setText(config.motherboard_model)
        self.bios_version.setText(config.bios_version)
        self._set_combo(self.memory_ic, config.memory_ic)
        self._set_combo(self.die_type, config.die_type)
        self._set_combo(self.kit, config.kit)
        self._set_combo(self.dimm_capacity, config.dimm_capacity)
        self._set_combo(self.rank, config.rank)
        self._set_combo(self.sides, config.sides)
        self.xmp_frequency.setValue(config.xmp_frequency)
        self.xmp_tcl.setValue(config.xmp_tcl)
        self.xmp_trcd.setValue(config.xmp_trcd)
        self.xmp_trp.setValue(config.xmp_trp)
        self.xmp_tras.setValue(config.xmp_tras)
        self._set_combo(self.target_frequency, "8000+" if config.target_frequency >= 8000 else str(config.target_frequency))
        self._set_combo(self.tuning_style, config.tuning_style)
        self._set_combo(self.cooling, config.cooling)
        self.temperature_limit.setValue(config.temperature_limit)
        self._set_combo(self.voltage_strategy, config.voltage_strategy)
        self.rgb_memory.setChecked(config.rgb_memory)
        self._update_profile_hint()

    def _set_combo(self, combo: QComboBox, value: str) -> None:
        index = combo.findText(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _update_profile_hint(self) -> None:
        if self.memory_ic.currentText() == "Hynix 16Gb A-die 2x32GB Dual Rank" and self.kit.currentText() != "4x32GB":
            self._set_combo(self.kit, "2x32GB")
            self._set_combo(self.die_type, "16Gb A-die")
        is_2x32_adie = (
            self.kit.currentText() == "2x32GB"
            and self.die_type.currentText() == "16Gb A-die"
            and self.memory_ic.currentText() in {"Hynix A-die", "Hynix 16Gb A-die 2x32GB Dual Rank"}
        )
        is_4x32_adie = (
            self.kit.currentText() == "4x32GB"
            and self.die_type.currentText() == "16Gb A-die"
            and self.memory_ic.currentText() in {"Hynix A-die", "Hynix 16Gb A-die 2x32GB Dual Rank"}
        )
        if is_2x32_adie:
            self._set_combo(self.memory_ic, "Hynix 16Gb A-die 2x32GB Dual Rank")
            self._set_combo(self.dimm_capacity, "32GB")
            self._set_combo(self.rank, "Dual Rank")
            self._set_combo(self.sides, "双面")
            self.profile_label.setText("64GB Dual Rank A-die Profile | 1DPC 2 DIMM | 建议先测试 6000 Daily")
            self.profile_label.setStyleSheet("padding: 6px; background: #fff4d6; border: 1px solid #d8a900; font-weight: 600;")
        elif is_4x32_adie:
            self._set_combo(self.dimm_capacity, "32GB")
            self._set_combo(self.rank, "Dual Rank")
            self._set_combo(self.sides, "双面")
            self.profile_label.setText("128GB Dual Rank A-die High Risk Profile | 2DPC 4 DIMM | 推荐 5600 Safe")
            self.profile_label.setStyleSheet("padding: 6px; background: #ffe4e4; border: 1px solid #c04b4b; font-weight: 600;")
        else:
            self.profile_label.setText("通用 DDR5 profile")
            self.profile_label.setStyleSheet("padding: 6px; background: #eef3f8; border: 1px solid #c8d3df;")

    def calculate(self) -> None:
        try:
            self.current_result = calculate_recommendation(self._read_config())
        except ValidationError as exc:
            QMessageBox.warning(self, "输入需要调整", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "计算失败", str(exc))
            return
        self.output.setHtml(result_to_html(self.current_result))

    def copy_result(self) -> None:
        if self.current_result is None:
            self.calculate()
        if self.current_result is None:
            return
        QGuiApplication.clipboard().setText(result_to_text(self.current_result))
        QMessageBox.information(self, "已复制", "BIOS 参数已复制到剪贴板。")

    def export_txt(self) -> None:
        if self.current_result is None:
            self.calculate()
        if self.current_result is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出 TXT", "ddr5_oc_result.txt", "Text Files (*.txt)")
        if not path:
            return
        Path(path).write_text(result_to_text(self.current_result), encoding="utf-8")
        QMessageBox.information(self, "已导出", f"已导出到：{path}")

    def save_config(self) -> None:
        try:
            config = self._read_config()
            self.current_result = calculate_recommendation(config)
        except ValidationError as exc:
            QMessageBox.warning(self, "输入需要调整", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "计算失败", str(exc))
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存配置 JSON", "ddr5_oc_config.json", "JSON Files (*.json)")
        if not path:
            return
        payload = result_to_json_dict(self.current_result)
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        QMessageBox.information(self, "已保存", f"已保存到：{path}")

    def load_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "读取配置 JSON", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if "config" in data:
                data = data["config"]
            config = InputConfig.from_dict(data)
            self._apply_config(config)
        except Exception as exc:
            QMessageBox.critical(self, "读取失败", str(exc))

    def reset_inputs(self) -> None:
        self._apply_config(InputConfig())
        self.current_result = None
        self.output.clear()

    def safe_rollback(self) -> None:
        config = self._read_config()
        config.target_frequency = 6000
        config.tuning_style = "Safe"
        config.cooling = "机箱风道"
        config.temperature_limit = 45
        config.voltage_strategy = "保守"
        config.rank = "Single Rank" if config.kit in {"2x16GB", "2x24GB"} else config.rank
        self._apply_config(config)
        self.calculate()
