#!/usr/bin/env python3
"""Master runner for QC Crypto Lab customer demo scenarios."""
import sys, importlib.util, pathlib, argparse, json, time

ROOT = pathlib.Path(__file__).parent

SCENARIOS = {
    "M1-S1": ("module1-foundations/src/qubit_demo.py",              "Qubit & Superposition Visualiser",        "✅"),
    "M1-S2": ("module1-foundations/src/entanglement_demo.py",        "Quantum Entanglement Demo",               "✅"),
    "M1-S3": ("module1-foundations/src/no_cloning_demo.py",          "No-Cloning Theorem Proof",                "✅"),
    "M1-S4": ("module1-foundations/src/shors_algorithm.py",          "Shor's Algorithm — RSA Threat",           "✅"),
    "M1-S5": ("module1-foundations/src/grovers_algorithm.py",        "Grover's Algorithm — Search Speedup",     "✅"),
    "M1-S6": ("../../pqc-control-tower/src/pqc_benchmark.py",        "Classical vs Quantum Crypto Comparison",  "🔄"),
    "M2-S1": ("../../qc-security-lab/src/qkd_bb84.py",               "BB84 Protocol — Full Simulation",         "✅"),
    "M2-S2": ("module2-qkd/src/bb84_privacy_amplification.py",       "BB84 — Privacy Amplification",            "✅"),
    "M2-S3": ("module2-qkd/src/b92_protocol.py",                     "B92 Protocol",                            "✅"),
    "M2-S4": ("module2-qkd/src/e91_protocol.py",                     "E91 Protocol — Entanglement-Based QKD",   "✅"),
    "M2-S5": ("module2-qkd/src/cv_qkd.py",                           "CV-QKD — Continuous Variable",            "✅"),
    "M2-S6": ("module2-qkd/src/fiber_qkd_channel.py",                "Fiber-Optic QKD Channel Model",           "✅"),
    "M2-S7": ("module2-qkd/src/qkd_security_proof.py",               "QKD Security Proof — Info-Theoretic",     "✅"),
    "M3-S1": ("module3-attacks/src/intercept_resend_attack.py",      "Intercept-Resend Attack on BB84",         "✅"),
    "M3-S2": ("module3-attacks/src/pns_attack.py",                   "Photon Number Splitting (PNS) Attack",    "✅"),
    "M3-S3": ("module3-attacks/src/trojan_horse_attack.py",          "Trojan Horse Attack Simulation",          "✅"),
    "M3-S4": ("module3-attacks/src/side_channel_analysis.py",        "Side-Channel Attack Analysis",            "✅"),
    "M3-S5": ("module3-attacks/src/qrng.py",                         "QRNG — Quantum Random Number Generator",  "✅"),
    "M3-S6": ("module3-attacks/src/mdi_qkd.py",                      "MDI-QKD",                                 "✅"),
    "M3-S7": ("module3-attacks/src/grover_aes_attack.py",            "Grover Attack on AES",                    "✅"),
    "M4-S1": ("../../qc-security-lab/src/pqc_benchmark.py",          "ML-KEM (Kyber) Benchmark",                "✅"),
    "M4-S2": ("../../qc-security-lab/src/pqc_benchmark.py",          "ML-DSA (Dilithium) Benchmark",            "✅"),
    "M4-S3": ("../../pqc-control-tower/src/pqc_benchmark.py",        "SLH-DSA (SPHINCS+) Benchmark",            "✅"),
    "M4-S4": ("../../qc-security-lab/src/pqc_benchmark.py",          "Falcon Benchmark",                        "✅"),
    "M4-S5": ("module4-pqc/src/lwe_demo.py",                         "LWE — Learning With Errors Demo",         "✅"),
    "M4-S6": ("module4-pqc/src/ntru_demo.py",                        "NTRU Lattice Encryption",                 "✅"),
    "M4-S7": ("module4-pqc/src/mceliece_demo.py",                    "McEliece Code-Based Crypto",              "✅"),
    "M4-S8": ("module4-pqc/src/bike_hqc_demo.py",                    "BIKE / HQC — NIST Alternates",            "✅"),
    "M4-S9": ("module4-pqc/src/rainbow_demo.py",                     "Rainbow Multivariate Signatures",         "✅"),
    "M4-S10":("module4-pqc/src/hybrid_pqc_tls.py",                   "Hybrid Classical-PQC System",             "✅"),
    "M4-S11":("../../pqc-control-tower/src/pqc_benchmark.py",        "PQC Algorithm Comparison Dashboard",      "✅"),
    "M4-S12":("../../pqc-control-tower/src/crypto_inventory.py",     "Cryptographic Inventory & CBOM",          "✅"),
    "M5-S1": ("module5-applications/src/quantum_digital_signatures.py","Quantum Digital Signatures (QDS)",      "✅"),
    "M5-S2": ("module5-applications/src/quantum_authentication.py",  "Quantum Authentication Protocol",         "✅"),
    "M5-S3": ("module5-applications/src/quantum_resistant_blockchain.py","Quantum-Resistant Blockchain",        "✅"),
    "M5-S4": ("module5-applications/src/trusted_relay_network.py",   "Trusted Relay QKD Network",               "✅"),
    "M5-S5": ("module5-applications/src/micius_case_study.py",       "Micius Satellite QKD Case Study",         "✅"),
    "M5-S6": ("module5-applications/src/quantum_secure_cloud.py",    "Quantum Secure Cloud Computing",          "✅"),
    "M5-S7": ("module5-applications/src/smpc_demo.py",               "Secure Multi-Party Computation (SMPC)",   "✅"),
    "M5-S8": ("module5-applications/src/quantum_internet_stack.py",  "Quantum Internet Stack Demo",             "✅"),
    "M5-S9": ("../../pqc-control-tower/src/migration_planner.py",    "PQC Migration Roadmap Generator",         "✅"),
    "M5-S10":("../../qc-security-lab/src/quantum_ids.py",            "Quantum IDS — Intrusion Detection",       "✅"),
}

def list_scenarios():
    print(f"\n{'ID':<8} {'Status':<4} {'Scenario'}")
    print("-" * 70)
    current_module = ""
    for sid, (path, name, status) in SCENARIOS.items():
        mod = sid[:2]
        if mod != current_module:
            labels = {"M1":"Module 1 — Foundations","M2":"Module 2 — QKD","M3":"Module 3 — Attacks",
                      "M4":"Module 4 — PQC","M5":"Module 5 — Applications"}
            print(f"\n  {labels.get(mod, mod)}")
            current_module = mod
        exists = (ROOT / path).exists()
        avail = "  " if exists else "??"
        print(f"  {sid:<8} {status} {avail} {name}")
    impl = sum(1 for _,_,s in SCENARIOS.values() if s == "✅")
    print(f"\n  Total: {len(SCENARIOS)} | Implemented: {impl} | Pending: {len(SCENARIOS)-impl}\n")

def run_scenario(sid):
    if sid not in SCENARIOS:
        print(f"Unknown scenario: {sid}. Use --list to see all.")
        sys.exit(1)
    path, name, status = SCENARIOS[sid]
    full = (ROOT / path).resolve()
    if not full.exists():
        print(f"[{sid}] File not found: {full}")
        sys.exit(1)
    print(f"\n{'='*70}")
    print(f"  {sid}: {name}")
    print(f"{'='*70}\n")
    spec = importlib.util.spec_from_file_location("scenario", full)
    mod = importlib.util.module_from_spec(spec)
    t0 = time.time()
    spec.loader.exec_module(mod)
    if hasattr(mod, "main"):
        mod.main()
    print(f"\n[Done in {time.time()-t0:.1f}s]\n")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="QC Crypto Lab scenario runner")
    p.add_argument("scenario", nargs="?", help="Scenario ID e.g. M1-S4")
    p.add_argument("--list", action="store_true")
    p.add_argument("--all", action="store_true")
    args = p.parse_args()
    if args.list or not args.scenario:
        list_scenarios()
    elif args.all:
        for sid in SCENARIOS:
            try: run_scenario(sid)
            except Exception as e: print(f"[{sid}] ERROR: {e}")
    else:
        run_scenario(args.scenario.upper())
