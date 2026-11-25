"""Tier 3 Inter-Tier Leakage Gain Matrix K Extractor (EQ-27).

Sequentially injects a small-amplitude f_test = 100 Hz sinusoidal tone into each of
the 3 analog/electronic 1/f noise nodes (TIA offset, DAC V_ref, resistive crosstalk)
in Tier 2 (0.1 s real SystemC-AMS simulation each) and measures the 100 Hz harmonic
amplitude of Omega_out via coherent FFT/DFT to assemble:
    K = [ K_{TIA->Omega}, K_{DAC->Omega}, K_{xtalk->Omega} ]_{f = 100 Hz}

CLI Contract:
    python3 tier3_analysis/extract_k_matrix.py --bin ./build/ifog_sim \
        --cfg configs/baseline_1km.json --phys data/run01/phys_params.json --out data/run01/
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from tier1_offline.config_loader import deep_merge, load_config
from tier3_analysis.binary_io import extract_coherent_tone_amplitude, read_sim_records


def measure_single_node_leakage(
    sim_bin: Path | str,
    base_cfg: dict[str, Any],
    phys_path: Path | str,
    work_dir: Path,
    target: str,
    inject_amp: float,
    freq_Hz: float = 100.0,
    duration_s: float = 0.1,
) -> dict[str, float]:
    """Run a single 100 Hz sinusoidal injection Tier 2 simulation and extract leakage gain."""
    if target not in {"tia", "dac", "xtalk"}:
        raise ValueError(f"Unsupported target node: {target}")

    work_dir.mkdir(parents=True, exist_ok=True)
    # Keep deterministic noise-free injection while preserving configured nonlinearities
    overrides: dict[str, Any] = {
        "noise": {
            "en_white_noise": False,
            "en_pink_noise": False,
            "sine_inject_target": target,
            "sine_inject_freq_Hz": float(freq_Hz),
            "sine_inject_amp": float(inject_amp),
        },
        "simulation": {
            "duration_s": float(duration_s),
            "decimation_tau": 4,
            "dump_micro_ms": 0.0,
        },
    }
    run_cfg = deep_merge(base_cfg, overrides)
    cfg_file = work_dir / f"cfg_inject_{target}.json"
    with cfg_file.open("w", encoding="utf-8") as fh:
        json.dump(run_cfg, fh, indent=2)

    out_dir = work_dir / f"out_inject_{target}"
    subprocess.run(
        [
            str(sim_bin),
            "--phys",
            str(phys_path),
            "--cfg",
            str(cfg_file),
            "--out",
            str(out_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    records = read_sim_records(out_dir / "sim_out.bin")
    t_s = records["t"]
    omega_out = records["omega_out"]

    # Discard initial 20% settling transient (leaves exact integer cycles at 100 Hz)
    start_idx = len(t_s) // 5
    amp_omega = extract_coherent_tone_amplitude(t_s[start_idx:], omega_out[start_idx:], freq_Hz)

    # Convert relative node perturbation into physical parameter perturbation per EQ-27:
    #   TIA:   dV_off_TIA = inject_amp [V]
    #   DAC:   dV_ref_DAC = V_ref_dac_V * inject_amp [V]
    #   xtalk: dk_xtalk   = k_xtalk_A_per_V * inject_amp [A/V]
    if target == "tia":
        phys_delta = inject_amp
    elif target == "dac":
        phys_delta = float(base_cfg["adc_dac"]["V_ref_dac_V"]) * inject_amp
    else:
        k_xt = float(base_cfg["analog_frontend"]["k_xtalk_A_per_V"])
        phys_delta = k_xt * inject_amp if k_xt != 0.0 else inject_amp

    gain_phys = amp_omega / phys_delta if phys_delta > 0.0 else 0.0
    gain_node_unit = amp_omega / inject_amp if inject_amp > 0.0 else 0.0
    return {
        "target": target,
        "freq_Hz": float(freq_Hz),
        "inject_amp": float(inject_amp),
        "phys_delta": float(phys_delta),
        "omega_amp_rad_s": float(amp_omega),
        "gain_phys": float(gain_phys),
        "gain_node_unit": float(gain_node_unit),
    }


def extract_k_matrix(
    sim_bin: Path | str,
    cfg: dict[str, Any],
    phys_path: Path | str,
    out_dir: Path | str,
    freq_Hz: float = 100.0,
    duration_s: float = 0.1,
    amp_tia_V: float = 0.02,
    amp_dac_rel: float = 5.0e-3,
    amp_xtalk_rel: float = 0.2,
) -> dict[str, Any]:
    """Measure all 3 components of leakage matrix K = [K_TIA, K_DAC, K_xtalk] (EQ-27)."""
    out_path = Path(out_dir)
    work_dir = out_path / "k_matrix_probes"

    res_tia = measure_single_node_leakage(
        sim_bin, cfg, phys_path, work_dir, "tia", amp_tia_V, freq_Hz=freq_Hz, duration_s=duration_s
    )
    res_dac = measure_single_node_leakage(
        sim_bin, cfg, phys_path, work_dir, "dac", amp_dac_rel, freq_Hz=freq_Hz, duration_s=duration_s
    )
    res_xtalk = measure_single_node_leakage(
        sim_bin, cfg, phys_path, work_dir, "xtalk", amp_xtalk_rel, freq_Hz=freq_Hz, duration_s=duration_s
    )

    k_summary: dict[str, Any] = {
        "spec_id": "IFOG-SIM-SPEC-004",
        "formula_id": "EQ-27",
        "f_test_Hz": float(freq_Hz),
        "duration_s": float(duration_s),
        "K_TIA_to_Omega_rad_s_per_V": res_tia["gain_phys"],
        "K_DAC_to_Omega_rad_s_per_V": res_dac["gain_phys"],
        "K_xtalk_to_Omega_rad_s_per_A_per_V": res_xtalk["gain_phys"],
        "K_node_unit_vector": [
            res_tia["gain_node_unit"],
            res_dac["gain_node_unit"],
            res_xtalk["gain_node_unit"],
        ],
        "K_physical_vector": [
            res_tia["gain_phys"],
            res_dac["gain_phys"],
            res_xtalk["gain_phys"],
        ],
        "probes": {
            "tia": res_tia,
            "dac": res_dac,
            "xtalk": res_xtalk,
        },
    }

    out_path.mkdir(parents=True, exist_ok=True)
    with (out_path / "k_matrix.json").open("w", encoding="utf-8") as fh:
        json.dump(k_summary, fh, indent=2)
    return k_summary


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for Tier 2 -> Tier 3 leakage matrix K extraction."""
    parser = argparse.ArgumentParser(
        description="Extract 1/f Leakage Gain Matrix K via 100 Hz FFT Injection (EQ-27)"
    )
    parser.add_argument("--bin", required=True, help="Path to compiled ifog_sim executable")
    parser.add_argument("--cfg", required=True, help="Path to IFOG config JSON")
    parser.add_argument("--phys", required=True, help="Path to Tier 1 phys_params.json")
    parser.add_argument("--out", required=True, help="Output directory for k_matrix.json")
    parser.add_argument("--freq-hz", type=float, default=100.0, help="Test tone frequency [Hz]")
    parser.add_argument("--duration-s", type=float, default=0.1, help="Probe duration [s]")
    args = parser.parse_args(argv)

    cfg = load_config(args.cfg)
    extract_k_matrix(
        sim_bin=args.bin,
        cfg=cfg,
        phys_path=args.phys,
        out_dir=args.out,
        freq_Hz=args.freq_hz,
        duration_s=args.duration_s,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
