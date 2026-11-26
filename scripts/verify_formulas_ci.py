#!/usr/bin/env python3
"""CI/CD Formula Verification Gate (AGENT.md Rule 3).

Executes all 30 individual normative formula verification tests (EQ-01 .. EQ-30)
defined in IFOG-SIM-SPEC-004, asserts that every single formula ID is present and
PASSED with zero skips/failures, and writes JSON + Markdown traceability reports.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

EXPECTED_FORMULAS = [f"EQ-{i:02d}" for i in range(1, 45)]

FORMULA_DESCRIPTIONS = {
    "EQ-01": "Sec 1 Eq. (1): 4-state bias phase sequence [+(pi-a), -(pi-a), -(pi+a), +(pi+a)]",
    "EQ-02": "Sec 1 Eqs. (2)-(5): 1st-order Taylor expansion at 4 bias states",
    "EQ-03": "Sec 1 Eq. (6): Orthogonal 4-state demodulation e_Omega & e_Vpi (sign corrected)",
    "EQ-04": "Sec 3.1.1 Eq. (7): Spectral-sliced Jones matrices J_CW, J_CCW = J_CW^T",
    "EQ-05": "Sec 3.1.1 Eq. (8): Fringe visibility V & polarization bias phase phi_pol",
    "EQ-06": "Sec 3.1.2 Eq. (9): Coil transit time tau & non-reciprocal phase sum Delta_phi_NR",
    "EQ-07": "Sec 3.1.2 Eq. (10a): Optical Sagnac scale factor K_opt = 2*pi*L*D/(lambda*c)",
    "EQ-08": "Sec 3.1.2 Eq. (10b): Optical Kerr phase Delta_phi_Kerr with eta_coh (Bergh 1982)",
    "EQ-09": "Sec 3.1.2 Eq. (11): Thermal Shupe integral Delta_phi_Shupe(t) with delta_z_quad",
    "EQ-10": "Sec 3.1.2 Eq. (12): Magneto-optic Faraday phase Delta_phi_Faraday(t)",
    "EQ-11": "Sec 3.1.2 Eq. (13): MIOC modulation phase phi_MIOC[m] with eps_Vpi & gamma_nl",
    "EQ-12": "Sec 3.1.2 Eq. (14): Differential modulation phase Delta_phi_mod & wrap_2pi",
    "EQ-13": "Sec 3.1.2 Eq. (15): Photodiode detected power P_det[m] with parasitic RAM",
    "EQ-14": "Sec 3.2.1 Eq. (16): TIA inverting-node total input current I_in[m] with crosstalk",
    "EQ-15": "Sec 3.2.1 Eq. (17): 6-component input current noise PSD S_i,tot(f) & variance",
    "EQ-16": "Sec 3.2.2 Eqs. (18)-(19): 2nd-order TIA transfer function H_TIA(s), omega_0, zeta",
    "EQ-17": "Sec 3.2.2 Eq. (20): Butterworth optimal C_f,opt and 0.1% settling time t_s(0.1%)",
    "EQ-18": "Sec 3.2.3 Eqs. (21)-(22): TIA 1/f offset & cubic polynomial nonlinearity + clipping",
    "EQ-19": "Sec 3.2.3 Eq. (23): ADC blanking window, N_ADC quantization & 1/sqrt(eta_b) penalty",
    "EQ-20": "Sec 3.3.1 Eqs. (24)-(27): 2-state & 4-state Loop-1/Loop-2 integrator updates",
    "EQ-21": "Sec 3.3.1 Eqs. (28)-(29): Digital phase ramp wrap_2pi & DAC code with PRBS dither",
    "EQ-22": "Sec 3.3.2 Eqs. (30)-(31): Z-domain L_1(z), Jury stability 0<K_tot<1 & Loop-2 separation",
    "EQ-23": "Sec 3.3.2 Eq. (32): Closed-loop output angular rate Omega_out = Delta_phi_step / SF_CL",
    "EQ-24": "Sec 3.4 Eq. (33): IEEE Std 952-2020 5-component Allan variance sigma^2(T)",
    "EQ-25": "Sec 3.4 Eq. (34): Rate Random Walk (RRW) Wiener & 1st-order Gauss-Markov AR(1)",
    "EQ-26": "Sec 4.1 Eq. (35): Inter-tier phase-to-rate conversion (rad/s <-> deg/h x 206264.8)",
    "EQ-27": "Sec 4.2 Eq. (36): Leakage gain matrix K = [K_TIA, K_DAC, K_xtalk] at 100 Hz FFT",
    "EQ-28": "Sec 4.3 Eq. (37): Slow-scale 10h / 100 Hz rate synthesis Omega_slow[i]",
    "EQ-29": "Sec 4.3 Eq. (38): IEEE Std 952 Overlapping Allan Variance sigma^2(T_m)",
    "EQ-30": "Sec 4.3 Eq. (39): Dual-regime overlap continuity < 5% on T_m in [0.1, 5] s",
    "EQ-31": "SPEC-005 Sec 3.2.1: Official 6-state anti-periodic psi_0..psi_5 & differential phi_1..phi_6",
    "EQ-32": "SPEC-005 Sec 3.2.2: 6-state 1st-order Taylor expansion & zero-crosstalk angle alpha*=pi/3",
    "EQ-33": "SPEC-005 Sec 3.2.3: Orthogonal 6-state 3-channel demodulation (e_Omega, e_Vpi, e_asym)",
    "EQ-34": "SPEC-005 Sec 3.2.4: 6-state Loop-1/Loop-2 gains, closed-loop -3 dB BW & anti-windup",
    "EQ-35": "SPEC-005 Sec 5.1: ADC sampling aperture jitter dV_j = (dV/dt)*dt_j & jitter ARW RSS",
    "EQ-36": "SPEC-005 Sec 5.2: 3-axis IMU shared-SLD back-reflection P_axis,i & shared rail droop",
    "EQ-37": "SPEC-005 Sec 5.3: Vibration Rectification Error (VRE) quadratic G2*V^2 law [deg/h/g^2]",
    "EQ-38": "SPEC-005 Sec 5.3: Dynamic Faraday magnetic sensitivity S_B & Mu-metal shielding [dB]",
    "EQ-39": "SPEC-005 Sec 5.4: Real-time FPGA BIT/FDIR 5-fault classification thresholds & TTA",
    "EQ-40": "SPEC-005 Sec 5.5: Monte Carlo Production Yield, Wilson 95% CI & process capability C_pk",
    "EQ-41": "SPEC-005 Sec 5.5: Thermal drift model (lambda(T), V_pi(T)), 2D poly & EKF bias compensation",
    "EQ-42": "SPEC-006 Sec 4.1: FMI 3.0 multi-rate ZOH alignment N_tau & anti-aliased macro-step average",
    "EQ-43": "SPEC-006 Sec 4.2: FMI 3.0 Loop-2 residual V_pi phase error e_Vpi_res [rad] & 6-bit bit_status",
    "EQ-44": "SPEC-006 Sec 4.3: Black-box FMU vs standalone Tier 2 < 1e-12 equivalence & singleton contract",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify all 44 IFOG-SIM-SPEC-006 formulas in CI")
    parser.add_argument("--out-dir", default="data/ci_formula_report", help="Report output directory")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    junit_xml = out_dir / "formula_junit.xml"

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/formula_verification",
        "-m",
        "formula",
        "-v",
        f"--junitxml={junit_xml}",
    ]
    proc = subprocess.run(cmd, check=False)

    if not junit_xml.exists():
        print("ERROR: JUnit XML report was not generated by pytest", file=sys.stderr)
        return 1

    tree = ET.parse(junit_xml)
    root = tree.getroot()
    results: dict[str, dict[str, str]] = {}

    for tc in root.iter("testcase"):
        name = tc.attrib.get("name", "")
        match = re.match(r"^test_eq(\d{2})_", name)
        if not match:
            continue
        eq_id = f"EQ-{int(match.group(1)):02d}"
        status = "PASS"
        if tc.find("failure") is not None or tc.find("error") is not None:
            status = "FAIL"
        elif tc.find("skipped") is not None:
            status = "SKIP"
        results[eq_id] = {
            "formula_id": eq_id,
            "test_name": name,
            "classname": tc.attrib.get("classname", ""),
            "time_s": tc.attrib.get("time", "0"),
            "status": status,
            "description": FORMULA_DESCRIPTIONS.get(eq_id, ""),
        }

    missing = [eq for eq in EXPECTED_FORMULAS if eq not in results]
    failed = [eq for eq in EXPECTED_FORMULAS if results.get(eq, {}).get("status") != "PASS"]

    report_json = {
        "spec_id": "IFOG-SIM-SPEC-006",
        "total_expected": len(EXPECTED_FORMULAS),
        "total_verified": len(results),
        "missing": missing,
        "failed": failed,
        "all_passed": (proc.returncode == 0 and not missing and not failed),
        "formulas": [results.get(eq, {"formula_id": eq, "status": "MISSING"}) for eq in EXPECTED_FORMULAS],
    }
    (out_dir / "formula_verification_matrix.json").write_text(
        json.dumps(report_json, indent=2), encoding="utf-8"
    )

    lines = [
        "# IFOG-SIM-SPEC-006 Formula Verification Traceability Matrix (CI/CD)",
        "",
        f"- **Expected Formulas:** {len(EXPECTED_FORMULAS)} (`EQ-01` .. `EQ-44`)",
        f"- **Verified & Passed:** {len(EXPECTED_FORMULAS) - len(failed)} / {len(EXPECTED_FORMULAS)}",
        f"- **Overall Status:** {'PASS' if report_json['all_passed'] else 'FAIL'}",
        "",
        "| Formula ID | Status | Test Function | Duration (s) | Specification Equation |",
        "| :--- | :---: | :--- | :---: | :--- |",
    ]
    for eq in EXPECTED_FORMULAS:
        entry = results.get(eq)
        if entry is None:
            lines.append(f"| `{eq}` | MISSING | — | — | {FORMULA_DESCRIPTIONS[eq]} |")
        else:
            lines.append(
                f"| `{eq}` | **{entry['status']}** | `{entry['test_name']}` | {entry['time_s']} | {entry['description']} |"
            )
    (out_dir / "formula_verification_matrix.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    if not report_json["all_passed"]:
        print(f"ERROR: Formula verification failed! missing={missing}, failed={failed}", file=sys.stderr)
        return 1

    print(f"SUCCESS: All {len(EXPECTED_FORMULAS)} formulas (EQ-01 .. EQ-44) individually verified and PASSED!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
