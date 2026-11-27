// =============================================================================
// IFOG-VPROTO v4.1.0 — Synthesizable SystemVerilog-2012 Reference RTL (IND-02)
// Official 6-State Symmetric Closed-Loop IFOG Digital Signal Processor
// Fixed-Point Architecture: Signed Q16.32 (48-bit) Loop-1/Loop-2 Accumulators
// Conforms to IFOG-SIM-SPEC-005 (EQ-31..EQ-34) & DO-254 Bit-True Traceability
// =============================================================================
`timescale 1ns/1ps

module ifog_dsp_6state #(
    parameter int ADC_WIDTH   = 16,
    parameter int DAC_WIDTH   = 16,
    parameter int ACC_WIDTH   = 48,   // Signed Q16.32 accumulator
    parameter int FRAC_BITS   = 32,
    // 2*pi in Q16.32: round(2 * pi * 2^32) = 26986075409 (0x0006_487E_D511)
    parameter logic signed [ACC_WIDTH-1:0] TWO_PI_FXP = 48'sd26986075409,
    // +pi in Q16.32: round(pi * 2^32) = 13493037705
    parameter logic signed [ACC_WIDTH-1:0] PI_FXP     = 48'sd13493037705
) (
    input  logic                         clk,
    input  logic                         rst_n,
    input  logic                         adc_valid,
    input  logic signed [ADC_WIDTH-1:0]  adc_code,
    input  logic [2:0]                   rx_state_idx,   // 0..1 (2s), 0..3 (4s), 0..5 (6s)
    input  logic [1:0]                   dsp_mode_sel,   // 2'd0=2-State, 2'd1=4-State, 2'd2=6-State
    input  logic                         en_vpi_loop,
    // Signed Q16.32 gains: k_i1_fxp = round(K_I1 * 2^32), k_i2_fxp = round(K_I2 * 2^32)
    input  logic signed [ACC_WIDTH-1:0]  k_i1_fxp,
    input  logic signed [ACC_WIDTH-1:0]  k_i2_fxp,
    input  logic signed [ACC_WIDTH-1:0]  max_dphi_fxp,
    input  logic signed [ACC_WIDTH-1:0]  g_dac_min_fxp,
    input  logic signed [ACC_WIDTH-1:0]  g_dac_max_fxp,
    input  logic signed [ACC_WIDTH-1:0]  g_dac_init_fxp,

    output logic                         frame_valid,
    output logic signed [ACC_WIDTH-1:0]  delta_phi_step_fxp, // Q16.32 [rad]
    output logic signed [ACC_WIDTH-1:0]  phi_ramp_fxp,       // Q16.32 [-pi, +pi]
    output logic signed [ACC_WIDTH-1:0]  g_dac_fxp,          // Q16.32 [1]
    output logic signed [ADC_WIDTH+3:0]  e_omega_out,
    output logic signed [ADC_WIDTH+3:0]  e_vpi_out,
    output logic signed [ADC_WIDTH+3:0]  e_asym_out,
    output logic                         flyback_pulse,
    output logic                         anti_windup_flag
);

    // 6-slot frame capture register bank y[0..5]
    logic signed [ADC_WIDTH-1:0] y_frame [0:5];
    logic                        is_frame_end;

    // Widened signed demodulation sums (zero overflow margin)
    logic signed [ADC_WIDTH+3:0] e_omega_comb;
    logic signed [ADC_WIDTH+3:0] e_vpi_comb;
    logic signed [ADC_WIDTH+3:0] e_asym_comb;

    // 64-bit signed multiply-accumulate temporaries
    logic signed [63:0] dphi_prod;
    logic signed [63:0] dphi_next_wide;
    logic signed [63:0] gdac_prod;
    logic signed [63:0] gdac_next_wide;
    logic signed [ACC_WIDTH-1:0] dphi_clamped;
    logic signed [ACC_WIDTH-1:0] gdac_clamped;
    logic signed [ACC_WIDTH:0]   ramp_sum;

    // Multi-Mode Orthogonal Demodulation: 2-State (EQ-20), 4-State (EQ-03), 6-State (EQ-33)
    always_comb begin
        unique case (dsp_mode_sel)
            2'd0: begin // 2-State Square-Wave (Loop-1 only)
                is_frame_end = (rx_state_idx == 3'd1);
                e_omega_comb = adc_code - y_frame[0];
                e_vpi_comb   = '0;
                e_asym_comb  = '0;
            end
            2'd1: begin // 4-State Lefevre Dual-Loop
                is_frame_end = (rx_state_idx == 3'd3);
                e_omega_comb = (y_frame[1] - y_frame[0]) + (adc_code - y_frame[2]);
                e_vpi_comb   = (y_frame[2] + adc_code) - (y_frame[0] + y_frame[1]);
                e_asym_comb  = '0;
            end
            default: begin // 6-State Official Anti-Periodic Symmetric 3-Channel
                is_frame_end = (rx_state_idx == 3'd5);
                e_omega_comb = (y_frame[3] + y_frame[4] + adc_code)
                             - (y_frame[0] + y_frame[1] + y_frame[2]);
                e_vpi_comb   = ( (y_frame[1] + y_frame[4]) <<< 1 )
                             - (y_frame[0] + y_frame[2] + y_frame[3] + adc_code);
                e_asym_comb  = (y_frame[0] - y_frame[2]) + (adc_code - y_frame[3]);
            end
        endcase

        // Loop-1 integrator step (Q16.32): delta_phi_step + K_I1 * e_omega
        dphi_prod      = $signed(e_omega_comb) * $signed(k_i1_fxp);
        dphi_next_wide = $signed({{16{delta_phi_step_fxp[ACC_WIDTH-1]}}, delta_phi_step_fxp}) + dphi_prod;
        if (dphi_next_wide > $signed({{16{max_dphi_fxp[ACC_WIDTH-1]}}, max_dphi_fxp})) begin
            dphi_clamped = max_dphi_fxp;
        end else if (dphi_next_wide < -$signed({{16{max_dphi_fxp[ACC_WIDTH-1]}}, max_dphi_fxp})) begin
            dphi_clamped = -max_dphi_fxp;
        end else begin
            dphi_clamped = dphi_next_wide[ACC_WIDTH-1:0];
        end

        // Loop-2 V_pi gain tracker (Q16.32): g_dac - K_I2 * e_vpi
        gdac_prod      = $signed(e_vpi_comb) * $signed(k_i2_fxp);
        gdac_next_wide = $signed({{16{g_dac_fxp[ACC_WIDTH-1]}}, g_dac_fxp}) - gdac_prod;
        if (gdac_next_wide > $signed({{16{g_dac_max_fxp[ACC_WIDTH-1]}}, g_dac_max_fxp})) begin
            gdac_clamped = g_dac_max_fxp;
        end else if (gdac_next_wide < $signed({{16{g_dac_min_fxp[ACC_WIDTH-1]}}, g_dac_min_fxp})) begin
            gdac_clamped = g_dac_min_fxp;
        end else begin
            gdac_clamped = gdac_next_wide[ACC_WIDTH-1:0];
        end

        // EQ-21: Digital phase ramp modulo-2*pi flyback accumulation
        ramp_sum = $signed({phi_ramp_fxp[ACC_WIDTH-1], phi_ramp_fxp})
                 + $signed({dphi_clamped[ACC_WIDTH-1], dphi_clamped});
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (int i = 0; i < 6; i++) begin
                y_frame[i] <= '0;
            end
            delta_phi_step_fxp <= '0;
            phi_ramp_fxp       <= '0;
            g_dac_fxp          <= g_dac_init_fxp;
            e_omega_out        <= '0;
            e_vpi_out          <= '0;
            e_asym_out         <= '0;
            frame_valid        <= 1'b0;
            flyback_pulse      <= 1'b0;
            anti_windup_flag   <= 1'b0;
        end else if (adc_valid) begin
            y_frame[rx_state_idx] <= adc_code;
            frame_valid           <= is_frame_end;
            flyback_pulse         <= 1'b0;
            anti_windup_flag      <= 1'b0;

            if (is_frame_end) begin
                e_omega_out        <= e_omega_comb;
                e_vpi_out          <= e_vpi_comb;
                e_asym_out         <= e_asym_comb;
                delta_phi_step_fxp <= dphi_clamped;
                anti_windup_flag   <= (dphi_next_wide > $signed({{16{max_dphi_fxp[ACC_WIDTH-1]}}, max_dphi_fxp})) ||
                                      (dphi_next_wide < -$signed({{16{max_dphi_fxp[ACC_WIDTH-1]}}, max_dphi_fxp}));
                if (en_vpi_loop && (dsp_mode_sel != 2'd0)) begin
                    g_dac_fxp <= gdac_clamped;
                end
            end

            // Update phase ramp every tau cycle with modulo-2*pi flyback wrapping
            if (ramp_sum > $signed({1'b0, PI_FXP})) begin
                phi_ramp_fxp  <= ramp_sum[ACC_WIDTH-1:0] - TWO_PI_FXP;
                flyback_pulse <= 1'b1;
            end else if (ramp_sum < -$signed({1'b0, PI_FXP})) begin
                phi_ramp_fxp  <= ramp_sum[ACC_WIDTH-1:0] + TWO_PI_FXP;
                flyback_pulse <= 1'b1;
            end else begin
                phi_ramp_fxp  <= ramp_sum[ACC_WIDTH-1:0];
            end
        end
    end

endmodule
