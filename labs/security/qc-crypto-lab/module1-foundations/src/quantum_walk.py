"""
╔══════════════════════════════════════════════════════════════════╗
║     Discrete-Time Quantum Walk on a Line                         ║
║     QC Crypto Lab | Module 1 — Foundations                       ║
║     Portfolio: Principal Engineer / Security Architect           ║
╚══════════════════════════════════════════════════════════════════╝

Algorithm   : Discrete-Time Quantum Walk (DTQW) on a line graph
Purpose     : Demonstrate quadratic quantum spreading, graph search
              speedup, and the element distinctness collision advantage.
Complexity  : Quantum walk hits target in O(√N) steps vs classical O(N)
              Spreading: quantum σ ≈ T/√2 vs classical σ ≈ √T
Quantum     : Quadratic speedup for search; O(N^(1/3)) for collision/
Advantage     element distinctness — beats classical Grover-based bound.

This file implements:
  1. Full discrete-time quantum walk on position line -N..+N
  2. Hadamard coin operator on |L⟩/|R⟩ qubit
  3. Conditional shift operator
  4. Position probability distribution at T=50, 100, 200 steps
  5. Classical random walk comparison (standard deviation comparison)
  6. Text histogram visualisation
  7. Graph search application: O(√N) quantum vs O(N) classical
  8. Speedup table for different graph types
  9. Security application: element distinctness O(N^(1/3))

Dependencies: stdlib + numpy (no Qiskit required).
"""

import math
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
#  1.  Quantum walk state representation
# ══════════════════════════════════════════════════════════════════

# Coin states: index 0 = |L⟩ (left), index 1 = |R⟩ (right)
LEFT  = 0
RIGHT = 1

# Hadamard coin: H|L⟩ = (|L⟩+|R⟩)/√2,  H|R⟩ = (|L⟩-|R⟩)/√2
H_COIN = np.array([[1, 1], [1, -1]], dtype=complex) / math.sqrt(2)

# Y coin (alternative): gives symmetric distribution from |L⟩ start
Y_COIN = np.array([[0, -1j], [1j, 0]], dtype=complex)


def make_state(max_pos: int) -> np.ndarray:
    """
    Allocate state tensor shape (2N+1, 2).
    Axis 0: position index (0 = position -max_pos, ..., max_pos = position +max_pos)
    Axis 1: coin state (0=L, 1=R)
    Returns complex128 zeros tensor.
    """
    return np.zeros((2 * max_pos + 1, 2), dtype=complex)


def pos_to_idx(pos: int, max_pos: int) -> int:
    """Convert position integer to array index."""
    return pos + max_pos


def idx_to_pos(idx: int, max_pos: int) -> int:
    """Convert array index to position integer."""
    return idx - max_pos


# ══════════════════════════════════════════════════════════════════
#  2.  Quantum walk step: coin flip + conditional shift
# ══════════════════════════════════════════════════════════════════

def walk_step(state: np.ndarray, max_pos: int, coin: np.ndarray = H_COIN) -> np.ndarray:
    """
    Single step of the discrete-time quantum walk:
      1. Coin flip: apply coin matrix to coin register at each position.
      2. Conditional shift:
           |L⟩|x⟩ → |L⟩|x-1⟩   (left-moving component shifts left)
           |R⟩|x⟩ → |R⟩|x+1⟩   (right-moving component shifts right)
    """
    size = 2 * max_pos + 1
    new_state = np.zeros_like(state)

    # Step 1: coin flip at every position
    coined = np.einsum('ij,nj->ni', coin, state)  # apply coin to coin register

    # Step 2: conditional shift
    for idx in range(size):
        # Left-going amplitude moves to idx-1 (if in bounds)
        if idx > 0:
            new_state[idx - 1, LEFT] += coined[idx, LEFT]
        # Right-going amplitude moves to idx+1 (if in bounds)
        if idx < size - 1:
            new_state[idx + 1, RIGHT] += coined[idx, RIGHT]

    return new_state


def run_quantum_walk(T: int, max_pos: int, initial_coin: int = RIGHT,
                     coin: np.ndarray = None) -> np.ndarray:
    """
    Run quantum walk for T steps starting at position 0 with coin in
    |initial_coin⟩ state.

    Returns: position probability distribution (array of length 2*max_pos+1).
    """
    if coin is None:
        coin = H_COIN
    state = make_state(max_pos)
    state[pos_to_idx(0, max_pos), initial_coin] = 1.0 + 0j

    for _ in range(T):
        state = walk_step(state, max_pos, coin)

    # Marginalise over coin: P(x) = |ψ_L(x)|² + |ψ_R(x)|²
    probs = np.sum(np.abs(state) ** 2, axis=1)
    return probs


# ══════════════════════════════════════════════════════════════════
#  3.  Classical random walk comparison
# ══════════════════════════════════════════════════════════════════

def classical_walk_std(T: int) -> float:
    """Classical random walk standard deviation: σ = √T."""
    return math.sqrt(T)


def quantum_walk_std(T: int) -> float:
    """
    Quantum walk standard deviation on a line: σ ≈ T/√2.
    This is derived from the exact variance formula for the Hadamard walk:
      Var(X_T) = T²/2 - (1 - (-1)^T)/4 ≈ T²/2 for large T.
    Standard deviation σ ≈ T/√2.
    """
    return T / math.sqrt(2)


def compute_walk_std(probs: np.ndarray, max_pos: int) -> float:
    """Compute standard deviation of position probability distribution."""
    positions = np.array([idx_to_pos(i, max_pos) for i in range(len(probs))])
    mean = float(np.sum(positions * probs))
    var  = float(np.sum((positions - mean) ** 2 * probs))
    return math.sqrt(max(var, 0.0))


# ══════════════════════════════════════════════════════════════════
#  4.  Text histogram
# ══════════════════════════════════════════════════════════════════

def text_histogram(probs: np.ndarray, max_pos: int, bar_width: int = 40,
                   title: str = "") -> None:
    """Print a text-mode histogram of position probabilities."""
    if title:
        print(f"\n  {title}")
    max_p = float(np.max(probs))
    if max_p < 1e-15:
        print("  (all zero)")
        return

    # Only print positions with non-negligible probability
    threshold = max_p * 0.005
    shown = [(idx_to_pos(i, max_pos), float(probs[i]))
             for i in range(len(probs)) if float(probs[i]) > threshold]

    if not shown:
        print("  (no peaks above threshold)")
        return

    print(f"  {'Position':>10}  {'Prob':>8}  {'Distribution'}")
    print(f"  {'─'*10}  {'─'*8}  {'─'*bar_width}")
    for pos, p in shown:
        bar = "█" * int(p / max_p * bar_width)
        print(f"  {pos:>10}  {p:>8.4f}  {bar}")


# ══════════════════════════════════════════════════════════════════
#  5.  Main demo
# ══════════════════════════════════════════════════════════════════

GRAPH_SPEEDUP_TABLE = [
    # (Graph type, N nodes, Classical hits, Quantum hits, Speedup class, Notes)
    ("Line (path)",       "N",    "O(N)",        "O(√N)",       "Quadratic", "CTQW hitting time"),
    ("Cycle",             "N",    "O(N²)",       "O(N)",        "Quadratic", "DTQW mixing time"),
    ("Complete graph",    "N",    "O(N)",        "O(√N)",       "Quadratic", "Grover = QW"),
    ("Hypercube",         "2^n",  "O(2^n)",      "O(√(2^n)n)", "Quadratic", "Quantum walk oracle"),
    ("2D grid",           "N",    "O(N log N)",  "O(√N)",       "Quadratic", "Spatial search"),
    ("Glued trees",       "2^n",  "exp(n)",      "poly(n)",     "Exp",       "Childs et al. 2003"),
    ("Element distinct.", "N",    "O(N)",        "O(N^(2/3))", "Cubic root","Ambainis 2004"),
    ("Triangle finding",  "N",    "O(N^1.5)",    "O(N^1.3)",   "Modest",    "Quantum walk oracle"),
]


def main() -> None:
    box("Discrete-Time Quantum Walk on a Line")
    print(f"  Algorithm : Discrete-Time Quantum Walk (Hadamard coin)")
    print(f"  Purpose   : Quadratic spreading, O(√N) graph search speedup")
    print(f"  Spreading : Quantum σ ≈ T/√2  vs  Classical σ ≈ √T")
    print(f"  Qiskit    : Not required — pure numpy simulation\n")

    # ── Section 1: Walk at T=50,100,200 steps ─────────────────────
    section(1, "Quantum Walk Probability Distributions — T=50, 100, 200 steps")

    print(f"""
  Setup:
    Initial state : |0⟩|R⟩  (position 0, coin = right)
    Coin operator : Hadamard H (creates quantum interference)
    Shift operator: |L⟩|x⟩ → |L⟩|x-1⟩,  |R⟩|x⟩ → |R⟩|x+1⟩
    Position space: integers from -T to +T

  Note: Unlike classical walks, the Hadamard walk is asymmetric
  starting from |R⟩.  Starting from (|L⟩+i|R⟩)/√2 gives symmetric
  distributions — shown below for comparison.
""")

    step_configs = [(50, 55), (100, 105), (200, 205)]

    for T, max_pos in step_configs:
        probs_q = run_quantum_walk(T, max_pos, initial_coin=RIGHT)
        std_q   = compute_walk_std(probs_q, max_pos)
        std_q_theory = quantum_walk_std(T)
        std_c_theory = classical_walk_std(T)

        # Find the two dominant peaks
        peak_indices = np.argsort(probs_q)[::-1][:5]
        peak_positions = [idx_to_pos(int(i), max_pos) for i in peak_indices]
        peak_probs     = [float(probs_q[int(i)]) for i in peak_indices]

        print(f"\n  ┌─ T = {T} steps")
        print(f"  │  Quantum std dev (observed)   : σ = {std_q:.2f}")
        print(f"  │  Quantum std dev (theory T/√2): σ ≈ {std_q_theory:.2f}")
        print(f"  │  Classical std dev (theory √T): σ ≈ {std_c_theory:.2f}")
        print(f"  │  Quantum / Classical spread   : {std_q / std_c_theory:.2f}× wider")
        print(f"  │  Top 5 positions: " +
              ", ".join(f"x={p}(P={prob:.3f})" for p, prob in zip(peak_positions, peak_probs)))

        text_histogram(probs_q, max_pos, bar_width=38,
                       title=f"Position distribution at T={T}")

        print(f"  └─ (positions outside ±{T//2} suppressed)")

    # ── Section 2: Classical vs Quantum comparison ────────────────
    section(2, "Classical Random Walk vs Quantum Walk — Spreading Comparison")

    print(f"\n  Classical random walk: unbiased ±1 steps, σ = √T (diffusive)")
    print(f"  Quantum walk: σ ≈ T/√2 (ballistic — linear in T)\n")

    print(f"  {'T steps':>10} {'Classical σ≈√T':>15} {'Quantum σ≈T/√2':>16} "
          f"{'Quantum/Classical':>18} {'Speedup class'}")
    print(f"  {'─'*10} {'─'*15} {'─'*16} {'─'*18} {'─'*16}")

    for T in [10, 25, 50, 100, 200, 500, 1000, 10000]:
        s_c = classical_walk_std(T)
        s_q = quantum_walk_std(T)
        ratio = s_q / s_c
        print(f"  {T:>10} {s_c:>15.2f} {s_q:>16.2f} {ratio:>18.2f}×  Quantum = {ratio:.1f}× faster")

    print(f"""
  Interpretation:
    After T=100 steps: quantum walker has spread over ~70 positions,
    classical walker only ~10.  This 7× difference grows as √T → ∞.

    In algorithmic terms:
      Classical: O(N) steps to hit a target at distance N
      Quantum:   O(√N) steps to hit target with high probability
    This is a QUADRATIC SPEEDUP — the same class as Grover's algorithm.
""")

    # ── Section 3: Symmetric walk ─────────────────────────────────
    section(3, "Symmetric Distribution with Y-Coin Initial State")

    print(f"\n  Starting from (|L⟩ + i|R⟩)/√2 gives symmetric distribution:")

    T_sym = 50
    max_pos_sym = 55
    # Use H coin but start from symmetric state manually
    state_sym = make_state(max_pos_sym)
    idx0 = pos_to_idx(0, max_pos_sym)
    state_sym[idx0, LEFT]  = 1.0 / math.sqrt(2)
    state_sym[idx0, RIGHT] = 1j  / math.sqrt(2)

    for _ in range(T_sym):
        state_sym = walk_step(state_sym, max_pos_sym, H_COIN)

    probs_sym = np.sum(np.abs(state_sym) ** 2, axis=1)
    std_sym   = compute_walk_std(probs_sym, max_pos_sym)

    text_histogram(probs_sym, max_pos_sym, bar_width=38,
                   title=f"Symmetric walk T={T_sym}, σ = {std_sym:.2f}")

    # ── Section 4: Graph search application ───────────────────────
    section(4, "Graph Search Application — O(√N) Quantum vs O(N) Classical")

    print(f"""
  Grover-like quantum walk search on 2D grids / graphs:

  Algorithm (Ambainis-style quantum walk search):
    1. Start in equal superposition over all N vertices
    2. Apply coin that marks the target: modified coin at target vertex
    3. Repeatedly apply walk step (≈ O(1) oracle calls per step)
    4. After O(√N) steps: probability of finding target is O(1)

  Why O(√N)?  The walk spreads ballistically — covers O(T) positions
  in T steps.  To cover N positions: T = O(√N) steps.
  Classical random walk needs T = O(N) steps to cover all vertices.

  Example: Search among N = 1,000,000 vertices
    Classical: ~1,000,000 queries expected
    Quantum:   ~1,000    steps (1000× faster)
""")

    # Numerical example: simulate "hitting time" conceptually
    print(f"  Quantum walk search time estimates:")
    print(f"\n  {'N (graph size)':>18} {'Classical O(N)':>16} "
          f"{'Quantum O(√N)':>15} {'Speedup':>10}")
    print(f"  {'─'*18} {'─'*16} {'─'*15} {'─'*10}")

    for N_graph in [100, 1_000, 10_000, 100_000, 1_000_000]:
        classical = N_graph
        quantum   = int(math.ceil(math.sqrt(N_graph)))
        speedup   = classical / quantum
        print(f"  {N_graph:>18,} {classical:>16,} {quantum:>15,} {speedup:>10.1f}×")

    # ── Section 5: Speedup table for different graph types ────────
    section(5, "Quantum Walk Speedup by Graph Type")

    print(f"\n  {'Graph Type':<22} {'N':>8} {'Classical':>12} "
          f"{'Quantum':>14} {'Speedup':>10} {'Notes'}")
    print(f"  {'─'*22} {'─'*8} {'─'*12} {'─'*14} {'─'*10} {'─'*20}")

    for row in GRAPH_SPEEDUP_TABLE:
        graph, N_size, cl, qu, speedup_cls, notes = row
        print(f"  {graph:<22} {N_size:>8} {cl:>12} {qu:>14} {speedup_cls:>10} {notes}")

    # ── Section 6: Security application ──────────────────────────
    section(6, "Security Application: Element Distinctness & Collision Search")

    print("""
  Element Distinctness (Ambainis 2004):
    Problem: Given N elements, decide if any two are equal.
    Classical: O(N) queries (need to check all pairs in worst case)
    Quantum walk: O(N^(2/3)) queries -- cubic root speedup

  Collision Search (Brassard-Hoyer-Tapp 1997):
    Problem: Find x!=y such that f(x) = f(y) -- break hash collision resistance
    Classical birthday paradox: O(sqrt(N)) = O(2^(n/2)) for n-bit hash
    Quantum walk on Johnson graph: O(N^(1/3)) = O(2^(n/3))

    Impact on hash security:
      SHA-256 (n=256): Classical collision = 2^128, Quantum = 2^(256/3) ~ 2^85
      Quantum walk beats Grover (2^(256/2)=2^128) for collision finding!

  Walk on Johnson graph J(N,r):
    Vertices: r-element subsets of {1,...,N} (use plain braces, no f-string)
    Edge: two subsets differ by one element
    Walk step: remove one element, check for collision, add new element
    After O(sqrt(N)) setup + O(N^(1/3)) steps -> collision with O(1) prob

  +--------------------------------------------------------------+
  |  Algorithm      | Problem              | Complexity           |
  +-----------------+----------------------+----------------------+
  |  Classical      | Element distinctness | O(N)                 |
  |  Grover's       | Element distinctness | O(N^(3/4)) [query]  |
  |  QW on Johnson  | Element distinctness | O(N^(2/3)) optimal  |
  +-----------------+----------------------+----------------------+
  |  Classical BDay | Hash collision       | O(2^(n/2))           |
  |  QW collision   | Hash collision       | O(2^(n/3))           |
  +--------------------------------------------------------------+

  Implication for cryptography:
    SHA-256: Quantum collision strength reduced from 128-bit to ~85-bit
    NIST recommends SHA-384 or SHA-512 for post-quantum collision resistance
    SHA-256 is still acceptable for pre-image resistance (Grover: 128-bit)
""")

    # Numerical table: quantum walk collision vs hash size
    print(f"  Hash collision complexity (quantum walk O(2^(n/3))):")
    print(f"\n  {'Hash':>12} {'n bits':>8} {'Classical 2^(n/2)':>18} "
          f"{'QW 2^(n/3)':>14} {'Gap factor':>12}")
    print(f"  {'─'*12} {'─'*8} {'─'*18} {'─'*14} {'─'*12}")

    for name, n_bits in [("SHA-1", 160), ("SHA-256", 256), ("SHA-384", 384), ("SHA-512", 512)]:
        cl = n_bits // 2
        qw = n_bits // 3
        gap = cl - qw
        print(f"  {name:>12} {n_bits:>8} {'2^' + str(cl):>18} "
              f"{'2^' + str(qw):>14} {'Classical ' + str(gap) + ' bits stronger':>12}")

    sep()
    print(f"  Quantum Walk Demo complete — 3 time steps simulated, 8 graph types analysed")
    sep()


if __name__ == "__main__":
    main()
