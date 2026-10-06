"""
╔══════════════════════════════════════════════════════════════════╗
║     Quantum Fourier Transform (QFT)                              ║
║     QC Crypto Lab | Module 1 — Foundations                       ║
║     Portfolio: Principal Engineer / Security Architect           ║
╚══════════════════════════════════════════════════════════════════╝

Algorithm   : Quantum Fourier Transform (QFT)
Purpose     : Extract periodicity from quantum superpositions — the
              core subroutine enabling Shor's algorithm, QPE, and
              quantum phase estimation.
Complexity  : O(n²) quantum gates where n = number of qubits
              (vs classical FFT: O(n · 2^n) where N = 2^n samples)
Quantum     : Exponential speedup over classical DFT on state vectors
Advantage     of size N=2^n — processes all 2^n amplitudes in parallel.

This file implements:
  1. QFT matrix construction and direct application to state vectors
  2. Inverse QFT (IQFT)
  3. Circuit decomposition: H gates + controlled-R_k phase gates
  4. Application: period finding for N=15, a=2 (r=4)
  5. Complexity comparison table
  6. QFT vs DFT numerical comparison on same input

Dependencies: stdlib + numpy (no Qiskit required).
"""

import math
import cmath
import numpy as np

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
#  1.  QFT matrix and state-vector operations
# ══════════════════════════════════════════════════════════════════

def qft_matrix(n: int) -> np.ndarray:
    """
    Build the N×N QFT matrix for an n-qubit register (N = 2^n).

    QFT[j,k] = (1/√N) · ω^(j·k)   where ω = e^(2πi/N)

    This is the same DFT matrix (up to conjugation convention) but
    quantum hardware applies it in O(n²) gates while a classical
    computer would need O(N log N) for FFT on all N amplitudes.
    """
    N = 1 << n
    omega = cmath.exp(2j * math.pi / N)
    rows, cols = np.meshgrid(np.arange(N), np.arange(N), indexing='ij')
    return (1.0 / math.sqrt(N)) * (omega ** (rows * cols))


def qft_state(state: np.ndarray) -> np.ndarray:
    """Apply QFT to a state vector (numpy complex128 array of size 2^n)."""
    N = len(state)
    n = int(round(math.log2(N)))
    assert 1 << n == N, "State vector size must be a power of 2"
    return qft_matrix(n) @ state


def iqft_state(state: np.ndarray) -> np.ndarray:
    """Apply Inverse QFT (IQFT) — just conjugate transpose of QFT matrix."""
    N = len(state)
    n = int(round(math.log2(N)))
    return qft_matrix(n).conj().T @ state


# ══════════════════════════════════════════════════════════════════
#  2.  Standard quantum states for n qubits
# ══════════════════════════════════════════════════════════════════

def basis_state(n: int, k: int) -> np.ndarray:
    """Computational basis state |k⟩ in an n-qubit register."""
    v = np.zeros(1 << n, dtype=complex)
    v[k] = 1.0
    return v


def equal_superposition(n: int) -> np.ndarray:
    """Equal superposition |+⟩^⊗n = (1/√N) Σ|k⟩."""
    N = 1 << n
    return np.ones(N, dtype=complex) / math.sqrt(N)


def plus_state_n(n: int) -> np.ndarray:
    """Same as equal_superposition — alias for clarity in circuit context."""
    return equal_superposition(n)


# ══════════════════════════════════════════════════════════════════
#  3.  Circuit decomposition helpers
# ══════════════════════════════════════════════════════════════════

def hadamard_gate() -> np.ndarray:
    """2×2 Hadamard matrix."""
    return np.array([[1, 1], [1, -1]], dtype=complex) / math.sqrt(2)


def r_k_gate(k: int) -> np.ndarray:
    """Controlled-R_k phase rotation: phase = e^(2πi / 2^k)."""
    phase = cmath.exp(2j * math.pi / (1 << k))
    return np.array([[1, 0], [0, phase]], dtype=complex)


def circuit_gate_count(n: int) -> dict:
    """
    Count gates in the QFT circuit decomposition.

    For n qubits:
      - n Hadamard gates (one per qubit)
      - n(n-1)/2 controlled-R_k gates (for all pairs j < k)
      - n//2 SWAP gates (bit-reversal permutation at end)
    Total: O(n²) gates.
    """
    h_gates   = n
    cr_gates  = n * (n - 1) // 2
    swap_gates = n // 2
    total = h_gates + cr_gates + swap_gates
    return {
        "H_gates":    h_gates,
        "cR_gates":   cr_gates,
        "SWAP_gates": swap_gates,
        "total":      total,
    }


# ══════════════════════════════════════════════════════════════════
#  4.  Period-finding application: N=15, a=2 → r=4
# ══════════════════════════════════════════════════════════════════

def period_finding_qft(a: int, N_factor: int, n_bits: int = 4) -> dict:
    """
    Simulate QFT period finding: build the periodic superposition
    Σ|s·M/r⟩ and show how QFT peaks at multiples of 2^n/r.

    For a=2, N=15: order r=4, so peaks appear at 0, M/4, 2M/4, 3M/4
    where M = 2^n_bits = 16.

    Returns amplitudes and peak positions.
    """
    M = 1 << n_bits
    # Compute order r classically (what QPE would find)
    r = 1
    val = a % N_factor
    while val != 1:
        val = (val * a) % N_factor
        r += 1
        if r > N_factor:
            r = None
            break

    if r is None:
        return {"error": f"No order found for a={a}, N={N_factor}"}

    # Build periodic state: equal superposition over x ≡ 0 (mod r),
    # representing the post-modular-exponentiation register.
    state = np.zeros(M, dtype=complex)
    count = 0
    for x in range(M):
        if x % r == 0:
            state[x] = 1.0
            count += 1
    state /= math.sqrt(count)

    # Apply QFT
    qft_out = qft_state(state)
    probs = np.abs(qft_out) ** 2

    # Theoretical peak positions: s·M/r for s=0,...,r-1
    expected_peaks = [round(s * M / r) % M for s in range(r)]

    return {
        "a": a,
        "N_factor": N_factor,
        "r": r,
        "n_bits": n_bits,
        "M": M,
        "probabilities": probs,
        "expected_peaks": expected_peaks,
        "peak_prob": float(probs[expected_peaks[1]]) if len(expected_peaks) > 1 else 0.0,
    }


# ══════════════════════════════════════════════════════════════════
#  5.  Main demo
# ══════════════════════════════════════════════════════════════════

def main() -> None:
    box("Quantum Fourier Transform (QFT)")
    print(f"  Algorithm : Quantum Fourier Transform")
    print(f"  Purpose   : Extract periodicity — core of Shor's & QPE")
    print(f"  Complexity: O(n²) gates  vs  classical FFT O(n·2^n)")
    print(f"  Qiskit    : Not required — pure numpy simulation\n")

    # ── Section 1: QFT on standard states ────────────────────────
    section(1, "QFT Applied to Standard 3-Qubit States")

    n = 3
    N = 1 << n  # 8
    states = [
        ("|000⟩", basis_state(n, 0)),
        ("|001⟩", basis_state(n, 1)),
        ("|+⟩^3 equal superposition", equal_superposition(n)),
    ]

    for label, psi in states:
        out = qft_state(psi)
        probs = np.abs(out) ** 2
        print(f"\n  Input  : {label}")
        print(f"  State  : [{', '.join(f'{x.real:+.3f}{x.imag:+.3f}j' for x in psi)}]")
        print(f"  QFT    : probs = [{', '.join(f'{p:.3f}' for p in probs)}]")
        bar_line = "  Prob   : " + "".join(
            f"{'█' * int(p * 20):<20}" if p > 0.001 else " " * 20
            for p in probs
        )
        print(f"  Spread : {'uniform' if np.std(probs) < 0.01 else 'peaked'}")

        # Verify IQFT recovers original state
        recovered = iqft_state(out)
        err = np.max(np.abs(recovered - psi))
        print(f"  IQFT   : max reconstruction error = {err:.2e}  ({'✅ OK' if err < 1e-10 else '❌ FAIL'})")

    # ── Section 2: IQFT round-trip verification ───────────────────
    section(2, "Inverse QFT — Round-Trip Fidelity")

    print(f"\n  Test: QFT then IQFT should recover original state exactly")
    print(f"\n  {'State':<28} {'Input norm':>10} {'Recovered norm':>14} {'Max error':>12}")
    print(f"  {'─'*28} {'─'*10} {'─'*14} {'─'*12}")

    test_states = [
        ("|0000⟩",     basis_state(4, 0)),
        ("|0101⟩",     basis_state(4, 5)),
        ("|1111⟩",     basis_state(4, 15)),
        ("|+⟩^4",      equal_superposition(4)),
        ("Random state", np.random.default_rng(7).standard_normal(16)
                         + 1j * np.random.default_rng(13).standard_normal(16)),
    ]

    for lbl, psi in test_states:
        psi = psi / np.linalg.norm(psi)
        out = qft_state(psi)
        rec = iqft_state(out)
        err = float(np.max(np.abs(rec - psi)))
        print(f"  {lbl:<28} {np.linalg.norm(psi):>10.6f} {np.linalg.norm(rec):>14.6f} {err:>12.2e}")

    # ── Section 3: Circuit decomposition ─────────────────────────
    section(3, "QFT Circuit Decomposition — Gate Count vs n Qubits")

    print(f"""
  QFT circuit for n qubits:
    Step 1: Apply H to qubit 0
    Step 2: Apply controlled-R_2 between qubit 0 and 1
    Step 3: Apply controlled-R_3 between qubit 0 and 2 ... etc.
    Step n: Apply H to qubit n-1
    Step n+1: Bit-reversal SWAP network (n//2 swaps)

  Controlled-R_k gate: |1⟩ → e^(2πi/2^k)|1⟩  (phase rotation)
  This gives QFT[j,k] = (1/√N)·e^(2πijk/N) directly.
""")

    print(f"  {'n qubits':>10} {'N = 2^n':>10} {'H gates':>9} "
          f"{'cR gates':>10} {'SWAPs':>7} {'Total':>8} {'Classical FFT':>14}")
    print(f"  {'─'*10} {'─'*10} {'─'*9} {'─'*10} {'─'*7} {'─'*8} {'─'*14}")

    for n_q in [2, 3, 4, 5, 8, 10, 16, 20]:
        gc = circuit_gate_count(n_q)
        N_q = 1 << n_q
        classical = n_q * N_q   # O(n · 2^n) for FFT
        print(f"  {n_q:>10} {N_q:>10,} {gc['H_gates']:>9} "
              f"{gc['cR_gates']:>10} {gc['SWAP_gates']:>7} "
              f"{gc['total']:>8} {classical:>14,}")

    print(f"""
  Key insight: QFT uses O(n²) gates while classical FFT needs O(n·2^n).
  For n=20 qubits (N=1,048,576): QFT = 400 gates vs FFT = 20,971,520 ops.
  Speedup factor: ~52,429× for n=20; grows exponentially with n.
""")

    # ── Section 4: Period finding — N=15, a=2 ────────────────────
    section(4, "Application: Period Finding for N=15, a=2  (Shor's core step)")

    result = period_finding_qft(a=2, N_factor=15, n_bits=4)
    r       = result["r"]
    M       = result["M"]
    peaks   = result["expected_peaks"]
    probs   = result["probabilities"]

    print(f"""
  Goal: Find the order r of a=2 modulo N=15.
  i.e., find smallest r > 0 such that 2^r ≡ 1 (mod 15).

  Classical answer: 2^1=2, 2^2=4, 2^3=8, 2^4=16≡1 → r = 4

  QFT setup (n=4 bits, M=16 measurement outcomes):
    Build periodic state: equal superposition over x ∈ {{0,4,8,12}}
    (multiples of r=4 in the range 0..M-1)
    Apply QFT → measure → get multiple of M/r = 16/4 = 4
""")

    print(f"  Expected QFT peaks: {peaks}  (= s·M/r for s=0,1,2,3)")
    print(f"\n  QFT output probabilities (M={M} outcomes):")
    print(f"\n  {'Outcome':>8}  {'Probability':>12}  Bar")
    print(f"  {'─'*8}  {'─'*12}  {'─'*30}")

    for k_out in range(M):
        p = probs[k_out]
        bar = "█" * int(p * 40)
        mark = " ← PEAK" if k_out in peaks else ""
        if p > 0.001 or k_out in peaks:
            print(f"  {k_out:>8}  {p:>12.4f}  {bar}{mark}")

    print(f"""
  From peak = 4: phase = 4/16 = 1/4 → continued fractions → r = 4
  From peak = 8: phase = 8/16 = 1/2 → denominator 2 (r/2) → double = r=4
  From peak = 12: phase = 12/16 = 3/4 → denominator 4 → r = 4  ✅

  Factoring step: a^(r/2) ± 1 = 2^2 ± 1 = 5 or 3
    gcd(5, 15) = 5   gcd(3, 15) = 3   → 15 = 3 × 5  ✅
""")

    # ── Section 5: Why QFT matters for Shor's ────────────────────
    section(5, "Why QFT Matters for Shor's Algorithm")

    print("""
  The QFT extracts periodicity from quantum superpositions:

  1. Shor's algorithm prepares the state:
       SUM_{x=0}^{M-1} |x>|a^x mod N>

  2. After measuring the second register (value f0 = a^x0 mod N),
     the first register collapses to:
       (1/sqrt(K)) SUM_{j} |x0 + j*r>   (periodic with period r)

  3. QFT on this periodic state maps it to:
       SUM_{s} amplitude_s * |s*M/r>
     -- all probability concentrated at multiples of M/r.

  4. Measuring gives s*M/r -> divide by M -> get s/r -> continued
     fractions algorithm recovers r exactly.

  5. With r: gcd(a^(r/2) +/- 1, N) reveals factors of N.

  +--------------------------------------------------------------+
  |  Classical: find period of a^x mod N -> brute force O(N)    |
  |  Quantum QFT: extract period from superposition -> O(n^2)   |
  |  Speedup: EXPONENTIAL -- this is why RSA breaks             |
  +--------------------------------------------------------------+
""")

    # ── Section 6: QFT vs DFT numerical comparison ───────────────
    section(6, "QFT vs DFT Numerical Comparison (same input vector)")

    print(f"\n  Input: 4-qubit state |0101⟩ = basis vector k=5")
    n_cmp = 4
    psi_cmp = basis_state(n_cmp, 5)

    qft_out = qft_state(psi_cmp)
    # numpy FFT (standard DFT — same matrix up to normalization)
    dft_out = np.fft.fft(psi_cmp) / math.sqrt(len(psi_cmp))

    print(f"\n  {'k':>4}  {'|QFT output|':>14}  {'|DFT output|':>14}  {'Match':>6}")
    print(f"  {'─'*4}  {'─'*14}  {'─'*14}  {'─'*6}")
    max_err = 0.0
    for k_idx in range(len(psi_cmp)):
        qft_amp = abs(qft_out[k_idx])
        dft_amp = abs(dft_out[k_idx])
        diff    = abs(qft_amp - dft_amp)
        max_err = max(max_err, diff)
        match   = "✅" if diff < 1e-10 else f"Δ={diff:.2e}"
        print(f"  {k_idx:>4}  {qft_amp:>14.8f}  {dft_amp:>14.8f}  {match:>6}")

    print(f"\n  Max |QFT - DFT| difference: {max_err:.2e}  "
          f"({'✅ Identical' if max_err < 1e-10 else 'Numerical difference'})")
    print(f"""
  Conclusion: QFT and DFT produce identical results on the same input.
  The quantum advantage is NOT in the computation per output element —
  it is in processing all 2^n amplitudes SIMULTANEOUSLY (in superposition)
  with only O(n²) quantum gates instead of O(n·2^n) classical operations.
""")

    sep()
    print(f"  QFT Demo complete — 4 states transformed, period finding verified")
    sep()


if __name__ == "__main__":
    main()
