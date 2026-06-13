from __future__ import annotations

HYNIX_ADIE_2X32_DUAL_RANK_NOTES = [
    "Market baseline: DDR5-6000 CL30 2x32GB kits commonly use 30-40-40-96 around 1.40V.",
    "High-bin baseline: Some 2x32GB kits use tighter 30-36-36 around 1.40V.",
    "Tuning baseline: 6000 MT/s is the preferred daily target on AM5 for 2x32GB dual-rank kits.",
    "6200/6400 profiles are optional advanced profiles and require IMC, motherboard BIOS and memory cooling validation.",
    "Dual-rank 2x32GB kits should use more conservative tRFC/tREFI/tRRD_L/tFAW and SD/DD tertiary timings than 2x16GB single-rank kits.",
    "Active DIMM airflow is recommended when using high tREFI, low tRFC or DRAM VDD/VDDQ above 1.40V.",
    "These notes are descriptive program context for profile selection and testing scope. Stability still requires local validation.",
]


def get_reference_notes(profile_name: str) -> list[str]:
    if profile_name in {"Hynix 16Gb A-die 2x32GB Dual Rank", "Hynix A-die 2x32GB Dual Rank"}:
        return list(HYNIX_ADIE_2X32_DUAL_RANK_NOTES)
    return []
