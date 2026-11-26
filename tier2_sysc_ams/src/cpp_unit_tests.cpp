#include <cassert>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <systemc.h>
#include "ifog_config.hpp"
#include "ifog_math.hpp"
#include "imu_3axis.hpp"
#include "micro_trace.hpp"
#include "pink_noise_tdf.hpp"
#include "sim_runner.hpp"

using namespace ifog;

#define CHECK(cond)                                                              \
    do {                                                                         \
        if (!(cond)) {                                                           \
            std::cerr << "CHECK FAILED: " #cond " at line " << __LINE__ << "\n"; \
            std::abort();                                                        \
        }                                                                        \
    } while (0)

static void expect_near(double a, double b, double tol, const char* msg) {
    if (std::fabs(a - b) > tol) {
        std::cerr << "FAIL [" << msg << "]: got " << a << " expected " << b
                  << " (diff=" << std::fabs(a - b) << " > " << tol << ")\n";
        std::abort();
    }
}

static void test_math_formulas() {
    // EQ-12 / EQ-21: wrap_2pi precision at 6.55e-9 rad
    expect_near(wrap_2pi(6.55e-9 + 200.0 * PI), 6.55e-9, 1e-13, "wrap_2pi_large");
    expect_near(wrap_2pi(-3.0 * PI + 0.25), -PI + 0.25, 1e-14, "wrap_2pi_neg");

    // EQ-06, EQ-07, EQ-08, EQ-10
    expect_near(compute_tau(1000.0, 1.468), 4.8967209175e-6, 1e-12, "compute_tau");
    expect_near(compute_k_opt(1000.0, 0.10, 1.55e-6), 1.3521580787, 1e-8, "compute_k_opt");
    expect_near(
        compute_kerr_phase(2.6e-20, 1000.0, 1.55e-6, 5e-11, 0.5005, 1e-3, 1.0),
        -2.1079073289e-6,
        1e-12,
        "compute_kerr"
    );
    expect_near(compute_faraday_phase(0.6, 1e-4, 0.5), 3e-5, 1e-15, "compute_faraday");

    // EQ-11, EQ-13
    expect_near(compute_mioc_phase(3.0, 3.0, 0.02, 1e-3), PI * 1.02 + 9e-3, 1e-12, "compute_mioc");
    expect_near(compute_pd_power(1e-4, 0.0, 0.0, 1.0, 0.0, 0.0), 1e-4, 1e-15, "compute_pd_max");
    expect_near(compute_pd_power(1e-4, 0.0, 0.0, 1.0, 0.0, PI), 0.0, 1e-15, "compute_pd_min");

    // EQ-15, EQ-16, EQ-17
    const double cf_opt = compute_tia_cf_opt(150e6, 50000.0, 3e-12);
    expect_near(cf_opt, 2.5231325e-13, 1e-18, "tia_cf_opt");
    const double w0 = compute_tia_omega0(150e6, 50000.0, 3e-12, cf_opt);
    const double zeta = compute_tia_zeta(150e6, 50000.0, 3e-12, cf_opt);
    const double ts = compute_tia_ts_0p1pct(zeta, w0);
    CHECK(w0 > 7.5e7 && w0 < 7.7e7);
    CHECK(ts > 0.0 && ts < 3.0e-7);

    const double var_i = compute_tia_noise_variance(
        5e-5, 0.95, 5e-9, 300.0, 50000.0, 7.51e12, 2e-12, 4e-9, 3e-12, cf_opt, 1.63e6
    );
    CHECK(var_i > 0.0);

    // EQ-22: Jury stability & Loop-2 separation
    CHECK(check_jury_stability(0.25));
    CHECK(!check_jury_stability(0.0));
    CHECK(!check_jury_stability(1.0));
    CHECK(check_dual_loop_separation(0.25, 0.02));
    CHECK(!check_dual_loop_separation(0.25, 0.05));

    // EQ-31: 6-state anti-periodic bias sequence & zero-crosstalk optimal angle alpha = pi/3
    {
        const double alpha6 = PI / 3.0;
        double psi[6];
        double sum_psi = 0.0;
        for (int s = 0; s < 6; ++s) {
            psi[s] = compute_6state_bias_phase(s, alpha6);
            sum_psi += psi[s];
        }
        expect_near(sum_psi, 0.0, 1e-15, "6state_zero_dc_mean");
        expect_near(psi[0] - psi[5], PI - alpha6, 1e-15, "6state_phi1");
        expect_near(psi[1] - psi[0], -(PI + alpha6), 1e-15, "6state_phi2");
        expect_near(psi[2] - psi[1], PI - alpha6, 1e-15, "6state_phi3");
        expect_near(psi[3] - psi[2], -(PI - alpha6), 1e-15, "6state_phi4");
        expect_near(psi[4] - psi[3], PI + alpha6, 1e-15, "6state_phi5");
        expect_near(psi[5] - psi[4], -(PI - alpha6), 1e-15, "6state_phi6");
        // Zero RAM/crosstalk drive sum at alpha = pi/3
        expect_near((psi[3] + psi[4] + psi[5]) - (psi[0] + psi[1] + psi[2]), 0.0, 1e-15, "6state_zero_ram");
    }

    // EQ-39: Fault window helper
    CHECK(!is_fault_active(0.001, 0.005, 0.0));
    CHECK(is_fault_active(0.005, 0.005, 0.0));
    CHECK(is_fault_active(0.006, 0.005, 0.002));
    CHECK(!is_fault_active(0.008, 0.005, 0.002));

    // Stimuli (all 4 types + Ramp-Hold)
    IfogConfig cfg;
    cfg.duration_s = 1.0;
    cfg.stimulus_type = StimulusType::Constant;
    cfg.omega_const_rad_per_s = 0.25;
    expect_near(eval_stimulus(cfg, 0.5), 0.25, 1e-15, "stim_const");

    cfg.stimulus_type = StimulusType::Step;
    cfg.omega_start_rad_per_s = 0.0;
    cfg.omega_end_rad_per_s = 1.0;
    cfg.step_time_s = 0.4;
    expect_near(eval_stimulus(cfg, 0.2), 0.0, 1e-15, "stim_step_lo");
    expect_near(eval_stimulus(cfg, 0.5), 1.0, 1e-15, "stim_step_hi");

    cfg.stimulus_type = StimulusType::Ramp;
    cfg.step_time_s = 0.0;
    expect_near(eval_stimulus(cfg, 0.5), 0.5, 1e-15, "stim_ramp_mid");
    cfg.step_time_s = 0.2;
    expect_near(eval_stimulus(cfg, 0.1), 0.5, 1e-15, "stim_ramphold_mid");
    expect_near(eval_stimulus(cfg, 0.5), 1.0, 1e-15, "stim_ramphold_hold");

    cfg.stimulus_type = StimulusType::Sine;
    cfg.omega_const_rad_per_s = 0.1;
    cfg.sine_freq_Hz = 1.0;
    cfg.sine_amp_rad_per_s = 0.5;
    expect_near(eval_stimulus(cfg, 0.25), 0.6, 1e-14, "stim_sine_peak");

    // Shupe LUT interpolation (empty, below, mid, above)
    std::vector<ShupeSample> empty_lut;
    expect_near(interpolate_shupe(empty_lut, 1.0), 0.0, 1e-15, "shupe_empty");
    std::vector<ShupeSample> lut = {{0.0, 0.0}, {10.0, 2.0e-7}, {20.0, 6.0e-7}};
    expect_near(interpolate_shupe(lut, -1.0), 0.0, 1e-15, "shupe_low");
    expect_near(interpolate_shupe(lut, 5.0), 1.0e-7, 1e-15, "shupe_mid");
    expect_near(interpolate_shupe(lut, 25.0), 6.0e-7, 1e-15, "shupe_high");

    // FastRng & PrbsLfsr32 & FivePolePinkFilter
    FastRng rng(12345ULL);
    double sum_n = 0.0;
    for (int i = 0; i < 1000; ++i) {
        sum_n += rng.normal01();
    }
    CHECK(std::isfinite(sum_n));

    PrbsLfsr32 lfsr_zero(0u);
    PrbsLfsr32 lfsr_seed(42u);
    int ones = 0;
    for (int i = 0; i < 100; ++i) {
        int b1 = lfsr_zero.next_bit_signed();
        int b2 = lfsr_seed.next_bit_signed();
        CHECK(b1 == 1 || b1 == -1);
        CHECK(b2 == 1 || b2 == -1);
        if (b2 == 1) ++ones;
    }
    CHECK(ones > 10 && ones < 90);

    FivePolePinkFilter pink(10.0, 5000.0, 4.897e-6, 1.0);
    double p_acc = 0.0;
    for (int i = 0; i < 500; ++i) {
        p_acc += pink.step(rng);
    }
    CHECK(std::isfinite(p_acc));

    // ExactSecondOrderLtf across underdamped, critically damped, and overdamped regimes
    ExactSecondOrderLtf ltf_u, ltf_c, ltf_o;
    ltf_u.configure(50000.0, 7.6e7, 0.7071, 3.06e-7, 0.0);
    ltf_c.configure(50000.0, 1.0e6, 1.0, 1.0e-7, 0.0);
    ltf_o.configure(50000.0, 1.0e6, 1.5, 1.0e-7, 0.0);
    double yu = 0.0, yc = 0.0, yo = 0.0;
    for (int i = 0; i < 500; ++i) {
        yu = ltf_u.step(1.0);
        yc = ltf_c.step(1.0);
        yo = ltf_o.step(1.0);
    }
    expect_near(yu, 50000.0, 1e-6, "ltf_underdamped_dc");
    expect_near(yc, 50000.0, 1e-3, "ltf_critical_dc");
    expect_near(yo, 50000.0, 1e-1, "ltf_overdamped_dc");
}

static void test_config_and_cli_validation() {
    // Test validate_ifog_config error paths
    auto expect_throws = [](auto fn) {
        bool threw = false;
        try {
            fn();
        } catch (const std::exception&) {
            threw = true;
        }
        CHECK(threw);
    };

    IfogConfig base;
    validate_ifog_config(base);

    {
        IfogConfig bad = base;
        bad.K_oversample = 8;
        expect_throws([&]() { validate_ifog_config(bad); });
    }
    {
        IfogConfig bad = base;
        bad.k_start = 10;
        bad.k_end = 5;
        expect_throws([&]() { validate_ifog_config(bad); });
    }
    {
        IfogConfig bad = base;
        bad.K_tot_1 = 1.2;
        expect_throws([&]() { validate_ifog_config(bad); });
    }
    {
        IfogConfig bad = base;
        bad.K_tot_2 = 0.09;
        expect_throws([&]() { validate_ifog_config(bad); });
    }
    {
        IfogConfig bad = base;
        bad.duration_s = 0.0;
        expect_throws([&]() { validate_ifog_config(bad); });
    }
    {
        IfogConfig bad = base;
        bad.V_min_V = 5.0;
        bad.V_max_V = 5.0;
        expect_throws([&]() { validate_ifog_config(bad); });
    }

    // CLI parser valid & error paths
    {
        char arg0[] = "ifog_sim";
        char arg1[] = "--phys";
        char arg2[] = "p.json";
        char arg3[] = "--cfg";
        char arg4[] = "c.json";
        char arg5[] = "--out";
        char arg6[] = "out_dir";
        char arg7[] = "--shupe";
        char arg8[] = "s.bin";
        char arg9[] = "--duration-s";
        char arg10[] = "0.5";
        char arg11[] = "--dump-micro-ms";
        char arg12[] = "1.0";
        char arg13[] = "--imu3axis";
        char* argv[] = {arg0, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9, arg10, arg11, arg12, arg13};
        CliArgs a = parse_cli_args(14, argv);
        CHECK(a.phys_path == "p.json");
        CHECK(a.cfg_path == "c.json");
        CHECK(a.out_dir == "out_dir");
        CHECK(a.shupe_path == "s.bin");
        CHECK(a.imu_3axis);
        expect_near(a.override_duration_s, 0.5, 1e-12, "cli_dur");
        expect_near(a.override_dump_micro_ms, 1.0, 1e-12, "cli_micro");
    }
    {
        char arg0[] = "ifog_sim";
        char arg1[] = "--phys";
        char* argv[] = {arg0, arg1};
        expect_throws([&]() { parse_cli_args(2, argv); });
    }
    {
        char arg0[] = "ifog_sim";
        char arg1[] = "--bogus";
        char* argv[] = {arg0, arg1};
        expect_throws([&]() { parse_cli_args(2, argv); });
    }
    {
        char arg0[] = "ifog_sim";
        char* argv[] = {arg0};
        expect_throws([&]() { parse_cli_args(1, argv); });
    }

    // Shupe LUT error paths + valid write/read
    const std::string tmp_dir = "/tmp/ifog_cpp_unit_test_tmp";
    std::filesystem::create_directories(tmp_dir);

    expect_throws([&]() { load_shupe_lut(tmp_dir + "/nonexistent.bin"); });
    {
        std::ofstream bad_hdr(tmp_dir + "/bad_hdr.bin", std::ios::binary);
        bad_hdr << "NOPE12345678901234567890";
    }
    expect_throws([&]() { load_shupe_lut(tmp_dir + "/bad_hdr.bin"); });
    {
        std::ofstream trunc(tmp_dir + "/trunc.bin", std::ios::binary);
        const char magic[4] = {'S', 'H', 'U', 'P'};
        uint32_t ver = 1u;
        uint64_t n = 5u;
        double dt = 1.0;
        trunc.write(magic, 4);
        trunc.write(reinterpret_cast<const char*>(&ver), sizeof(ver));
        trunc.write(reinterpret_cast<const char*>(&n), sizeof(n));
        trunc.write(reinterpret_cast<const char*>(&dt), sizeof(dt));
    }
    expect_throws([&]() { load_shupe_lut(tmp_dir + "/trunc.bin"); });
    {
        std::ofstream good(tmp_dir + "/good.bin", std::ios::binary);
        const char magic[4] = {'S', 'H', 'U', 'P'};
        uint32_t ver = 1u;
        uint64_t n = 2u;
        double dt = 10.0;
        double t0 = 0.0, p0 = 1e-7, t1 = 10.0, p1 = 2e-7;
        good.write(magic, 4);
        good.write(reinterpret_cast<const char*>(&ver), sizeof(ver));
        good.write(reinterpret_cast<const char*>(&n), sizeof(n));
        good.write(reinterpret_cast<const char*>(&dt), sizeof(dt));
        good.write(reinterpret_cast<const char*>(&t0), sizeof(double));
        good.write(reinterpret_cast<const char*>(&p0), sizeof(double));
        good.write(reinterpret_cast<const char*>(&t1), sizeof(double));
        good.write(reinterpret_cast<const char*>(&p1), sizeof(double));
    }
    auto loaded = load_shupe_lut(tmp_dir + "/good.bin");
    CHECK(loaded.size() == 2u);
    expect_near(loaded[1].delta_phi_rad, 2e-7, 1e-16, "shupe_lut_read");

    // MicroTraceCollector, DspTraceCollector & summary error paths
    expect_throws([&]() { MicroTraceCollector("/nonexistent_dir_xyz/micro.bin", 1e-3, 16); });
    expect_throws([&]() { DspTraceCollector("/nonexistent_dir_xyz/dsp_trace.bin", true); });
    {
        DspTraceCollector disabled_tr("", false);
        DspTraceRecord dummy{};
        disabled_tr.push(dummy);
        CHECK(disabled_tr.records_written() == 0u);
    }
    expect_throws([&]() {
        SimSummary s{};
        write_sim_summary_json("/nonexistent_dir_xyz/sum.json", s);
    });
    expect_throws([&]() {
        Imu3AxisSummary im{};
        write_imu_3axis_summary_json("/nonexistent_dir_xyz/imu.json", im);
    });
    expect_throws([&]() { load_ifog_config("/nonexistent_cfg.json", "/nonexistent_phys.json"); });

    // Create minimal valid cfg json but nonexistent phys json
    {
        std::ofstream cf(tmp_dir + "/min_cfg.json");
        cf << "{}";
    }
    expect_throws([&]() { load_ifog_config(tmp_dir + "/min_cfg.json", "/nonexistent_phys.json"); });

    // SPEC-007 EQ-47..EQ-52 C++ math & LUT v2 unit tests
    {
        const double k_dyn = compute_dynamic_k_opt(1.352, 20.0, 5.0, 12.0, 35.0, 1.55e-6, 1.5e-9, 1e-6, 1.468, 1e-5);
        CHECK(k_dyn > 1.352);

        // EQ-51 capacitive crosstalk & C_xtalk=0 reduction
        const double i_cap = compute_capacitive_crosstalk_A(1.5, 0.0, 3.0e-7, 1.5e-8, 5.0e-12);
        const double i_res = compute_capacitive_crosstalk_A(1.5, 0.0, 3.0e-7, 1.5e-8, 0.0);
        expect_near(i_res, 2.25e-8, 1e-18, "eq51_zero_cap_reduction");
        expect_near(i_cap - i_res, 5.0e-12 * (1.5 / 3.0e-7), 1e-18, "eq51_cap_spike");

        // EQ-52 backscatter sigma (finite & -200 dB silent floor)
        CHECK(compute_backscatter_sigma_rad(-60.0, 4.5e-5, 1.5e-3, 7.51e12) > 1e-3);
        expect_near(compute_backscatter_sigma_rad(-200.0, 0.0, 0.0, 7.51e12), 0.0, 1e-18, "eq52_zero");

        // EQ-50 MiocDynamicsFilter: inactive passthrough, elec-only, acoustic-only, combined
        MiocDynamicsFilter mf_idle;
        expect_near(step_mioc_dynamics(mf_idle, 1.25), 1.25, 1e-15, "mioc_idle");
        MiocDynamicsFilter mf_elec;
        mf_elec.configure(10e6, 0.0, 0.1, 0.0, 3e-7, 0.0);
        CHECK(mf_elec.active() && step_mioc_dynamics(mf_elec, 1.0) > 0.0);
        MiocDynamicsFilter mf_ac;
        mf_ac.configure(0.0, 3.5e6, 0.08, 0.05, 3e-7, 0.0);
        CHECK(mf_ac.active() && step_mioc_dynamics(mf_ac, 1.0) > 0.0);

        // EQ-49 LUT v2 write, read, and O(1) interpolation (empty, before start, mid, after end)
        std::vector<ShupeLutRecordV2> empty_v2;
        expect_near(interpolate_shupe_v2(empty_v2, 5.0).k_opt_scale_rel_t, 1.0, 1e-15, "lut_v2_empty");
        {
            std::ofstream v2f(tmp_dir + "/good_v2.bin", std::ios::binary);
            const char magic[4] = {'S', 'H', 'U', 'P'};
            uint32_t ver = 2u;
            uint64_t n = 2u;
            double dt = 10.0;
            v2f.write(magic, 4);
            v2f.write(reinterpret_cast<const char*>(&ver), sizeof(ver));
            v2f.write(reinterpret_cast<const char*>(&n), sizeof(n));
            v2f.write(reinterpret_cast<const char*>(&dt), sizeof(dt));
            ShupeLutRecordV2 r0{0.0, 1e-7, 2e-8, 0.999, 1e-8, 3.0, 1.0};
            ShupeLutRecordV2 r1{10.0, 3e-7, 6e-8, 0.997, 3e-8, 3.02, 1.0001};
            v2f.write(reinterpret_cast<const char*>(&r0), sizeof(r0));
            v2f.write(reinterpret_cast<const char*>(&r1), sizeof(r1));
        }
        uint32_t det_ver = 0u;
        auto v2_loaded = load_shupe_lut_v2(tmp_dir + "/good_v2.bin", &det_ver);
        CHECK(det_ver == 2u && v2_loaded.size() == 2u);
        expect_near(interpolate_shupe_v2(v2_loaded, -1.0).v_pi_V_t, 3.0, 1e-15, "lut_v2_lo");
        expect_near(interpolate_shupe_v2(v2_loaded, 5.0).delta_phi_stress_rad, 4e-8, 1e-15, "lut_v2_mid");
        expect_near(interpolate_shupe_v2(v2_loaded, 20.0).k_opt_scale_rel_t, 1.0001, 1e-15, "lut_v2_hi");

        // SPEC-007 fail-closed validation guard in validate_ifog_config
        IfogConfig bad_sp7;
        bad_sp7.spec007.R_facet_dB = 5.0;
        expect_throws([&]() { validate_ifog_config(bad_sp7); });
    }

    std::filesystem::remove_all(tmp_dir);
}

static void test_gate1_closed_loop_systemc_ams() {
    // Golden Linear Baseline Gate 1 inside C++ unit tests:
    // Ideal linear closed-loop with Delta_phi_S = 1e-8 rad and eps_vpi = 2% locked by Loop-2
    IfogConfig cfg;
    cfg.seed = 42004;
    cfg.K_opt = compute_k_opt(cfg.L_m, cfg.D_m, cfg.lambda_bar_m);
    cfg.tau_s = compute_tau(cfg.L_m, cfg.n_eff);
    cfg.visibility_V = 1.0;
    cfg.phi_pol_rad = 0.0;
    cfg.delta_phi_kerr_rad = 0.0;
    cfg.eps_vpi = 0.02;
    cfg.gamma_nl_rad_per_V2 = 0.0;
    cfg.dsp_mode = DspMode::FourState;
    cfg.K_tot_1 = 0.25;
    cfg.K_tot_2 = 0.02;
    cfg.en_adc_blanking = true;
    cfg.en_vpi_loop = true;
    cfg.en_prbs_dither = false;
    cfg.en_white_noise = false;
    cfg.en_pink_noise = false;

    // Disable all nonlinearities except MIOC V_pi error (so Loop-2 locking is verified simultaneously!)
    cfg.ablation.en_pol_error = false;
    cfg.ablation.en_kerr = false;
    cfg.ablation.en_shupe = false;
    cfg.ablation.en_faraday = false;
    cfg.ablation.en_mioc_vpi_err = true;
    cfg.ablation.en_ram = false;
    cfg.ablation.en_xtalk = false;
    cfg.ablation.en_ltf_transient = false;
    cfg.ablation.en_tia_poly_nl = false;
    cfg.ablation.en_quantization = false;

    const double target_dphi = 1.0e-8;
    cfg.stimulus_type = StimulusType::Constant;
    cfg.omega_const_rad_per_s = target_dphi / cfg.K_opt;
    cfg.duration_s = 0.02;  // 4084 tau (~1021 4-state frames) -> converges to < 1e-13!
    cfg.decimation_tau = 4;
    cfg.dump_micro_ms = 0.1;

    const std::string out_dir = "/tmp/ifog_cpp_gate1_out";
    SimSummary s = run_ifog_simulation(cfg, out_dir);

    std::cout << "[cpp_unit_tests] Gate1: final_dphi=" << s.final_delta_phi_step_rad
              << " err=" << std::fabs(s.final_delta_phi_step_rad - target_dphi)
              << " eps_vpi_eff=" << s.final_eps_vpi_eff << "\n";

    assert(s.total_tau_steps > 3000);
    assert(s.total_records_written > 700);
    assert(s.total_micro_records > 0);
    expect_near(s.final_delta_phi_step_rad, target_dphi, 1.0e-9, "gate1_dphi_static_err");
    expect_near(s.final_eps_vpi_eff, 0.0, 1.0e-5, "gate1_vpi_lock");

    std::filesystem::remove_all(out_dir);
}

int sc_main(int, char*[]) {
    test_math_formulas();
    test_config_and_cli_validation();
    test_gate1_closed_loop_systemc_ams();
    std::cout << "[cpp_unit_tests] ALL PASSED\n";
    return 0;
}
