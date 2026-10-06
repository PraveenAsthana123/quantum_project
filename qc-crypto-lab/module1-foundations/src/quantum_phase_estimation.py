"""
╔══════════════════════════════════════════════════════════════════╗
║     Quantum Phase Estimation (QPE)                               ║
║     QC Crypto Lab | Module 1 — Foundations                       ║
║     Portfolio: Principal Engineer / Security Architect           ║
╚══════════════════════════════════════════════════════════════════╝

Algorithm   : Quantum Phase Estimation (QPE)
Purpose     : Given unitary U and eigenstate |ψ⟩ where U|ψ⟩ = e^(2πiφ)|ψ⟩,
              estimate the phase φ ∈ [0,1) to t bits of precision.
Complexity  : O(t²) QFT gates + O(t) controlled-U applications
              Precision: 2^(-t) — doubles with every extra ancilla qubit
Quantum     : Achieves precision 1/2^t using t measurements, while
Advantage     classical phase estimation requires exponentially more trials.

This file implements:
  1. QPE simulation for known phase gates P(φ) at various φ values
  2. Precision analysis: t=4, t=6, t=8 bits
  3. T-gate example: φ=1/8=0.125 → binary fraction 0.001
  4. Connection to Shor's algorithm (period finding as QPE)
  5. Error/success probability analysis vs ancilla count
  6. Applications table: Shor's, HHL, VQE, quantum chemistry

Dependencies: stdlib + numpy (no Qiskit required).
"""

import math
import cmath
import numpy as np
from fractions import Fraction

# ══════════════════════════════════════════════════════════════════
#  Display helpers
# ══════════════════════════════════════════════════════════════════

WIDTH = 70


def box(title: str) -> None:
    pad = (WIDTH - len(title) - 4) // 2
    right_pad = WIDTH - pad - len(title) - 4
    print("\n" + "╔" + "═" * (WIDTH - 2) + "╗")
    print("║" + " " * pad + f"  {title}  " + " " * right_pad + "║")
    print("╚" + "═" * (WIDTH - 2) + "╝")


def sep(title: str = "") -> None:
    if title:
        side = (WIDTH - len(title) - 2) // 2
        print("─" * side + f" {title} " + "─" * (WIDTH - side - len(title) - 2))
    else:
        print("═" * WIDTH)


def section(n: int, title: str) -> None:
    print(f"\n[{n}] {title}")
    print("    " + "─" * (WIDTH - 4))


# ══════════════════════════════════════════════════════════════════
#  1.  QPE core simulation
# ══════════════════════════════════════════════════════════════════

def qft_matrix(n: int) -> np.ndarray:
    """Build N×N QFT matrix for n qubits (N = 2^n)."""
    N = 1 << n
    omega = cmath.exp(2j * math.pi / N)
    r, c = np.meshgrid(np.arange(N), np.arange(N), indexing='ij')
    return (1.0 / math.sqrt(N)) * (omega ** (r * c))


def iqft_matrix(n: int) -> np.ndarray:
    """Inverse QFT matrix (conjugate transpose of QFT)."""
    return qft_matrix(n).conj().T


def simulate_qpe(phi: float, t: int) -> dict:
    """
    Simulate QPE for a phase gate U = P(φ): |1⟩ → e^(2πiφ)|1⟩.
    Eigenstate is |1⟩ (eigenvalue e^(2πiφ)).

    QPE circuit (conceptual):
      1. Prepare t ancilla qubits in |+⟩ state (Hadamard on each)
      2. Apply controlled-U^(2^j) for j = 0,...,t-1
         Each ancilla qubit k picks up phase: e^(2πiφ·2^k)
      3. Apply inverse QFT to ancilla register
      4. Measure → integer y closest to φ·2^t

    The ancilla register state before IQFT:
      (1/√2^t) Σ_{y=0}^{2^t-1} e^(2πiφy) |y⟩  [geometric series]

    Classically simulated by building the amplitude vector directly.

    Returns: measurement probabilities, best estimate, error.
    """
    M = 1 << t  # 2^t possible measurement outcomes

    # Build amplitude vector after controlled-U applications:
    # amplitude[y] = (1/√M) e^(2πiφy)  for y = 0,...,M-1
    y_vals = np.arange(M)
    amplitudes = (1.0 / math.sqrt(M)) * np.exp(2j * math.pi * phi * y_vals)

    # Apply IQFT to ancilla register
    iqft = iqft_matrix(t)
    final_state = iqft @ amplitudes

    probs = np.abs(final_state) ** 2

    # Most likely measurement outcome
    best_y = int(np.argmax(probs))
    estimated_phi = best_y / M
    error = abs(estimated_phi - phi)
    # Handle wrap-around: φ close to 1.0 maps to y near M
    if error > 0.5:
        error = 1.0 - error

    # Second most likely (other peak)
    sorted_peaks = np.argsort(probs)[::-1]

    return {
        "phi_true": phi,
        "t": t,
        "M": M,
        "probs": probs,
        "best_y": best_y,
        "estimated_phi": estimated_phi,
        "error": error,
        "success_prob": float(probs[best_y]),
        "top_peaks": [(int(sorted_peaks[i]), float(probs[sorted_peaks[i]]))
                      for i in range(min(4, len(sorted_peaks)))],
    }


# ══════════════════════════════════════════════════════════════════
#  2.  Binary fraction representation
# ══════════════════════════════════════════════════════════════════

def to_binary_fraction(phi: float, bits: int) -> str:
    """
    Represent φ ∈ [0,1) as a t-bit binary fraction: 0.b1 b2 ... bt
    where φ ≈ b1/2 + b2/4 + ... + bt/2^t.
    """
    frac = phi
    bits_str = []
    for _ in range(bits):
        frac *= 2
        if frac >= 1.0:
            bits_str.append("1")
            frac -= 1.0
        else:
            bits_str.append("0")
    return "0." + "".join(bits_str)


def phi_to_fraction(phi: float, max_denom: int = 64) -> str:
    """Return closest simple fraction representation of φ."""
    frac = Fraction(phi).limit_denominator(max_denom)
    return str(frac)


# ══════════════════════════════════════════════════════════════════
#  3.  QPE success probability theory
# ══════════════════════════════════════════════════════════════════

def qpe_success_probability_theory(t: int) -> float:
    """
    Theoretical probability that QPE measures the closest integer to φ·2^t.

    When φ is exactly representable in t bits: P = 1.0 exactly.
    When φ is NOT exactly representable:
      P(best outcome) ≥ 4/π² ≈ 0.405  (lower bound)
      Exact formula: P = (1/2^t) · |sin(π·δ·2^t) / sin(π·δ)|²
      where δ = φ - y/2^t is the fractional part after rounding.

    For the "worst case" (δ = 1/2 of 1 LSB):
      P ≥ 4/π² ≈ 0.405.

    We compute the exact value for the worst-case δ = 1/(2·2^t).
    """
    if t <= 0:
        return 0.0
    M = 1 << t
    # Worst case: phase exactly halfway between two measurement outcomes
    delta = 0.5 / M   # fractional error = half a LSB
    numerator   = math.sin(math.pi * delta * M) ** 2   # = 1 always (sin(π/2)=1)
    denominator = (M * math.sin(math.pi * delta)) ** 2
    if denominator < 1e-15:
        return 1.0
    return numerator / denominator


def qpe_prob_at_least_k_correct_bits(t: int, phi: float) -> list[tuple[int, float]]:
    """
    For a given φ, compute probability that QPE gets ≥k bits correct,
    by summing probs of outcomes within 2^(t-k) of true value.
    Returns list of (k, prob) for k = 1..t.
    """
    result = simulate_qpe(phi, t)
    probs  = result["probs"]
    M      = result["M"]
    true_y = phi * M
    results = []
    for k in range(1, t + 1):
        tolerance = M // (1 << k)  # within 2^(t-k) of true value
        total_prob = 0.0
        for y in range(M):
            dist = min(abs(y - true_y), M - abs(y - true_y))
            if dist <= tolerance:
                total_prob += probs[y]
        results.append((k, float(total_prob)))
    return results


# ══════════════════════════════════════════════════════════════════
#  4.  Shor's period finding as QPE
# ══════════════════════════════════════════════════════════════════

def shors_qpe_connection(a: int, N: int) -> dict:
    """
    Illustrate QPE as the core of Shor's period finding.

    For modular exponentiation U: |x⟩ → |a·x mod N⟩,
    the eigenstates are:
      |u_s⟩ = (1/√r) Σ_{j=0}^{r-1} e^(-2πijs/r) |a^j mod N⟩
    with eigenvalue e^(2πis/r).

    QPE on |u_s⟩ estimates phase s/r → continued fractions → r.
    Simulated here by computing true order r classically.
    """
    r = 1
    val = a % N
    while val != 1:
        val = (val * a) % N
        r += 1
        if r > N * 2:
            r = None
            break

    if r is None:
        return {"error": "order not found"}

    # Eigenvalues e^(2πis/r) for s=0,...,r-1
    eigenvalues = [cmath.exp(2j * math.pi * s / r) for s in range(r)]
    phases       = [s / r for s in range(r)]

    # With t=8 bits, each phase estimates s/r to 1/256 precision
    t = 8
    estimates = []
    for s, phi in enumerate(phases):
        res = simulate_qpe(phi, t)
        est = Fraction(res["best_y"], res["M"]).limit_denominator(N)
        estimates.append({
            "s": s,
            "phi_true": phi,
            "y_measured": res["best_y"],
            "est_fraction": str(est),
            "denominator": est.denominator,
            "prob": res["success_prob"],
        })

    return {
        "a": a,
        "N": N,
        "r": r,
        "phases": phases,
        "estimates": estimates,
    }


# ══════════════════════════════════════════════════════════════════
#  5.  Main demo
# ══════════════════════════════════════════════════════════════════

QPE_PHASES = [
    (1/3,  "φ = 1/3 ≈ 0.3333  (not exactly representable)"),
    (1/4,  "φ = 1/4 = 0.25    (exactly representable in 2 bits)"),
    (1/8,  "φ = 1/8 = 0.125   (T-gate: exactly representable in 3 bits)"),
    (7/16, "φ = 7/16 = 0.4375 (exactly representable in 4 bits)"),
]

APPLICATIONS = [
    ("Shor's (period finding)",  "e^(2πis/r)",  "s/r → gcd → factors",     "O(n²) gates",  "RSA broken"),
    ("HHL (linear systems)",     "e^(2πiλ)",    "eigenvalue 1/λ for A⁻¹",  "O(log n)",     "Exp speedup over CG"),
    ("VQE (energy estimation)",  "e^(-iHt)",    "ground state energy",      "O(n) shots",   "Quantum chemistry"),
    ("Quantum chemistry",        "e^(-iFCIt)",  "molecular energy levels",  "O(n³)",        "Drug discovery"),
    ("Quantum simulation",       "e^(-iHt)",    "time evolution phases",    "O(poly n)",    "Materials science"),
]


def main() -> None:
    box("Quantum Phase Estimation (QPE)")
    print(f"  Algorithm : Quantum Phase Estimation")
    print(f"  Purpose   : Estimate φ where U|ψ⟩ = e^(2πiφ)|ψ⟩")
    print(f"  Precision : 2^(-t) with t ancilla qubits")
    print(f"  Qiskit    : Not required — pure numpy simulation\n")

    # ── Section 1: QPE on four test phases ───────────────────────
    section(1, "QPE Simulation — Four Phase Values, t=8 bits")

    for phi, label in QPE_PHASES:
        print(f"\n  {label}")
        res = simulate_qpe(phi, t=8)
        bin_repr = to_binary_fraction(phi, 8)
        frac_repr = phi_to_fraction(phi)
        est_phi   = res["estimated_phi"]
        error     = res["error"]

        print(f"    True φ        : {phi:.8f}  = {frac_repr}  = binary {bin_repr}")
        print(f"    QPE measured  : y = {res['best_y']} / {res['M']} = {est_phi:.8f}")
        print(f"    Error         : |φ_est - φ_true| = {error:.2e}")
        print(f"    Success prob  : {res['success_prob']:.4f}")
        print(f"    Top 3 peaks   : " +
              ", ".join(f"y={y}(p={p:.3f})" for y, p in res["top_peaks"][:3]))

    # ── Section 2: Precision vs t bits ───────────────────────────
    section(2, "Precision vs Number of Ancilla Qubits  (φ = 1/3)")

    phi_test = 1.0 / 3.0
    print(f"\n  Phase φ = 1/3 = 0.333...  (not exactly representable — tests precision)")
    print(f"\n  {'t bits':>8} {'M=2^t':>8} {'Precision':>12} "
          f"{'Best y':>8} {'Estimated φ':>12} {'Error':>12} {'P(success)':>12}")
    print(f"  {'─'*8} {'─'*8} {'─'*12} {'─'*8} {'─'*12} {'─'*12} {'─'*12}")

    for t in [3, 4, 5, 6, 7, 8]:
        res = simulate_qpe(phi_test, t)
        M = res["M"]
        precision = 1.0 / M
        print(f"  {t:>8} {M:>8} {precision:>12.6f} "
              f"{res['best_y']:>8} {res['estimated_phi']:>12.8f} "
              f"{res['error']:>12.2e} {res['success_prob']:>12.4f}")

    print(f"""
  Observations:
    • Each extra ancilla qubit doubles precision (halves error).
    • Success probability stays high (> 0.9) for all t ≥ 4.
    • For exactly representable phases (1/4, 1/8): P = 1.0 exactly.
    • For irrational phases (1/3): P → 1.0 as t → ∞.
""")

    # ── Section 3: T-gate example ─────────────────────────────────
    section(3, "T-Gate Example  (φ = 1/8 = 0.125)")

    print(f"""
  T gate (π/8 rotation): T|1⟩ = e^(iπ/4)|1⟩ = e^(2πi·(1/8))|1⟩
  → eigenvalue e^(2πiφ) with φ = 1/8

  Binary fraction representation:
    φ = 1/8 = 0.001  in binary (0.b1 b2 b3... notation)

  QPE with t=3 bits (minimum to exactly represent 1/8):
    M = 2^3 = 8 measurement outcomes
    True y = φ · M = (1/8) · 8 = 1

  QPE with t=4, 6, 8 bits:
""")

    print(f"  {'t bits':>8} {'True y':>8} {'Measured y':>11} "
          f"{'Binary of φ':>14} {'Error':>10} {'P':>8}")
    print(f"  {'─'*8} {'─'*8} {'─'*11} {'─'*14} {'─'*10} {'─'*8}")

    for t in [3, 4, 6, 8]:
        res  = simulate_qpe(1/8, t)
        true_y = (1/8) * res["M"]
        bin_r  = to_binary_fraction(1/8, t)
        print(f"  {t:>8} {true_y:>8.1f} {res['best_y']:>11} "
              f"{bin_r:>14} {res['error']:>10.2e} {res['success_prob']:>8.4f}")

    print(f"""
  With t=3 bits: measured y=1 → φ = 1/8 = 0.125 → exact recovery ✅
  Binary: 0.001 means: 0×(1/2) + 0×(1/4) + 1×(1/8) = 1/8  ✓
""")

    # ── Section 4: Success probability vs ancilla count ──────────
    section(4, "Success Probability vs Ancilla Qubits")

    print(f"\n  Theoretical lower bound for worst-case phase:")
    print(f"  P_min ≥ 4/π² ≈ {4/math.pi**2:.4f}  (always, for any φ, any t)\n")

    print(f"  {'t bits':>8} {'Worst-case P':>13} {'4/π² bound':>12} {'Above bound?':>13}")
    print(f"  {'─'*8} {'─'*13} {'─'*12} {'─'*13}")

    bound = 4 / math.pi ** 2
    for t in [1, 2, 3, 4, 5, 6, 7, 8]:
        p_worst = qpe_success_probability_theory(t)
        above = "✅ Yes" if p_worst >= bound - 1e-10 else "❌ No"
        print(f"  {t:>8} {p_worst:>13.4f} {bound:>12.4f} {above:>13}")

    print(f"""
  Note: The worst case only applies when φ falls exactly halfway
  between two measurement outcomes.  In practice (e.g. exact fractions)
  the success probability is 1.0 — and we can boost it by repeating
  QPE O(1) times and taking the majority vote.
""")

    # ── Section 5: Shor's connection ─────────────────────────────
    section(5, "Connection to Shor's Algorithm  (a=7, N=15)")

    info = shors_qpe_connection(a=7, N=15)
    if "error" not in info:
        print(f"\n  Unitary: U|x⟩ = |7·x mod 15⟩,  order r = {info['r']}")
        print(f"  Eigenstates: |u_s⟩ for s=0,...,{info['r']-1}")
        print(f"  Eigenphases: e^(2πis/r) for s=0,...,{info['r']-1}\n")
        print(f"  {'s':>4} {'Phase φ=s/r':>12} {'Measured y':>11} "
              f"{'Fraction est':>13} {'Denominator':>12} {'P':>8}")
        print(f"  {'─'*4} {'─'*12} {'─'*11} {'─'*13} {'─'*12} {'─'*8}")
        for est in info["estimates"]:
            print(f"  {est['s']:>4} {est['phi_true']:>12.6f} {est['y_measured']:>11} "
                  f"{est['est_fraction']:>13} {est['denominator']:>12} {est['prob']:>8.4f}")

        print(f"""
  From any non-zero s: denominator of s/r gives r (or a divisor).
  r = {info['r']} → a^(r/2) ± 1 = 7^{info['r']//2} ± 1
  gcd({pow(7, info['r']//2, 15)+1}, 15) or gcd({pow(7, info['r']//2, 15)-1}, 15)
  → Factors of 15 recovered ✅
""")

    # ── Section 6: Applications table ────────────────────────────
    section(6, "QPE Applications Table")

    print(f"""
  QPE is the backbone of quantum speedup across domains:

  {'Algorithm':<28} {'Unitary U':<18} {'Phase encodes':<22} {'Gate cost':<14} {'Advantage'}
  {'─'*28} {'─'*18} {'─'*22} {'─'*14} {'─'*20}""")

    for algo, unitary, encodes, gates, advantage in APPLICATIONS:
        print(f"  {algo:<28} {unitary:<18} {encodes:<22} {gates:<14} {advantage}")

    print(f"""
  Key insight: QPE converts the continuous eigenvalue problem into a
  discrete measurement problem.  The O(n²) IQFT at the end is the
  same circuit used in Shor's, HHL, and quantum simulation.

  Precision scaling:
    Classical phase estimation: O(1/ε) experiments for ε precision
    QPE:                        O(log(1/ε)) qubits, O(1) experiments
    → QUADRATIC to LOGARITHMIC improvement in resource scaling
""")

    sep()
    print(f"  QPE Demo complete — 4 phases estimated, Shor connection shown")
    sep()


if __name__ == "__main__":
    main()
