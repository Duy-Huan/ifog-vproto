#ifndef MICRO_TRACE_HPP
#define MICRO_TRACE_HPP

#include <cstdint>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>
#include "ifog_types.hpp"

namespace ifog {

// Collects optional local-window micro-sample traces (K samples per tau) for plot_waveforms.py
class MicroTraceCollector {
public:
    MicroTraceCollector(const std::string& out_path, double max_time_s, int K)
        : enabled_(max_time_s > 0.0),
          max_time_s_(max_time_s),
          K_(K),
          records_written_(0),
          current_phi_ramp_(0.0),
          current_dac_code_(0),
          buf_(static_cast<size_t>(K)) {
        if (enabled_) {
            ofs_.open(out_path, std::ios::binary | std::ios::trunc);
            if (!ofs_.is_open()) {
                throw std::runtime_error("Cannot open micro_waveforms.bin: " + out_path);
            }
        }
    }

    bool active_at(double t_s) const {
        return enabled_ && (t_s <= max_time_s_);
    }

    void set_optical(int k, double t, double v_drv, double p_det) {
        auto& r = buf_[static_cast<size_t>(k)];
        r.t = t;
        r.v_drv = v_drv;
        r.p_det = p_det;
        r.k_idx = static_cast<uint32_t>(k);
        r.dac_code = current_dac_code_;
    }

    void set_analog(int k, double v_tia, double v_adc) {
        auto& r = buf_[static_cast<size_t>(k)];
        r.v_tia = v_tia;
        r.v_adc = v_adc;
    }

    void set_dsp_state(double phi_ramp, int32_t dac_code) {
        current_phi_ramp_ = phi_ramp;
        current_dac_code_ = dac_code;
    }

    void flush_cluster(int32_t adc_code, int k_start, int k_end) {
        for (int k = 0; k < K_; ++k) {
            auto& r = buf_[static_cast<size_t>(k)];
            r.phi_ramp = current_phi_ramp_;
            r.adc_code = adc_code;
            r.in_blanking = (k >= k_start && k <= k_end) ? 1u : 0u;
            r.dac_code = current_dac_code_;
        }
        ofs_.write(
            reinterpret_cast<const char*>(buf_.data()),
            static_cast<std::streamsize>(buf_.size() * sizeof(MicroRecord))
        );
        records_written_ += static_cast<uint64_t>(K_);
    }

    uint64_t records_written() const {
        return records_written_;
    }

private:
    bool enabled_;
    double max_time_s_;
    int K_;
    uint64_t records_written_;
    double current_phi_ramp_;
    int32_t current_dac_code_;
    std::vector<MicroRecord> buf_;
    std::ofstream ofs_;
};

// Optional buffered internal DSP register logger (64 bytes per tau, IFOG-SIM-SPEC-005)
class DspTraceCollector {
public:
    DspTraceCollector(const std::string& out_path, bool enabled)
        : enabled_(enabled), records_written_(0) {
        if (enabled_) {
            buf_.reserve(4096);
            ofs_.open(out_path, std::ios::binary | std::ios::trunc);
            if (!ofs_.is_open()) {
                throw std::runtime_error("Cannot open dsp_trace.bin: " + out_path);
            }
        }
    }

    ~DspTraceCollector() {
        flush();
    }

    bool enabled() const {
        return enabled_;
    }

    void push(const DspTraceRecord& rec) {
        if (!enabled_) {
            return;
        }
        buf_.push_back(rec);
        if (buf_.size() >= 4096u) {
            flush();
        }
    }

    void flush() {
        if (!buf_.empty() && ofs_.is_open()) {
            ofs_.write(
                reinterpret_cast<const char*>(buf_.data()),
                static_cast<std::streamsize>(buf_.size() * sizeof(DspTraceRecord))
            );
            records_written_ += buf_.size();
            buf_.clear();
        }
    }

    uint64_t records_written() const {
        return records_written_;
    }

private:
    bool enabled_;
    uint64_t records_written_;
    std::vector<DspTraceRecord> buf_;
    std::ofstream ofs_;
};

}  // namespace ifog

#endif  // MICRO_TRACE_HPP
