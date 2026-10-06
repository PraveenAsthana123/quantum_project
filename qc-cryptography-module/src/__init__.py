"""
Quantum Cryptography Module — QC-01 through QC-12
Covers QKD protocols (BB84, E91, B92, BBM92, MDI-QKD, TF-QKD, CV-QKD, SARG04)
and NIST PQC standards (ML-KEM, ML-DSA, SLH-DSA, FN-DSA/Falcon).
All implementations use stdlib + numpy only (no Qiskit).
"""

__version__ = "1.0.0"
__all__ = [
    "qc01_bb84", "qc02_e91", "qc03_b92", "qc04_bbm92",
    "qc05_mdi_qkd", "qc06_tfqkd", "qc07_cvqkd", "qc08_sarg04",
    "qc09_ml_kem", "qc10_ml_dsa", "qc11_slh_dsa", "qc12_fn_dsa",
]
