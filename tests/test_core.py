from __future__ import annotations

import unittest

from app.exporter import fields_to_json_dict, fields_to_text
from app.models import InputConfig
from app.presets import HYNIX_ADIE_2X32_DISPLAY, UNKNOWN_IC_PROFILE
from app.timing_rules import calculate_bios_parameters
from app.validators import ValidationError
from app.voltage_rules import calculate_am5_cpu_voltages
from app.zentimings_importer import parse_zentimings_text


def two_by_thirty_two_config(target: int = 6000) -> InputConfig:
    return InputConfig(
        cpu_model="AMD Ryzen 7 9700X",
        memory_ic=HYNIX_ADIE_2X32_DISPLAY,
        die_type="16Gb A-die",
        kit="2x32GB",
        dimm_capacity="32GB",
        rank="Dual Rank",
        sides="双面",
        target_frequency=target,
        tuning_style="Daily" if target <= 6000 else "Performance" if target <= 6200 else "Benchmark",
    )


class CoreRulesTests(unittest.TestCase):
    def test_daily_6000_profile_matches_reference_values(self) -> None:
        result, fields = calculate_bios_parameters(two_by_thirty_two_config())
        self.assertEqual(result.risk_score, 36)
        self.assertEqual(fields["tCL"], "30")
        self.assertEqual(fields["tRCD"], "38")
        self.assertEqual(fields["tRAS"], "50")
        self.assertEqual(fields["tRC"], "88")
        self.assertEqual(fields["CPU VDDIO"], "1.30V")
        self.assertEqual(fields["VSOC"], "1.25V")

    def test_am5_target_fallback_preserves_requested_frequency(self) -> None:
        result, fields = calculate_bios_parameters(two_by_thirty_two_config(6600))
        self.assertEqual(result.config.requested_frequency, 6600)
        self.assertEqual(result.config.target_frequency, 6200)
        self.assertEqual(fields["Memory Frequency"], "6200")

    def test_unconfirmed_6200_adds_thermal_risk_notice(self) -> None:
        result, _ = calculate_bios_parameters(two_by_thirty_two_config(6200))
        self.assertTrue(any("尚未确认内存散热" in reason for reason in result.risk_explanations))

    def test_unknown_ic_requires_manual_selection(self) -> None:
        config = two_by_thirty_two_config()
        config.memory_ic = UNKNOWN_IC_PROFILE
        with self.assertRaises(ValidationError):
            calculate_bios_parameters(config)

    def test_am5_cpu_voltage_policy(self) -> None:
        result = calculate_am5_cpu_voltages("Ryzen 7 9700X", 6400, "2x32GB", "Dual Rank", "机箱风道", "正常")
        self.assertEqual(result["VSOC"], "1.28V")
        self.assertEqual(result["CPU VDDIO"], "1.38V")
        self.assertEqual(result["VDDP"], "Auto / 1.05V")

    def test_zentimings_text_and_export_metadata(self) -> None:
        parsed = parse_zentimings_text("MCLK 3000\ntCL 30\ntRCDRD 38\nVSOC 1.25\nVDDGCCD Auto")
        self.assertEqual(parsed["MCLK"], "3000")
        self.assertEqual(parsed["tRCD"], "38")
        self.assertEqual(parsed["VSOC"], "1.25")
        result, fields = calculate_bios_parameters(two_by_thirty_two_config())
        payload = fields_to_json_dict(result.config, fields, result, [], {"tCL": "Calculated"})
        self.assertEqual(payload["profile_display_name"], HYNIX_ADIE_2X32_DISPLAY)
        self.assertEqual(payload["ic_density"], "16Gb")
        self.assertEqual(payload["parameter_sources"]["tCL"], "Calculated")
        self.assertEqual(payload["current_parameters"], {})
        self.assertIn("[Frequency]", fields_to_text(fields))


if __name__ == "__main__":
    unittest.main()
