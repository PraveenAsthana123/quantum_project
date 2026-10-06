"""
Quantum-Era Cryptographic Attack Simulations
=============================================
Educational lab: simulates quantum attacks on classical cryptography so
defenders understand migration urgency. All results are theoretical/simulated.

Defensive Security Educational Lab — /mnt/deepa/quantum/qc-attack-lab/
"""

import math
import time
import random
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Shared data types
# ---------------------------------------------------------------------------

@dataclass
class QuantumThreat:
    name: str
    algorithm: str               # Shor / Grover / BHT / AI
    target: str
    classical_security: str
    quantum_security: str
    qubits_logical: Optional[int]
    qubits_physical_est: Optional[int]
    crqc_year_est: str
    urgency: str                 # CRITICAL / HIGH / MEDIUM / LOW
    defense: str
    simulation_result: dict = field(default_factory=dict)

    def display(self):
        bar = "=" * 76
        print(f"\n{bar}")
        print(f"  THREAT: {self.name}")
        print(f"  Algorithm: {self.algorithm}  |  Target: {self.target}")
        print(bar)
        print(f"  Classical security : {self.classical_security}")
        print(f"  Quantum security   : {self.quantum_security}")
        if self.qubits_logical:
            print(f"  Logical qubits     : {self.qubits_logical:,}")
        if self.qubits_physical_est:
            print(f"  Physical qubits    : ~{self.qubits_physical_est:,} (at 0.1% error rate)")
        print(f"  CRQC estimate      : {self.crqc_year_est}")
        print(f"  Urgency            : {self.urgency}")
        print(f"  Defense            : {self.defense}")
        for k, v in self.simulation_result.items():
            print(f"  {k:<22}: {v}")


# ---------------------------------------------------------------------------
# 1. Shor's Algorithm — RSA
# ---------------------------------------------------------------------------

class ShorsRSAAttack:
    """
    Simulate Shor's algorithm factoring RSA.
    Small N: actually factor via classical period-finding simulation.
    Large N: compute quantum resource estimates.
    """

    @staticmethod
    def _gcd(a: int, b: int) -> int:
        while b:
            a, b = b, a % b
        return a

    @staticmethod
    def _order_classical(a: int, n: int) -> Optional[int]:
        """Find smallest r such that a^r ≡ 1 (mod n) — classical simulation of quantum step."""
        r = 1
        x = a % n
        while x != 1:
            x = (x * a) % n
            r += 1
            if r > 10_000:
                return None   # give up for large N
        return r

    def _shors_simulate(self, n: int) -> dict:
        """Run Shor's period-finding for small N (classical simulation of quantum step)."""
        for attempt in range(20):
            a = random.randint(2, n - 1)
            g = self._gcd(a, n)
            if g > 1:
                return {"p": g, "q": n // g, "attempts": attempt + 1, "method": "gcd shortcut"}
            r = self._order_classical(a, n)
            if r is None or r % 2 != 0:
                continue
            x = pow(a, r // 2, n)
            f1 = self._gcd(x - 1, n)
            f2 = self._gcd(x + 1, n)
            if 1 < f1 < n:
                return {"p": f1, "q": n // f1, "attempts": attempt + 1, "method": "period-finding"}
            if 1 < f2 < n:
                return {"p": f2, "q": n // f2, "attempts": attempt + 1, "method": "period-finding"}
        return {"p": None, "q": None, "attempts": 20, "method": "failed"}

    @staticmethod
    def _quantum_resources(key_bits: int) -> dict:
        """
        Quantum resource estimates for RSA factoring via Shor's algorithm.
        References: Gidney & Ekerå (2021) 'How to factor 2048-bit RSA integers
        in 8 hours using 20 million noisy qubits'.
        """
        logical_qubits = {
            512:  1152,
            1024: 2050,
            2048: 4098,
            4096: 8194,
        }
        # Physical qubits: ~1000× logical at current 0.1% physical error rates
        # (surface code with ~1000 physical qubits per logical qubit for most algorithms)
        physical_factor = 1000
        gate_ops = {
            512:  int(1e9),
            1024: int(1e10),
            2048: int(1e12),
            4096: int(1e13),
        }
        time_hours = {
            512: 0.5,
            1024: 2,
            2048: 8,
            4096: 32,
        }
        lq = logical_qubits.get(key_bits, key_bits * 2 + 2)
        pq = lq * physical_factor
        ops = gate_ops.get(key_bits, int(key_bits ** 3))
        hrs = time_hours.get(key_bits, key_bits / 256)
        return {
            "logical_qubits": lq,
            "physical_qubits_est": pq,
            "gate_operations": ops,
            "estimated_hours_ftqc": hrs,
        }

    def run(self) -> list[QuantumThreat]:
        threats = []

        # Small N — actually simulate
        demo_keys = [
            (15,   "N=pq, p=3, q=5"),
            (21,   "N=pq, p=3, q=7"),
            (35,   "N=pq, p=5, q=7"),
            (143,  "N=pq, p=11, q=13"),
        ]
        sim_results = {}
        for n, desc in demo_keys:
            res = self._shors_simulate(n)
            sim_results[f"N={n}"] = (
                f"p={res['p']}, q={res['q']} ({res['method']}, {res['attempts']} attempts)"
                if res["p"] else "factoring failed in simulation"
            )

        # Small key threat
        threats.append(QuantumThreat(
            name="Shor's RSA Attack — Small Demo Keys",
            algorithm="Shor's Algorithm (period-finding)",
            target="RSA public key moduli N=15,21,35,143",
            classical_security="trivially broken (trial division)",
            quantum_security="BROKEN (Shor's period-finding, O((log N)^3) quantum gates)",
            qubits_logical=8,
            qubits_physical_est=8000,
            crqc_year_est="Demonstrated on IBM quantum hardware (2001, N=15)",
            urgency="CRITICAL",
            defense="Replace RSA with ML-KEM (NIST FIPS 203) for key encapsulation.",
            simulation_result=sim_results,
        ))

        # Production key size estimates
        for key_bits in [1024, 2048, 4096]:
            res = self._quantum_resources(key_bits)
            threats.append(QuantumThreat(
                name=f"Shor's RSA Attack — RSA-{key_bits}",
                algorithm="Shor's Algorithm",
                target=f"RSA-{key_bits} key pair",
                classical_security=(
                    f"{'80-bit (broken)' if key_bits == 1024 else '112-bit' if key_bits == 2048 else '140-bit'}"
                ),
                quantum_security="0-bit (BROKEN by any CRQC via Shor's)",
                qubits_logical=res["logical_qubits"],
                qubits_physical_est=res["physical_qubits_est"],
                crqc_year_est="Estimated 2030–2035 for RSA-2048 (Gidney & Ekerå 2021)",
                urgency="CRITICAL",
                defense=(
                    "Immediate: hybrid ML-KEM + RSA for in-transit data. "
                    "Long-term: full PQC migration (ML-KEM-768/1024). "
                    f"RSA-{key_bits} broken on FTQC in ~{res['estimated_hours_ftqc']} hours."
                ),
                simulation_result={
                    "Gate ops": f"~{res['gate_operations']:.2e}",
                    "FTQC time": f"~{res['estimated_hours_ftqc']} hours",
                    "Reference": "Gidney & Ekerå (2021), Phys. Rev. Lett.",
                },
            ))
        return threats


# ---------------------------------------------------------------------------
# 2. Shor's Algorithm — Elliptic Curve Discrete Log
# ---------------------------------------------------------------------------

class ShorsECCAttack:
    """
    Shor's algorithm applied to ECDLP (elliptic curve discrete logarithm).
    Recovers ECDSA private key from public key.
    """

    # Quantum resource estimates from Roetteler et al. (2017)
    # "Quantum Resource Estimates for Computing Elliptic Curve Discrete Logarithms"
    ECC_RESOURCES = {
        "P-192":  {"logical_qubits": 1458,  "toffoli_gates": int(3.2e11), "bits": 192},
        "P-256":  {"logical_qubits": 2330,  "toffoli_gates": int(8.1e11), "bits": 256},
        "P-384":  {"logical_qubits": 3484,  "toffoli_gates": int(2.7e12), "bits": 384},
        "P-521":  {"logical_qubits": 4719,  "toffoli_gates": int(7.3e12), "bits": 521},
        "secp256k1": {"logical_qubits": 2330, "toffoli_gates": int(8.1e11), "bits": 256},
    }

    def run(self) -> list[QuantumThreat]:
        threats = []
        for curve, res in self.ECC_RESOURCES.items():
            bits = res["bits"]
            # Classical security: n/2 bits (ECDLP hardness)
            classical_bits = bits // 2
            phys = res["logical_qubits"] * 1000
            threats.append(QuantumThreat(
                name=f"Shor's ECC Attack — {curve}",
                algorithm="Shor's Algorithm (ECDLP variant)",
                target=f"ECDSA/ECDH with {curve} ({bits}-bit)",
                classical_security=f"{classical_bits}-bit (ECDLP hardness)",
                quantum_security="0-bit (BROKEN: private key recoverable from public key)",
                qubits_logical=res["logical_qubits"],
                qubits_physical_est=phys,
                crqc_year_est="2030–2035 (same CRQC as RSA)",
                urgency="CRITICAL",
                defense=(
                    f"Replace {curve} ECDSA with ML-DSA (NIST FIPS 204) for signatures. "
                    "Replace ECDH key exchange with ML-KEM (NIST FIPS 203). "
                    "Bitcoin/Ethereum use secp256k1 — CRITICAL risk for long-term key reuse."
                ),
                simulation_result={
                    "Toffoli gates": f"~{res['toffoli_gates']:.2e}",
                    "Reference": "Roetteler et al. (2017), arXiv:1706.06752",
                    "Bitcoin risk": "All BTC public keys exposed once CRQC exists",
                },
            ))
        return threats


# ---------------------------------------------------------------------------
# 3. Grover's Algorithm — AES Key Search
# ---------------------------------------------------------------------------

class GroversAESAttack:
    """
    Grover's algorithm reduces AES brute-force from O(2^n) to O(2^(n/2)).
    """

    @staticmethod
    def grover_speedup(key_bits: int) -> dict:
        classical_ops = 2 ** key_bits
        quantum_ops = 2 ** (key_bits // 2)
        effective_bits = key_bits // 2
        # Grover oracle calls: sqrt(2^n) but each oracle is expensive (AES circuit)
        # AES-128 Grover: ~2^70 quantum ops needed accounting for oracle depth
        # Reference: Grassl et al. (2016), Jaques et al. (2020)
        aes_oracle_overhead = {128: 6, 192: 6, 256: 6}  # depth multiplier
        adjusted_ops = quantum_ops * (10 ** aes_oracle_overhead.get(key_bits, 6))
        return {
            "key_bits": key_bits,
            "classical_ops": classical_ops,
            "quantum_ops": quantum_ops,
            "effective_bits": effective_bits,
            "adjusted_quantum_ops": adjusted_ops,
        }

    @staticmethod
    def _security_status(effective_bits: int) -> str:
        if effective_bits < 80:
            return "BROKEN"
        elif effective_bits < 100:
            return "CRITICAL"
        elif effective_bits < 120:
            return "HIGH CONCERN"
        elif effective_bits < 128:
            return "MARGINAL"
        else:
            return "ACCEPTABLE"

    def run(self) -> list[QuantumThreat]:
        threats = []
        configs = [
            (128, "AES-128 (most common)"),
            (192, "AES-192"),
            (256, "AES-256 (recommended)"),
        ]
        for key_bits, label in configs:
            res = self.grover_speedup(key_bits)
            eff = res["effective_bits"]
            status = self._security_status(eff)
            urgency_map = {"BROKEN": "CRITICAL", "CRITICAL": "CRITICAL",
                           "HIGH CONCERN": "HIGH", "MARGINAL": "HIGH", "ACCEPTABLE": "LOW"}
            threats.append(QuantumThreat(
                name=f"Grover's AES Attack — {label}",
                algorithm="Grover's Search Algorithm",
                target=f"{label} symmetric encryption key",
                classical_security=f"2^{key_bits} operations ({key_bits}-bit)",
                quantum_security=f"2^{eff} effective security → {status}",
                qubits_logical=2953 if key_bits == 128 else 3000,   # Grassl et al. 2016
                qubits_physical_est=3_000_000,
                crqc_year_est="2035–2040 (more qubits needed than RSA attack)",
                urgency=urgency_map[status],
                defense=(
                    "AES-128: UPGRADE to AES-256 immediately. "
                    "AES-256: ACCEPTABLE for quantum era (128-bit effective security). "
                    "Key wrap: use 256-bit keys. NIST recommends AES-256 for long-term data."
                ),
                simulation_result={
                    "Classical ops": f"2^{key_bits}",
                    "Quantum ops": f"2^{eff} (Grover speedup √(2^{key_bits}))",
                    "Effective security": f"{eff} bits",
                    "Status": status,
                    "Speedup formula": f"O(√(2^{key_bits})) = O(2^{eff})",
                },
            ))
        return threats


# ---------------------------------------------------------------------------
# 4. Grover's + BHT — SHA-256 Attack
# ---------------------------------------------------------------------------

class GroversSHA256Attack:
    """
    Grover's search on SHA-256 preimage and BHT algorithm for collisions.
    """

    def run(self) -> list[QuantumThreat]:
        threats = []
        # SHA-256 preimage: 256-bit, Grover gives 2^128 — still safe
        threats.append(QuantumThreat(
            name="Grover's SHA-256 Preimage Attack",
            algorithm="Grover's Search",
            target="SHA-256 preimage resistance",
            classical_security="2^256 operations",
            quantum_security="2^128 operations (SAFE — doubled key rule applies)",
            qubits_logical=2403,   # Banegas et al. (2021)
            qubits_physical_est=2_500_000,
            crqc_year_est="N/A — 2^128 operations still infeasible on any CRQC",
            urgency="LOW",
            defense=(
                "SHA-256 preimage resistance is ACCEPTABLE for the quantum era. "
                "Use SHA-384 or SHA-512 for maximum margin. "
                "Do NOT use SHA-1 or MD5."
            ),
            simulation_result={
                "Classical": "2^256",
                "Quantum (Grover)": "2^128",
                "Status": "SAFE",
                "Note": "NIST retains SHA-256 as quantum-safe for preimage",
            },
        ))

        # SHA-256 collision: BHT quantum walk gives 2^85.3
        # Reference: Brassard, Høyer, Tapp (1998) BHT collision algorithm
        # 256-bit hash → collision classical: 2^128 → quantum (BHT): 2^(256/3) ≈ 2^85.3
        collision_quantum = 256 / 3
        threats.append(QuantumThreat(
            name="BHT Quantum Walk SHA-256 Collision",
            algorithm="Brassard-Høyer-Tapp (BHT) Quantum Walk",
            target="SHA-256 collision resistance",
            classical_security="2^128 (birthday bound)",
            quantum_security=f"2^{collision_quantum:.1f} (BHT algorithm) — MARGINAL",
            qubits_logical=None,
            qubits_physical_est=None,
            crqc_year_est="Theoretical — large memory requirements reduce practical risk",
            urgency="MEDIUM",
            defense=(
                "Migrate to SHA-384 (collision: 2^128 quantum-safe) or SHA-3-256. "
                "Certificate authorities should use SHA-384 for long-lived certs. "
                "BHT requires large quantum RAM (QRAM) — not yet practical."
            ),
            simulation_result={
                "Classical collision": "2^128",
                "Quantum collision (BHT)": f"2^{collision_quantum:.1f}",
                "SHA-384 quantum collision": "2^128 (safe)",
                "Practical risk": "LOW — QRAM requirements are prohibitive today",
                "Reference": "BHT (1998), J. Cryptol.; Bernstein (2009) quantum security",
            },
        ))
        return threats


# ---------------------------------------------------------------------------
# 5. Harvest Now Decrypt Later (HNDL)
# ---------------------------------------------------------------------------

class HarvestNowDecryptLater:
    """
    Simulate the HNDL attack: adversaries record encrypted traffic today
    and decrypt it once a CRQC exists.
    """

    CRQC_YEAR = 2033  # midpoint of 2030–2035 estimate
    CURRENT_YEAR = 2026

    @staticmethod
    def _data_at_risk(
        gb_per_day: float,
        years_collected: int,
        tls_fraction: float = 0.65,
    ) -> dict:
        """Estimate stored encrypted data volume."""
        total_gb = gb_per_day * 365 * years_collected
        tls_gb = total_gb * tls_fraction
        tb = total_gb / 1024
        return {
            "total_gb": total_gb,
            "tls_gb": tls_gb,
            "total_tb": tb,
            "years": years_collected,
            "gb_per_day": gb_per_day,
        }

    def _urgency_score(self, data_sensitivity: str, retention_years: int) -> str:
        """
        CRITICAL: data still sensitive when CRQC arrives.
        urgency = (CRQC_year - current_year) < retention_years AND high sensitivity
        """
        years_until_crqc = self.CRQC_YEAR - self.CURRENT_YEAR
        if retention_years > years_until_crqc:
            if data_sensitivity in ("government", "financial", "medical", "nuclear"):
                return "CRITICAL — data intercepted TODAY will be decryptable before sensitivity expires"
            return "HIGH — long retention + approaching CRQC window"
        return "MEDIUM — CRQC arrives after data becomes stale"

    def run(self) -> QuantumThreat:
        # NSA CNSA 2.0 acknowledges HNDL: https://media.defense.gov/2022/Sep/07/2003071834/-1/-1/0/CSA_CNSA_2.0_ALGORITHMS_.PDF
        storage_scenarios = {}
        for scenario, gb_day, years in [
            ("Nation-state IXP tap",  10_000, 5),
            ("ISP backbone intercept", 1_000, 5),
            ("Enterprise VPN tap",       100, 5),
            ("Personal TLS traffic",      10, 5),
        ]:
            d = self._data_at_risk(gb_day, years)
            storage_scenarios[scenario] = (
                f"{d['total_tb']:.0f} TB total / {d['tls_gb']/1024:.0f} TB TLS "
                f"({d['years']} years × {d['gb_per_day']:,} GB/day)"
            )

        risk_categories = {
            "Government comms (10yr retention)": self._urgency_score("government", 10),
            "Financial records (7yr retention)": self._urgency_score("financial", 7),
            "Medical data (25yr retention)":     self._urgency_score("medical", 25),
            "Commercial secrets (3yr)":          self._urgency_score("commercial", 3),
            "Personal email (0yr)":              self._urgency_score("personal", 0),
        }

        sim = {**storage_scenarios, **risk_categories}
        sim["CRQC window"] = f"{self.CURRENT_YEAR}–{self.CRQC_YEAR} ({self.CRQC_YEAR - self.CURRENT_YEAR} years)"
        sim["NSA CNSA 2.0"] = "Issued 2022: agencies MUST migrate to PQC NOW"
        sim["Affected protocols"] = "TLS 1.2/1.3 (RSA/ECDHE), SSH, IPsec, S/MIME"

        return QuantumThreat(
            name="Harvest Now, Decrypt Later (HNDL)",
            algorithm="HNDL (store-now, Shor's-decrypt-later)",
            target="All RSA/ECDH-protected data in transit TODAY",
            classical_security="Secure today (correct key agreement)",
            quantum_security=(
                "ZERO post-CRQC — all intercepted ciphertexts become readable. "
                "Urgency is proportional to data lifetime, NOT CRQC arrival."
            ),
            qubits_logical=4098,  # RSA-2048 via Shor's
            qubits_physical_est=1_000_000_000,
            crqc_year_est="2030–2035 (NSA, CISA estimate)",
            urgency="CRITICAL — action required NOW for long-lived sensitive data",
            defense=(
                "1. Deploy hybrid PQC: ML-KEM-768 + ECDHE in TLS today (Chrome/Firefox support). "
                "2. CNSA 2.0 compliance: ML-KEM-1024 for national security systems by 2030. "
                "3. Prioritize: government > financial > medical > commercial traffic. "
                "4. Enable forward secrecy (ephemeral keys) — limits blast radius. "
                "5. Inventory long-lived encrypted archives for retroactive risk."
            ),
            simulation_result=sim,
        )


# ---------------------------------------------------------------------------
# 6. AI-Assisted Cryptographic Attack
# ---------------------------------------------------------------------------

class AIAssistedCryptoAttack:
    """
    Demonstrate how AI/ML amplifies classical cryptographic attacks.
    """

    ATTACK_TYPES = [
        {
            "name": "Neural Network Differential Cryptanalysis",
            "description": (
                "Gohr (2019, CRYPTO) showed a neural network distinguisher for "
                "Speck-32/64 that outperforms all classical differential distinguishers. "
                "The NN learns non-linear differential approximations the human analyst misses."
            ),
            "impact": "HIGH",
            "target": "Lightweight block ciphers (Speck, Simon, PRESENT)",
            "defense": "Use AES-256 (no known NN distinguisher for full rounds).",
        },
        {
            "name": "ML Side-Channel Analysis (power/EM traces → key bits)",
            "description": (
                "Deep learning on oscilloscope power traces achieves >99% key-byte "
                "recovery accuracy with <1000 traces (vs. >50000 for CPA). "
                "Reference: Maghrebi et al. (2016), Benadjila et al. (2020) ASCAD dataset."
            ),
            "impact": "CRITICAL",
            "target": "Hardware crypto (smart cards, HSMs, microcontrollers)",
            "defense": "Masking, shuffling, noise injection, EM shielding, TVLA testing.",
        },
        {
            "name": "ML Timing Attack Optimization",
            "description": (
                "Reinforcement learning agent learns optimal query sequence to maximize "
                "timing information leakage from remote servers. Reduces required samples "
                "by 10–100× compared to classical timing analysis."
            ),
            "impact": "HIGH",
            "target": "Remote RSA/ECDSA implementations, TLS servers",
            "defense": "Constant-time implementations, Nginx/OpenSSL with RSA blinding.",
        },
        {
            "name": "LLM-Assisted Vulnerability Discovery",
            "description": (
                "Large language models fine-tuned on CVE databases and crypto source code "
                "discover implementation flaws (timing leaks, padding errors, nonce reuse) "
                "faster than manual audit. GPT-4 class models find ~40% of crypto CVEs "
                "when given source code context (Pearce et al. 2023)."
            ),
            "impact": "HIGH",
            "target": "Crypto library source code, TLS configurations",
            "defense": "Formal verification (HACL*, EverCrypt), fuzzing, automated SAST.",
        },
        {
            "name": "Deepfake + Social Engineering for Key Material Theft",
            "description": (
                "AI-generated deepfake audio/video impersonates executives or IT staff "
                "to social-engineer HSM operators into exporting key material. "
                "Most expensive HSM is useless if the operator is deceived. "
                "Ferrari (2024): CFO voice cloned, $25M transferred."
            ),
            "impact": "CRITICAL",
            "target": "Key custodians, HSM operators, certificate authorities",
            "defense": (
                "Multi-party key ceremonies, M-of-N secret sharing (Shamir), "
                "out-of-band identity verification, deepfake detection tools."
            ),
        },
    ]

    def run(self) -> list[QuantumThreat]:
        threats = []
        for atk in self.ATTACK_TYPES:
            threats.append(QuantumThreat(
                name=f"AI-Assisted: {atk['name']}",
                algorithm="AI/ML-enhanced classical attack",
                target=atk["target"],
                classical_security="Varies per target",
                quantum_security=(
                    "AI acceleration persists in quantum era — amplifies quantum attacks. "
                    "Grover+NN distinguisher is an active research area."
                ),
                qubits_logical=None,
                qubits_physical_est=None,
                crqc_year_est="N/A — AI attacks work on classical hardware TODAY",
                urgency=atk["impact"],
                defense=atk["defense"],
                simulation_result={
                    "Description": atk["description"][:120] + "...",
                    "Impact": atk["impact"],
                },
            ))
        return threats


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main():
    print("\n" + "#" * 76)
    print("  QUANTUM-ERA CRYPTOGRAPHIC ATTACK SIMULATION LAB")
    print("  Defensive Security / Educational — Not for offensive use")
    print("#" * 76)

    all_threats: list[QuantumThreat] = []

    # Shor's RSA
    print("\n\n>>> [1/5] SHOR'S ALGORITHM — RSA ATTACKS")
    for t in ShorsRSAAttack().run():
        all_threats.append(t)
        t.display()

    # Shor's ECC
    print("\n\n>>> [2/5] SHOR'S ALGORITHM — ECC ATTACKS")
    for t in ShorsECCAttack().run():
        all_threats.append(t)
        t.display()

    # Grover's AES
    print("\n\n>>> [3/5] GROVER'S ALGORITHM — AES ATTACKS")
    for t in GroversAESAttack().run():
        all_threats.append(t)
        t.display()

    # Grover's SHA-256
    print("\n\n>>> [4/5] GROVER'S / BHT — SHA-256 ATTACKS")
    for t in GroversSHA256Attack().run():
        all_threats.append(t)
        t.display()

    # HNDL
    print("\n\n>>> [5/5] HARVEST NOW DECRYPT LATER (HNDL)")
    hndl = HarvestNowDecryptLater().run()
    all_threats.append(hndl)
    hndl.display()

    # AI-assisted
    print("\n\n>>> [BONUS] AI-ASSISTED CRYPTOGRAPHIC ATTACKS")
    for t in AIAssistedCryptoAttack().run():
        all_threats.append(t)
        t.display()

    # Threat matrix summary
    print("\n\n" + "=" * 76)
    print("  QUANTUM THREAT MATRIX — SUMMARY")
    print("=" * 76)
    print(f"  {'Threat':<44} {'Urgency':<12} {'Logical Qubits'}")
    print("  " + "-" * 72)
    for t in all_threats:
        lq = f"{t.qubits_logical:,}" if t.qubits_logical else "N/A"
        print(f"  {t.name[:44]:<44} {t.urgency[:12]:<12} {lq}")
    print("=" * 76)

    critical = sum(1 for t in all_threats if "CRITICAL" in t.urgency)
    high = sum(1 for t in all_threats if "HIGH" in t.urgency and "CRITICAL" not in t.urgency)
    print(f"\n  Total threats: {len(all_threats)}  |  CRITICAL: {critical}  |  HIGH: {high}")
    print()


if __name__ == "__main__":
    main()
