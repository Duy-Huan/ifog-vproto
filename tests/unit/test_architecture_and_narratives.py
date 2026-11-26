"""100% Unit Coverage Tests for viz/architecture_explorer.py & viz/report_narratives.py."""

from __future__ import annotations

import json
from pathlib import Path

from viz.architecture_explorer import (
    ARCHITECTURE_NODES,
    CODE_AUDIT_ROWS,
    main as arch_main,
    render_architecture_explorer_html,
    write_architecture_explorer,
)
from viz.report_narratives import (
    FIGURE_GUIDES,
    _md_inline_to_html,
    get_figure_narrative,
    render_narrative_html,
    render_narrative_markdown,
)


def _full_mock_summary() -> dict:
    return {
        "report_meta": {"run_id": "unit_full", "overall_status": "PASS", "version": "3.0.1"},
        "phys_params": {
            "K_opt_rad_per_rad_s": 1.6223,
            "tau_s": 4.896721e-6,
            "visibility_V": 0.999999,
        },
        "sim_summary": {
            "total_tau_steps": 1000,
            "flyback_count": 1200,
            "adc_clip_count": 0,
            "final_eps_vpi_eff": 1e-12,
        },
        "gate1_metrics": {
            "small_signal_err_rad": 3.1e-16,
            "flyback_count": 1666,
            "final_eps_vpi_eff": 5.8e-14,
        },
        "nonlinearity_summary": {
            "deadband_reduction_pct": 98.85,
            "bunny_ears_sf_reduction_pct": 98.85,
        },
        "gate3_metrics": {
            "slope_linear": -0.062,
            "slope_nonlinear": -0.893,
            "k_repeatability_max_rel_pct": 0.0,
        },
        "avar_metrics": {
            "overlap_check": {"max_relative_mismatch_pct": 2.42},
            "fitted_ieee952": {
                "Q_arcsec": 0.0021,
                "N_deg_per_rt_h": 0.00038,
                "B_deg_per_h": 0.0040,
                "K_deg_per_rt_h3": 0.0205,
                "R_deg_per_h2": 0.0273,
            },
        },
        "dsp6_compare": {
            "four_state": {"ram_xtalk_bias_deg_per_h": 354.56},
            "six_state": {"ram_xtalk_bias_deg_per_h": 5.04e-5, "static_err_rad": 1.28e-16},
            "ram_xtalk_rejection_dB": 136.94,
            "peak_voltage_reduction_pct": 33.3,
        },
        "fmi_gate": {
            "equivalence": {"max_final_omega_err_rad_per_s": 0.0},
            "deadband": {"deadband_reduction_pct": 97.42},
            "avar": {"overlap_check": {"max_relative_mismatch_pct": 3.83}},
        },
        "td_scenarios": {
            "TD-01": {
                "tia_ts_0p1pct_ns": 174.1,
                "k_start_optimal_0p5pct": 5,
                "clean_window_max_err_pct": 2.978,
                "arw_blanking_penalty_factor": 1.155,
            },
            "TD-02": {
                "rise_time_10_90_ms": 0.22,
                "overshoot_pct": 0.0,
                "bw_3db_measured_Hz": 2540.0,
                "bw_3db_theory_Hz": 2354.0,
            },
            "TD-03": {
                "four_state": {"final_eps_vpi_eff": 1.78e-15},
                "six_state": {"final_eps_vpi_eff": 1.68e-11, "convergence_99pct_ms": 6.3},
            },
            "TD-04": {
                "hold_700_err_pct": 0.0003,
                "flyback_count": 7184,
                "flyback_rate_kHz": 179.6,
                "anti_windup_flag_count": 200,
            },
            "TD-05": {
                "peak_uncompensated_bias_deg_per_h": 1483.6,
                "truth_correlation_r": 1.0,
                "thermal_compensation_reduction_pct": 99.74,
            },
            "TD-06": {
                "without_dither": {"unique_dac_codes": 3},
                "with_dither": {"unique_dac_codes": 1595},
                "bias_err_reduction_pct": 3.6,
            },
        },
        "eng_scenarios": {
            "ENG-01": {
                "recommended_min_bits": 12,
                "jitter_sweep": [{"arw_degradation_pct": 2216.3}],
                "pareto_optimal": {"arw_deg_per_rt_h": 1.41e-4},
            },
            "ENG-02": {
                "peak_rail_droop_V": 0.0924,
                "inter_axis_y_crosstalk_4state_deg_per_h": 40.63,
                "inter_axis_y_crosstalk_6state_deg_per_h": 0.1064,
            },
            "ENG-03": {
                "vre": {"vre_coeff_nonlinear_deg_h_per_g2": -0.3486},
                "faraday": {
                    "sensitivity_measured_deg_h_per_G": 0.183,
                    "required_mumetal_shield_dB_for_1G_0p01degh": 25.3,
                },
            },
            "ENG-04": {
                "cases": [
                    {"time_to_alert_us": 0.62, "fdir_recovered": False},
                    {"time_to_alert_us": 30.0, "fdir_recovered": True},
                ]
            },
            "ENG-05": {
                "monte_carlo": {"n_runs": 500, "yield_pct": 97.2, "cpk_bias_1degh": 0.604},
                "virtual_calibration": {"poly_reduction_pct": 99.98, "ekf_reduction_pct": 99.95},
            },
        },
        "dyn_scenarios": {
            "DYN-01": {
                "cases": {
                    "step10_6state": {"rise_time_10_90_ms": 0.206},
                    "step100_6state": {"rise_time_10_90_ms": 0.294, "overshoot_pct": 0.0},
                },
                "max_steady_state_err_pct": 0.0,
            },
            "DYN-02": {
                "four_state": {"bw_3db_measured_Hz": 2544.0, "low_freq_group_delay_us": 65.2},
                "six_state": {"bw_3db_measured_Hz": 1642.0, "low_freq_group_delay_us": 103.3},
                "bw_ratio_4state_to_6state": 1.55,
            },
            "DYN-03": {
                "regimes": {"white_linear": {"measured_arw_deg_per_rt_h": 0.000352, "hf_rolloff_dB": -13.5}},
                "arw_white_meas_to_theory_ratio": 0.97,
                "low_freq_6state_suppression_dB": 29.2,
            },
            "DYN-04": {
                "sine_tracking_gain": 0.9889,
                "sine_phase_lag_deg": -9.36,
                "output_thd_dB": -67.5,
                "output_sfdr_dB": 43.6,
                "peak_phi_sagnac_rad": 1.18,
                "flyback_count": 391,
                "pd_demod_to_phi_err_corr": 0.996,
            },
        },
        "spec007_scenarios": {
            "PHY-01": {
                "octupole_drift_reduction_pct": 47.7,
                "quadrupole_peak_therm_deg_per_h": 0.556,
                "octupole_peak_therm_deg_per_h": 0.291,
                "lut_roundtrip_err_rad": 0.0,
                "k_opt_thermal_drift_ppm": 85.6,
                "v_tia_cap_spike_diff_rms_V": 0.583,
                "sigma_phi_back_rad": 3.56e-3,
                "bi_quadrature_conservation_err_rad_s": 0.0,
                "passed": True,
            },
            "CAL-01": {
                "error_before_pct": {
                    "avar_nrmse_pct": 40.2,
                    "deadband_nrmse_pct": 102.7,
                    "thermal_bias_nrmse_pct": 58.8,
                },
                "error_after_pct": {
                    "avar_nrmse_pct": 0.81,
                    "deadband_nrmse_pct": 0.91,
                    "thermal_bias_nrmse_pct": 0.29,
                },
                "max_param_recovery_err_pct": 2.18,
                "tier2_closed_loop_rate_err_pct": 0.034,
                "passed": True,
            },
        },
    }


def test_architecture_explorer_rendering_live_banners_and_cli(tmp_path: Path) -> None:
    """Exercise all render paths, live banner chips (PASS/FAIL/INFO/empty), and CLI."""
    assert len(ARCHITECTURE_NODES) == 12
    assert len(CODE_AUDIT_ROWS) == 10

    # Standalone without summary
    standalone_html = render_architecture_explorer_html(version="4.0.0")
    assert "SPEC-007 v4.0.0" in standalone_html
    assert "AnalogFrontEnd_TDF" in standalone_html
    assert "ifog_core.fmu" in standalone_html
    assert "<div class='live-banner'>" not in standalone_html

    # Empty dict & dict with no populated chips
    assert "<div class='live-banner'>" not in render_architecture_explorer_html(summary={})
    assert "<div class='live-banner'>" not in render_architecture_explorer_html(summary={"report_meta": {}})

    # Full summary with PASS + back link
    full_sum = _full_mock_summary()
    with_back = render_architecture_explorer_html(
        version="4.0.0", summary=full_sum, back_report_href="report.html"
    )
    assert "chip-pass" in with_back
    assert "Quay lại Báo cáo" in with_back
    assert "FMU Equiv Err" in with_back

    # FAIL and INFO status chip branches
    assert "chip-fail" in render_architecture_explorer_html(
        summary={"report_meta": {"overall_status": "FAIL"}}
    )
    assert "chip-info" in render_architecture_explorer_html(
        summary={"report_meta": {"overall_status": "INFO"}}
    )

    # write_architecture_explorer & CLI with and without --summary-json
    out1 = write_architecture_explorer(tmp_path / "sub" / "arch.html", version="4.0.0")
    assert out1.exists() and out1.stat().st_size > 10_000

    sum_path = tmp_path / "metrics_summary.json"
    sum_path.write_text(json.dumps(full_sum), encoding="utf-8")
    out2 = tmp_path / "arch_cli.html"
    assert arch_main(["--out", str(out2), "--version", "4.0.0", "--summary-json", str(sum_path)]) == 0
    assert "unit_full" in out2.read_text(encoding="utf-8")

    out3 = tmp_path / "arch_cli_plain.html"
    assert arch_main(["--out", str(out3), "--version", "4.0.0"]) == 0
    assert out3.exists()


def test_report_narratives_all_21_figures_and_fallbacks() -> None:
    """Cover every single one of the 23 figure stems, sim_summary fallback, unknown stem, and inline formatter."""
    assert len(FIGURE_GUIDES) == 23
    full_sum = _full_mock_summary()

    for stem in FIGURE_GUIDES:
        info = get_figure_narrative(stem, full_sum)
        assert info["title"] and info["eq_refs"] and info["theory"] and info["plain_meaning"]
        assert "ĐẠT" in info["what_it_proves"]

        md_lines = render_narrative_markdown(stem, full_sum)
        assert len(md_lines) == 4
        assert "Cơ sở lý thuyết" in md_lines[1]

        html_box = render_narrative_html(stem, full_sum)
        assert "explain-box" in html_box
        assert "Cơ sở Lý thuyết" in html_box

    # Waveforms fallback to sim_summary only (without gate1_metrics)
    wf_sim_only = get_figure_narrative("waveforms", {"sim_summary": full_sum["sim_summary"]})
    assert "1,000" in wf_sim_only["what_it_proves"]

    # Waveforms & unknown stem fallback with empty summary
    wf_empty = get_figure_narrative("waveforms", {})
    assert "mô phỏng vật lý thực" in wf_empty["what_it_proves"]
    unk = get_figure_narrative("custom_unknown_plot", {})
    assert unk["title"] == "Custom Unknown Plot"
    assert "mô phỏng vật lý thực" in unk["what_it_proves"]

    # Inline markdown converter edge cases (closed bold/code + unclosed ** / `)
    assert _md_inline_to_html("**bold** and `code` and **unclosed and `tick") == (
        "<strong>bold</strong> and <code>code</code> and **unclosed and `tick"
    )
