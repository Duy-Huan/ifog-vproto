---
name: ifog-spec-formula-verification
description: Verify all 30 mathematical formulas (EQ-01..EQ-30) in IFOG-SIM-SPEC-004, enforce sign conventions, unit conversions, exact Jury stability bounds, and CI/CD traceability matrix generation.
---

# IFOG Specification Formula Verification (`EQ-01` .. `EQ-30`)

## 1. Normative Source & Immutability Lock
- Normative spec: `spec/IFOG-SIM-SPEC-004.tex` (compiled to `spec/IFOG-SIM-SPEC-004.pdf` via 3-pass `lualatex` with Noto Sans Vietnamese fonts).
- **Rule 7:** NEVER edit `spec/IFOG-SIM-SPEC-004.tex` without explicit project owner approval. Always check integrity first:
  ```bash
  sha256sum -c spec/IFOG-SIM-SPEC-004.sha256
  ```

## 2. Critical Mathematical Pitfalls Discovered & Locked

1. **4-State Demodulation Sign Correction (`EQ-01`..`EQ-03`, Lefèvre Ch. 8):**
   - With differential bias sequence $[+(\pi-\alpha), -(\pi-\alpha), -(\pi+\alpha), +(\pi+\alpha)]$:
     - **CORRECT:** $e_\Omega = (y_2 - y_1) + (y_4 - y_3) \approx 4 S_\alpha \Delta\phi_{\text{NR}}$ and $e_{V_\pi} = (y_3 + y_4) - (y_1 + y_2) \approx 4\pi S_\alpha \epsilon_{V_\pi}$.
     - **WRONG (legacy SPEC-003 bug):** $(y_2 - y_1) + (y_3 - y_4)$ cancels $\Delta\phi_{\text{NR}}$ to $0$.
     - `test_eq03_orthogonal_four_state_demodulation_sign_correction` explicitly asserts BOTH orthogonality of the correct formula AND cancellation of the legacy wrong formula.
2. **Exact Cubic Jury / Schur-Cohn Stability Bound (`EQ-22`):**
   - For $L_1(z) = \frac{K_{\text{tot}}}{z^2 (z - 1)}$, the closed-loop characteristic polynomial is $P(z) = z^3 - z^2 + K_{\text{tot}} = 0$.
   - The 1st-row Jury bound gives $0 < K_{\text{tot}} < 1$ (enforced as schema/startup hard bound per Spec §3.3.2).
   - The 2nd-row Jury determinant condition $|a_0^2 - a_3^2| > |a_0 a_2 - a_3 a_1| \iff 1 - K_{\text{tot}}^2 > K_{\text{tot}}$ gives the **exact cubic stability limit**:
     $$0 < K_{\text{tot}} < \frac{\sqrt{5} - 1}{2} \approx 0.618034$$
   - The spec-recommended design range $K_{\text{tot}} \in [0.15, 0.35]$ sits well inside $(0, 0.6180)$ with healthy phase margin and fast damping.
   - Loop-2 bandwidth separation MUST satisfy $K_{\text{tot},2} = 4\pi S_\alpha K_{I,2} \le 0.1\,K_{\text{tot},1}$.
3. **IEEE Std 952 Overlapping AVAR Angle Sample Indexing (`EQ-29`):**
   - Given $N_\Omega$ rate samples $\Omega[0..N_\Omega-1]$, integrated angle $\theta$ has $N_\theta = N_\Omega + 1$ points ($\theta[0] = 0$, $\theta[j] = \sum_{i<j}\Omega[i]\Delta t$).
   - The number of overlapping second-difference terms at cluster factor $m$ is $N_\theta - 2m = N_\Omega + 1 - 2m$, matching `np.mean((theta[2*m:] - 2*theta[m:-m] + theta[:-2*m])**2)`.
4. **Exact Unit Conversions (`EQ-26`, `EQ-24`):**
   - Rate: $1\text{ rad/s} = \frac{180}{\pi} \cdot 3600 = 206264.80624709636\,^\circ/\text{h}$
   - Angle Quantization $Q$: $1\text{ rad} = 206264.806247\text{ arcsec}$
   - ARW $N$: $1\text{ rad}/\sqrt{\text{s}} = \frac{180}{\pi}\cdot 60\,^\circ/\sqrt{\text{h}}$
   - RRW $K$: $1\text{ rad}/\text{s}^{3/2} = \frac{180}{\pi}\cdot 3600^{3/2}\,^\circ/\text{h}^{3/2}$
   - Rate Ramp $R$: $1\text{ rad}/\text{s}^2 = \frac{180}{\pi}\cdot 3600^2\,^\circ/\text{h}^2$

## 3. Running Per-Formula Verification Locally & in CI
```bash
python3 scripts/verify_formulas_ci.py --out-dir data/ci_formula_report
```
This script verifies that ALL 30 individual tests `test_eq01_*` .. `test_eq30_*` ran, had zero skips/failures, and generates `formula_verification_matrix.md` and `formula_verification_matrix.json`.
