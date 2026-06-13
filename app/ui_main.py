from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.exporter import FIELD_SECTIONS, fields_to_json_dict, fields_to_text
from app.hardware_reader import read_system_hardware
from app.models import HardwareInfo, InputConfig, RecommendationResult
from app.presets import COOLING_OPTIONS, HYNIX_ADIE_2X32_DISPLAY, HYNIX_ADIE_2X32_INTERNAL, KITS, MEMORY_ICS, PLATFORMS, TARGET_FREQUENCIES, VOLTAGE_STRATEGIES
from app.spd_detector import infer_ic_profile
from app.timing_rules import calculate_bios_parameters
from app.validators import ValidationError, parse_frequency
from app.zentimings_importer import import_zentimings_file


PRIMARY_FIELDS = ["tCL", "tRCD", "tRP", "tRAS", "tRC", "tCWL"]
SECONDARY_FIELDS = ["tWR", "tRTP", "tRFC", "tRFC2", "tRFCsb", "tREFI", "tRRD_S", "tRRD_L", "tFAW", "tWTR_S", "tWTR_L"]
TERTIARY_FIELDS = ["tRDRDSCL", "tWRWRSCL", "tRDRDSC", "tWRWRSC", "tRDRDSD", "tRDRDDD", "tWRWRSD", "tWRWRDD", "tRDWR", "tWRRD"]

FIELD_TOOLTIPS = {
    "Gear / Ratio": "AM5 6000/6200/6400 优先 UCLK=MCLK。",
    "DRAM VDD": "2x32GB A-die：6000 1.38V，6200 1.40V，6400 1.42V 起步。",
    "DRAM VDDQ": "通常跟随 DRAM VDD。",
    "CPU VDDIO": "影响 CPU 内存 I/O 和训练稳定性。",
    "VSOC": "AM5 日用推荐 1.20-1.25V，程序硬上限 1.30V。",
    "VDDP": "PHY / 内存训练相关电压，默认 Auto / 1.05V。",
    "VDDG CCD": "Fabric / CCD 相关电压，新手优先 Auto。",
    "VDDG IOD": "Fabric / IOD 相关电压，新手优先 Auto。",
    "VPP": "普通用户保持 Auto 或 1.80V。",
    "tRFC": "2x32GB Hynix A-die Dual Rank 建议从 560-640 起步。温度高时提高 tRFC。",
    "tREFI": "无主动风扇和高温场景优先使用 32768-50000。",
    "tRRD_L": "Dual Rank 大容量套条建议 10-12 起步。",
    "tFAW": "Dual Rank 大容量套条建议 24-32 起步。",
}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DDR5 OC Calculator - BIOS 参数编辑器")
        self.resize(1220, 720)
        self.detected_hardware = HardwareInfo()
        self.current_result: RecommendationResult | None = None
        self.param_fields: dict[str, QLineEdit] = {}
        self._build_ui()
        self._set_default_controls()
        self.statusBar().showMessage("Ready")
        QTimer.singleShot(150, self.auto_read_system)

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.addWidget(self._build_top_bar())
        root.addWidget(self._build_tabs(), 1)
        self.setCentralWidget(central)

    def _build_top_bar(self) -> QWidget:
        panel = QGroupBox("系统与操作")
        layout = QVBoxLayout(panel)

        buttons = QHBoxLayout()
        self.auto_button = QPushButton("自动读取系统")
        self.import_button = QPushButton("导入 ZenTimings")
        self.calculate_button = QPushButton("计算")
        self.safe_button = QPushButton("一键安全值")
        self.copy_button = QPushButton("复制参数")
        self.export_button = QPushButton("导出")
        self.save_button = QPushButton("保存配置")
        self.load_button = QPushButton("读取配置")
        for button in [self.auto_button, self.import_button, self.calculate_button, self.safe_button, self.copy_button, self.export_button, self.save_button, self.load_button]:
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        info_grid = QGridLayout()
        self.cpu_edit = QLineEdit()
        self.board_edit = QLineEdit()
        self.bios_edit = QLineEdit()
        self.memory_edit = QLineEdit()
        self.risk_label = QLabel("Profile: - | Target: - | Risk: -")
        self.risk_label.setStyleSheet("padding: 6px; background: #eef3f8; border: 1px solid #c8d3df; font-weight: 600;")
        info_grid.addWidget(QLabel("CPU"), 0, 0)
        info_grid.addWidget(self.cpu_edit, 0, 1)
        info_grid.addWidget(QLabel("Board"), 0, 2)
        info_grid.addWidget(self.board_edit, 0, 3)
        info_grid.addWidget(QLabel("BIOS"), 1, 0)
        info_grid.addWidget(self.bios_edit, 1, 1)
        info_grid.addWidget(QLabel("RAM"), 1, 2)
        info_grid.addWidget(self.memory_edit, 1, 3)
        info_grid.addWidget(self.risk_label, 0, 4, 2, 1)
        info_grid.setColumnStretch(1, 1)
        info_grid.setColumnStretch(3, 1)
        layout.addLayout(info_grid)

        controls = QHBoxLayout()
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(PLATFORMS)
        self.ic_combo = QComboBox()
        self.ic_combo.addItems(MEMORY_ICS)
        self.kit_combo = QComboBox()
        self.kit_combo.addItems(KITS)
        self.target_combo = QComboBox()
        self.target_combo.addItems(TARGET_FREQUENCIES)
        self.cooling_combo = QComboBox()
        self.cooling_combo.addItems(COOLING_OPTIONS)
        self.voltage_combo = QComboBox()
        self.voltage_combo.addItems(VOLTAGE_STRATEGIES)
        for label, widget in [("Platform", self.platform_combo), ("IC Profile", self.ic_combo), ("Kit", self.kit_combo), ("Target", self.target_combo), ("Cooling", self.cooling_combo), ("Voltage", self.voltage_combo)]:
            controls.addWidget(QLabel(label))
            controls.addWidget(widget)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.auto_button.clicked.connect(self.auto_read_system)
        self.import_button.clicked.connect(self.import_zentimings)
        self.calculate_button.clicked.connect(self.calculate)
        self.safe_button.clicked.connect(self.safe_values)
        self.copy_button.clicked.connect(self.copy_parameters)
        self.export_button.clicked.connect(self.export_parameters)
        self.save_button.clicked.connect(self.save_config)
        self.load_button.clicked.connect(self.load_config)
        return panel

    def _build_tabs(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.addTab(self._build_frequency_voltage_tab(), "频率 / 电压")
        tabs.addTab(self._build_memory_timing_tab(), "内存时序")
        tabs.addTab(self._build_test_tab(), "测试建议")
        return tabs

    def _build_frequency_voltage_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(self._build_group("Frequency", FIELD_SECTIONS["Frequency"], columns=2))
        layout.addWidget(self._build_group("Voltage", FIELD_SECTIONS["CPU / DRAM Voltage"], columns=2))
        layout.addStretch(1)
        return widget

    def _build_memory_timing_tab(self) -> QScrollArea:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(self._build_group("Primary Timings", PRIMARY_FIELDS, columns=3))
        layout.addWidget(self._build_group("Secondary Timings", SECONDARY_FIELDS, columns=3))
        layout.addWidget(self._build_group("Tertiary Timings", TERTIARY_FIELDS, columns=3))
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        return scroll

    def _build_group(self, title: str, names: list[str], columns: int) -> QGroupBox:
        group = QGroupBox(title)
        grid = QGridLayout(group)
        for index, name in enumerate(names):
            row = index // columns
            column = (index % columns) * 2
            label = QLabel(name)
            edit = QLineEdit()
            edit.setFixedWidth(105)
            edit.setToolTip(FIELD_TOOLTIPS.get(name, "可手动覆盖。"))
            self.param_fields[name] = edit
            if name in {"DRAM VDD", "DRAM VDDQ", "CPU VDDIO", "VSOC", "VDDP", "VDDG CCD", "VDDG IOD"}:
                edit.editingFinished.connect(lambda field_name=name: self._mark_manual_voltage_risk(field_name))
            grid.addWidget(label, row, column)
            grid.addWidget(edit, row, column + 1)
            grid.setColumnStretch(column, 1)
        return group

    def _build_test_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.test_advice = QTextEdit()
        self.test_advice.setReadOnly(True)
        self.test_advice.setPlainText("\n".join(f"- {item}" for item in self._suggestions()))
        layout.addWidget(self.test_advice)
        return widget

    def _set_default_controls(self) -> None:
        self._set_combo(self.platform_combo, "AMD AM5")
        self._set_combo(self.ic_combo, HYNIX_ADIE_2X32_DISPLAY)
        self._set_combo(self.kit_combo, "2x32GB")
        self._set_combo(self.target_combo, "6000")
        self._set_combo(self.cooling_combo, "机箱风道")
        self._set_combo(self.voltage_combo, "正常")
        self.memory_edit.setText("64GB 2x32GB")

    def _set_combo(self, combo: QComboBox, value: str) -> None:
        if value == HYNIX_ADIE_2X32_INTERNAL:
            value = HYNIX_ADIE_2X32_DISPLAY
        index = combo.findText(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _read_config(self) -> InputConfig:
        kit = self.kit_combo.currentText()
        dimm_capacity = kit.split("x", 1)[1] if "x" in kit else "32GB"
        total_capacity = "64GB" if kit == "2x32GB" else "128GB" if kit == "4x32GB" else "32GB"
        rank = "Dual Rank" if kit in {"2x32GB", "4x32GB"} else "Single Rank"
        sides = "双面" if rank == "Dual Rank" else "单面"
        target_frequency = parse_frequency(self.target_combo.currentText())
        return InputConfig(
            platform=self.platform_combo.currentText(),
            cpu_model=self.cpu_edit.text().strip(),
            motherboard_model=self.board_edit.text().strip(),
            bios_version=self.bios_edit.text().strip(),
            memory_ic=self.ic_combo.currentText(),
            die_type="16Gb A-die" if "A-die" in self.ic_combo.currentText() else "16Gb M-die",
            kit=kit,
            dimm_capacity=dimm_capacity,
            rank=rank,
            sides=sides,
            xmp_frequency=parse_frequency(self.param_fields["Memory Frequency"].text() or self.target_combo.currentText()),
            xmp_tcl=int(self.param_fields["tCL"].text() or 36),
            xmp_trcd=int(self.param_fields["tRCD"].text() or 36),
            xmp_trp=int(self.param_fields["tRP"].text() or 36),
            xmp_tras=int(self.param_fields["tRAS"].text() or 76),
            target_frequency=target_frequency,
            tuning_style="Daily" if target_frequency <= 6000 else "Performance" if target_frequency <= 6200 else "Benchmark",
            cooling=self.cooling_combo.currentText(),
            temperature_limit=50,
            voltage_strategy=self.voltage_combo.currentText(),
            total_capacity=total_capacity,
            module_capacity=dimm_capacity,
            profile_display_name=self.ic_combo.currentText(),
            ic_vendor="SK hynix",
            ic_type="A-die" if "A-die" in self.ic_combo.currentText() else "M-die",
            ic_density="16Gb",
            profile_type="2DPC 4 DIMM" if kit.startswith("4x") else "1DPC 2 DIMM",
            vsoc=self.param_fields.get("VSOC", QLineEdit()).text(),
            cpu_vddio=self.param_fields.get("CPU VDDIO", QLineEdit()).text(),
            vddp=self.param_fields.get("VDDP", QLineEdit()).text(),
            vddg_ccd=self.param_fields.get("VDDG CCD", QLineEdit()).text(),
            vddg_iod=self.param_fields.get("VDDG IOD", QLineEdit()).text(),
        )

    def _set_field(self, name: str, value: str, tooltip: str = "", status: str = "normal") -> None:
        field = self.param_fields.get(name)
        if field is None:
            return
        field.setText(str(value))
        field.setToolTip(tooltip or FIELD_TOOLTIPS.get(name, "可手动覆盖。"))
        if status == "high":
            field.setStyleSheet("border: 2px solid #c62828; padding: 2px;")
        elif status == "warning":
            field.setStyleSheet("border: 2px solid #d8a900; padding: 2px;")
        else:
            field.setStyleSheet("border: 1px solid #b7b7b7; padding: 2px;")

    def _field_voltage(self, name: str) -> float | None:
        field = self.param_fields.get(name)
        if field is None:
            return None
        text = field.text().replace("V", "").strip()
        try:
            return float(text)
        except ValueError:
            return None

    def _mark_manual_voltage_risk(self, name: str) -> None:
        value = self._field_voltage(name)
        if value is None:
            return
        status = "normal"
        tooltip = FIELD_TOOLTIPS.get(name, "可手动覆盖。")
        if name == "VSOC":
            if value > 1.30:
                status = "high"
                tooltip = "VSOC above 1.30V is high risk on AM5. Use 1.20-1.25V for daily."
            elif value > 1.25:
                status = "warning"
        elif name == "CPU VDDIO":
            if value >= 1.45:
                status = "high"
            elif value > 1.35:
                status = "warning"
        elif name in {"VDDP", "VDDG CCD", "VDDG IOD"}:
            if value > 1.15:
                status = "high"
            elif value > 1.10:
                status = "warning"
        elif name in {"DRAM VDD", "DRAM VDDQ"}:
            if value >= 1.50:
                status = "high"
            elif value > 1.40:
                status = "warning"
        self._set_field(name, self.param_fields[name].text(), tooltip, status)

    def _current_fields(self) -> dict[str, str]:
        return {name: field.text().strip() for name, field in self.param_fields.items() if field.text().strip()}

    def _apply_result(self, result: RecommendationResult, fields: dict[str, str]) -> None:
        risk_by_name: dict[str, str] = {}
        tooltip_by_name: dict[str, str] = {}
        for entry in result.primary + result.secondary + result.tertiary:
            risk_by_name[entry.name] = "warning" if entry.risk in {"偏激进", "高温敏感", "激进"} else "normal"
            tooltip_by_name[entry.name] = entry.note
        for voltage in result.voltages:
            name = "CPU VDDIO" if voltage.name == "CPU VDDIO / VDDIO MEM" else voltage.name
            risk_by_name[name] = "high" if voltage.risk == "高风险" else "warning" if voltage.risk == "偏高" else "normal"
            tooltip_by_name[name] = voltage.note
        for name, value in fields.items():
            self._set_field(name, value, tooltip_by_name.get(name, ""), risk_by_name.get(name, "normal"))

        profile = result.profile.display_name if result.profile else result.config.profile_display_name or result.config.memory_ic
        suffix = " | VSOC too high" if any("VSOC above 1.30V" in item for item in result.risk_explanations) else ""
        display_risk = "High Risk" if result.risk_level == "Benchmark / High Risk" else result.risk_level
        self.risk_label.setText(f"Profile: {profile} | Target: {result.config.target_frequency} MT/s | Risk: {display_risk} {result.risk_score}/100{suffix}")
        if result.risk_score >= 76:
            self.risk_label.setStyleSheet("padding: 6px; background: #ffe4e4; border: 1px solid #c62828; font-weight: 600;")
        elif result.risk_score >= 51:
            self.risk_label.setStyleSheet("padding: 6px; background: #fff4d6; border: 1px solid #d8a900; font-weight: 600;")
        else:
            self.risk_label.setStyleSheet("padding: 6px; background: #eaf7ed; border: 1px solid #2e7d32; font-weight: 600;")
        self.test_advice.setPlainText("\n".join(f"- {item}" for item in self._suggestions(result)))

    def _suggestions(self, result: RecommendationResult | None = None) -> list[str]:
        suggestions = [
            "建议先测试 6000 Daily。",
            "6200 需要更好 IMC。",
            "6400 属于高风险。",
            "2x32GB Dual Rank 关注温度、tRFC、tREFI、VDDIO、VSOC。",
            "出错优先回退 tRFC/tREFI/VDDIO/VSOC。",
        ]
        if result and result.risk_explanations:
            suggestions[-1] = result.risk_explanations[0]
        return suggestions[:5]

    def calculate(self) -> None:
        try:
            result, fields = calculate_bios_parameters(self._read_config())
        except (ValidationError, ValueError) as exc:
            QMessageBox.warning(self, "输入需要调整", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "计算失败", str(exc))
            return
        self.current_result = result
        self._apply_result(result, fields)
        self.statusBar().showMessage("Calculated")

    def safe_values(self) -> None:
        self._set_combo(self.target_combo, "6000")
        self._set_combo(self.ic_combo, HYNIX_ADIE_2X32_DISPLAY)
        self._set_combo(self.kit_combo, "2x32GB")
        self._set_combo(self.cooling_combo, "机箱风道")
        self._set_combo(self.voltage_combo, "正常")
        self.calculate()

    def auto_read_system(self) -> None:
        self.statusBar().showMessage("Auto detecting...")
        hardware = read_system_hardware()
        self.detected_hardware = hardware
        self.cpu_edit.setText(hardware.cpu_name or "自动读取失败，可手动填写")
        board = " ".join(part for part in [hardware.motherboard_manufacturer, hardware.motherboard_product] if part)
        self.board_edit.setText(board or "自动读取失败，可手动填写")
        self.bios_edit.setText(hardware.bios_version or "自动读取失败，可手动填写")
        self.memory_edit.setText(hardware.memory_summary())
        if "AMD" in hardware.cpu_name.upper() or "RYZEN" in hardware.cpu_name.upper():
            self._set_combo(self.platform_combo, "AMD AM5")
        elif hardware.cpu_name:
            self._set_combo(self.platform_combo, "Intel DDR5")
        if hardware.kit_type:
            self._set_combo(self.kit_combo, hardware.kit_type)
        if hardware.configured_speed:
            self._set_combo(self.target_combo, str(hardware.configured_speed) if hardware.configured_speed < 8000 else "8000+")
            self._set_field("Memory Frequency", str(hardware.configured_speed))
        part_profile = infer_ic_profile([module.part_number for module in hardware.memory_modules])
        if part_profile:
            self._set_combo(self.ic_combo, part_profile)
        elif hardware.kit_type == "2x32GB":
            self._set_combo(self.ic_combo, HYNIX_ADIE_2X32_DISPLAY)
        self.statusBar().showMessage("Auto detected" if not hardware.detection_error else "Ready")
        self.calculate()

    def import_zentimings(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "导入 ZenTimings 文本", "", "Text/JSON/CSV (*.txt *.json *.csv);;All Files (*.*)")
        if not path:
            return
        try:
            values = import_zentimings_file(path)
        except Exception as exc:
            QMessageBox.critical(self, "导入失败", str(exc))
            return
        for name, value in values.items():
            self._set_field(name, value)
        self.statusBar().showMessage("Ready")
        QMessageBox.information(self, "导入完成", f"已导入 {len(values)} 个字段。")

    def copy_parameters(self) -> None:
        QGuiApplication.clipboard().setText(fields_to_text(self._current_fields()))
        self.statusBar().showMessage("Ready")
        QMessageBox.information(self, "已复制", "当前参数框内容已复制。")

    def export_parameters(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "导出参数", "ddr5_bios_parameters.txt", "Text Files (*.txt);;JSON Files (*.json)")
        if not path:
            return
        fields = self._current_fields()
        if path.lower().endswith(".json"):
            payload = fields_to_json_dict(self._read_config(), fields, self.current_result, self._suggestions(self.current_result))
            Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            Path(path).write_text(fields_to_text(fields), encoding="utf-8")
        self.statusBar().showMessage("Exported")
        QMessageBox.information(self, "已导出", f"已导出到：{path}")

    def save_config(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "保存配置", "ddr5_bios_config.json", "JSON Files (*.json)")
        if not path:
            return
        payload = fields_to_json_dict(self._read_config(), self._current_fields(), self.current_result, self._suggestions(self.current_result))
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.statusBar().showMessage("Ready")
        QMessageBox.information(self, "已保存", f"已保存到：{path}")

    def load_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "读取配置", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            config_data = data.get("config", data)
            fields = data.get("bios_parameters", {})
            config = InputConfig.from_dict(config_data)
        except Exception as exc:
            QMessageBox.critical(self, "读取失败", str(exc))
            return
        self.cpu_edit.setText(config.cpu_model)
        self.board_edit.setText(config.motherboard_model)
        self.bios_edit.setText(config.bios_version)
        self.memory_edit.setText(f"{config.total_capacity} {config.kit}")
        self._set_combo(self.platform_combo, config.platform)
        self._set_combo(self.ic_combo, config.profile_display_name or config.memory_ic)
        self._set_combo(self.kit_combo, config.kit)
        self._set_combo(self.target_combo, str(config.target_frequency) if config.target_frequency < 8000 else "8000+")
        self._set_combo(self.cooling_combo, config.cooling)
        self._set_combo(self.voltage_combo, config.voltage_strategy)
        for name, value in fields.items():
            self._set_field(name, str(value))
        self.calculate()
