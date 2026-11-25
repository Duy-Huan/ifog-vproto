# Simulation Reports Directory (`report/`)

All simulation runs executed via [`scripts/run_sim.sh`](../scripts/run_sim.sh) or [`scripts/run_sim.py`](../scripts/run_sim.py) automatically generate both **Markdown (`.md`)** and **Interactive HTML (`.html`)** reports inside this directory:

```text
report/
├── README.md                 # Tracked guide (this file)
├── index.md                  # Auto-generated Markdown index of all runs
├── index.html                # Auto-generated HTML dashboard of all runs
└── <run_id>/
    ├── report.md             # Full Markdown diagnostic & Gate pass/fail report
    ├── report.html           # Interactive Plotly HTML5 report + KPI tables + figures
    ├── metrics_summary.json  # Complete structured JSON metrics bundle
    └── figures/              # 300-DPI PNG plots (waveforms, bunny_ears, psd_flicker, avar_5regions)
```

## Quick Usage

```bash
# Single baseline closed-loop run + auto report in report/
./scripts/run_sim.sh --mode single --run-id baseline_check

# Run individual acceptance gates (gate1, gate2, gate3, gate4) or full 4-Gate suite
./scripts/run_sim.sh --mode gate1
./scripts/run_sim.sh --mode full --run-id release_v1_1_0

# Re-export reports from an existing data/ run into report/
python3 viz/export_report.py --run data/run01 --report-dir report/run01 --format png,md,html --update-index
```

Generated run artifacts (`report/*` except this `README.md`) are excluded from Git via `.gitignore`.
