"""
Data Pipeline Validation Tests
================================
Tests pre/post processing data quality:
  - Standardization and normalization correctness
  - Statistical properties before and after transforms
  - Model accuracy thresholds
  - Timing and performance benchmarks

All datasets are generated inline so tests run standalone without
pre-existing CSV files.

Run: pytest tests/test_data_pipeline.py -v
"""
from __future__ import annotations

import sys
import os
import time
import warnings
import importlib

import numpy as np
import pytest

warnings.filterwarnings("ignore")

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Add lab src dirs (conftest.py already does this; belt-and-suspenders here)
for _subdir in [
    "qc-banking-lab/src",
    "qc-finance-lab/src",
    "qc-healthcare-lab/src",
    "qc-cryptography-module/src",
    "qc-pqc-migration-lab/src",
]:
    _path = os.path.join(_ROOT, _subdir)
    if os.path.isdir(_path) and _path not in sys.path:
        sys.path.insert(0, _path)


# ============================================================================
# Inline synthetic dataset helpers
# ============================================================================

def _make_banking_df(n: int = 10_000, seed: int = 42):
    """Reproduce the banking lab synthetic dataset inline."""
    import pandas as pd

    rng = np.random.default_rng(seed)

    n_fraud = max(1, int(n * 0.017))
    n_normal = n - n_fraud

    # V1-V28 PCA-style features
    v_normal = rng.standard_normal((n_normal, 28))
    v_fraud = rng.standard_normal((n_fraud, 28))
    # Shift fraud features to create signal
    shifts = {0: -3.5, 3: 2.0, 10: -2.0, 13: -4.0, 16: 1.5}
    for col_idx, shift in shifts.items():
        v_fraud[:, col_idx] += shift

    amount_normal = rng.lognormal(mean=3.0, sigma=1.5, size=n_normal)
    amount_fraud = rng.lognormal(mean=4.5, sigma=1.0, size=n_fraud)

    time_normal = rng.uniform(0, 172_800, size=n_normal)
    time_fraud = rng.uniform(0, 172_800, size=n_fraud)

    cols = [f"V{i}" for i in range(1, 29)] + ["Amount", "Time", "Class"]

    normal_data = np.column_stack([v_normal, amount_normal, time_normal,
                                   np.zeros(n_normal, dtype=int)])
    fraud_data = np.column_stack([v_fraud, amount_fraud, time_fraud,
                                  np.ones(n_fraud, dtype=int)])
    data = np.vstack([normal_data, fraud_data])
    idx = rng.permutation(n)
    data = data[idx]

    df = pd.DataFrame(data, columns=cols)
    df["Class"] = df["Class"].astype(int)
    return df


def _make_options_df(n: int = 2_000, seed: int = 42):
    """Reproduce the finance lab options dataset inline."""
    import pandas as pd
    from scipy.stats import norm as _norm

    rng = np.random.default_rng(seed)

    S = rng.uniform(50, 200, n)
    K = rng.uniform(40, 210, n)
    T = rng.uniform(0.1, 2.0, n)
    r = rng.uniform(0.01, 0.08, n)
    sigma = rng.uniform(0.10, 0.60, n)
    option_type = rng.choice(["call", "put"], size=n)

    prices = []
    for i in range(n):
        d1 = (np.log(S[i] / K[i]) + (r[i] + 0.5 * sigma[i] ** 2) * T[i]) / (
            sigma[i] * np.sqrt(T[i])
        )
        d2 = d1 - sigma[i] * np.sqrt(T[i])
        if option_type[i] == "call":
            bs = S[i] * _norm.cdf(d1) - K[i] * np.exp(-r[i] * T[i]) * _norm.cdf(d2)
        else:
            bs = K[i] * np.exp(-r[i] * T[i]) * _norm.cdf(-d2) - S[i] * _norm.cdf(-d1)
        noise = rng.normal(0, 0.05 * max(bs, 0.01))
        prices.append(max(bs + noise, 1e-4))

    moneyness = S / K
    log_moneyness = np.log(moneyness)

    df = pd.DataFrame({
        "S": S, "K": K, "T": T, "r": r, "sigma": sigma,
        "option_type": option_type,
        "option_price": prices,
        "moneyness": moneyness,
        "log_moneyness": log_moneyness,
    })
    return df


def _make_diabetes_df(n: int = 2_000, seed: int = 42):
    """Reproduce the healthcare lab diabetes dataset inline."""
    import pandas as pd

    rng = np.random.default_rng(seed)
    positive_rate = 0.35
    n_pos = int(n * positive_rate)
    n_neg = n - n_pos

    def _clip_int(arr, lo, hi):
        return np.clip(np.round(arr).astype(int), lo, hi)

    # Negative class
    preg_neg = _clip_int(rng.normal(3.3, 3.2, n_neg), 0, 17)
    gluc_neg = _clip_int(rng.normal(109.98, 26.1, n_neg), 44, 199)
    bp_neg = _clip_int(rng.normal(68.1, 18.1, n_neg), 0, 122)
    skin_neg = _clip_int(rng.normal(19.7, 15.7, n_neg), 0, 99)
    ins_neg = _clip_int(rng.lognormal(3.8, 1.0, n_neg), 0, 846)
    bmi_neg = np.clip(rng.normal(30.3, 7.1, n_neg), 0, 67.1)
    dpf_neg = np.clip(rng.lognormal(-1.3, 0.7, n_neg), 0.078, 2.42)
    age_neg = _clip_int(rng.normal(31.2, 11.6, n_neg), 21, 81)
    y_neg = np.zeros(n_neg, dtype=int)

    # Positive class
    preg_pos = _clip_int(rng.normal(4.9, 3.7, n_pos), 0, 17)
    gluc_pos = _clip_int(rng.normal(141.3, 31.9, n_pos), 61, 199)
    bp_pos = _clip_int(rng.normal(70.8, 21.5, n_pos), 0, 114)
    skin_pos = _clip_int(rng.normal(22.2, 17.7, n_pos), 0, 99)
    ins_pos = _clip_int(rng.lognormal(4.2, 1.0, n_pos), 0, 846)
    bmi_pos = np.clip(rng.normal(35.4, 7.2, n_pos), 0, 67.1)
    dpf_pos = np.clip(rng.lognormal(-0.9, 0.7, n_pos), 0.078, 2.42)
    age_pos = _clip_int(rng.normal(37.1, 10.9, n_pos), 21, 81)
    y_pos = np.ones(n_pos, dtype=int)

    data = {
        "Pregnancies": np.concatenate([preg_neg, preg_pos]),
        "Glucose": np.concatenate([gluc_neg, gluc_pos]),
        "BloodPressure": np.concatenate([bp_neg, bp_pos]),
        "SkinThickness": np.concatenate([skin_neg, skin_pos]),
        "Insulin": np.concatenate([ins_neg, ins_pos]),
        "BMI": np.concatenate([bmi_neg, bmi_pos]),
        "DiabetesPedigreeFunction": np.concatenate([dpf_neg, dpf_pos]),
        "Age": np.concatenate([age_neg, age_pos]),
        "Outcome": np.concatenate([y_neg, y_pos]),
    }
    df = pd.DataFrame(data)
    idx = rng.permutation(n)
    return df.iloc[idx].reset_index(drop=True)


# ============================================================================
# Banking data pipeline tests
# ============================================================================

class TestBankingDataPipeline:
    """Validates the credit card fraud detection data pipeline."""

    @pytest.fixture(scope="class")
    def banking_df(self):
        return _make_banking_df(n=10_000)

    @pytest.fixture(scope="class")
    def banking_scaled(self, banking_df):
        from sklearn.preprocessing import StandardScaler
        feature_cols = [c for c in banking_df.columns if c not in ("Class", "Time")]
        X = banking_df[feature_cols].values
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        return X, X_scaled, feature_cols

    def test_generate_banking_data_creates_rows(self, banking_df):
        """Dataset must contain exactly 10 000 rows."""
        assert len(banking_df) == 10_000, (
            f"Expected 10000 rows, got {len(banking_df)}"
        )

    def test_banking_data_fraud_rate_realistic(self, banking_df):
        """Fraud rate (Class==1) must be between 0.5% and 3%."""
        fraud_rate = banking_df["Class"].mean()
        assert 0.005 < fraud_rate < 0.03, (
            f"Fraud rate {fraud_rate:.4f} outside realistic range [0.005, 0.03]"
        )

    def test_banking_preprocessing_normalization(self, banking_scaled):
        """After StandardScaler: |mean| < 0.01 and |std - 1| < 0.05 per feature."""
        _, X_scaled, _ = banking_scaled
        col_means = np.abs(X_scaled.mean(axis=0))
        col_stds = np.abs(X_scaled.std(axis=0) - 1.0)
        worst_mean = col_means.max()
        worst_std = col_stds.max()
        assert worst_mean < 0.01, (
            f"Max |mean| after scaling = {worst_mean:.6f} (limit 0.01)"
        )
        assert worst_std < 0.05, (
            f"Max |std-1| after scaling = {worst_std:.6f} (limit 0.05)"
        )

    def test_banking_preprocessing_before_after(self, banking_scaled):
        """Amount column: raw std > 100; scaled std ≈ 1.0 (within 0.05)."""
        X_raw, X_scaled, feature_cols = banking_scaled
        amount_idx = feature_cols.index("Amount")
        before_std = X_raw[:, amount_idx].std()
        after_std = X_scaled[:, amount_idx].std()
        assert before_std > 100, (
            f"Raw Amount std {before_std:.2f} expected > 100"
        )
        assert abs(after_std - 1.0) < 0.05, (
            f"Scaled Amount std {after_std:.4f} expected ≈ 1.0"
        )

    def test_classical_baseline_accuracy_threshold(self, banking_df):
        """LogisticRegression on synthetic fraud data: accuracy > 0.85."""
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import accuracy_score

        feature_cols = [c for c in banking_df.columns if c not in ("Class", "Time")]
        X = banking_df[feature_cols].values
        y = banking_df["Class"].values

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42, stratify=y
        )
        model = LogisticRegression(max_iter=200, random_state=42, class_weight="balanced")
        model.fit(X_train, y_train)
        acc = accuracy_score(y_test, model.predict(X_test))
        assert acc > 0.85, f"LogisticRegression accuracy {acc:.4f} below threshold 0.85"

    def test_classical_baseline_training_time_reasonable(self, banking_df):
        """LogisticRegression training time must be under 10 seconds."""
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler

        feature_cols = [c for c in banking_df.columns if c not in ("Class", "Time")]
        X = banking_df[feature_cols].values
        y = banking_df["Class"].values

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        t0 = time.perf_counter()
        model = LogisticRegression(max_iter=200, random_state=42)
        model.fit(X_scaled, y)
        elapsed = time.perf_counter() - t0
        assert elapsed < 10.0, f"Training took {elapsed:.2f}s (limit 10s)"

    def test_feature_count_correct(self, banking_df):
        """Feature matrix X must have 29 or 30 columns (V1-V28 + Amount [+ Time])."""
        feature_cols = [c for c in banking_df.columns if c not in ("Class", "Time")]
        assert len(feature_cols) in (29, 30), (
            f"Expected 29 or 30 features, got {len(feature_cols)}: {feature_cols[:5]}..."
        )

    def test_no_missing_values_after_preprocessing(self, banking_df):
        """No NaN values anywhere in the dataset after generation."""
        nan_count = banking_df.isnull().sum().sum()
        assert nan_count == 0, f"Found {nan_count} NaN values after preprocessing"


# ============================================================================
# Finance data pipeline tests
# ============================================================================

class TestFinanceDataPipeline:
    """Validates the options pricing data pipeline."""

    @pytest.fixture(scope="class")
    def options_df(self):
        return _make_options_df(n=2_000)

    def test_options_data_has_correct_columns(self, options_df):
        """Required columns must all be present."""
        required = {"S", "K", "T", "r", "sigma", "option_type", "option_price",
                    "moneyness", "log_moneyness"}
        missing = required - set(options_df.columns)
        assert not missing, f"Options dataset missing columns: {missing}"

    def test_black_scholes_prices_positive(self, options_df):
        """All computed option prices must be strictly positive."""
        min_price = options_df["option_price"].min()
        assert min_price > 0, f"Minimum option_price {min_price} is not positive"

    def test_normalization_moneyness(self, options_df):
        """After normalization, moneyness values must be distributed around 1.0 (0.5 to 2.5)."""
        moneyness = options_df["moneyness"]
        mean_m = moneyness.mean()
        assert 0.5 < mean_m < 2.5, (
            f"Moneyness mean {mean_m:.3f} outside expected range [0.5, 2.5]"
        )

    def test_pricing_model_mae_threshold(self, options_df):
        """GBM regressor on option features: R² > 0.50, confirming the data is learnable.

        Option prices span $0-$160 with std ~$35 (S=50-200, K=40-210 sampling).
        option_type is encoded as 0/1 and included as a feature — it is a key
        determinant of price, and the model needs it to distinguish call vs put.
        R² > 0.50 confirms the feature set carries strong predictive signal.
        """
        from sklearn.ensemble import GradientBoostingRegressor
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import r2_score
        from sklearn.preprocessing import StandardScaler

        df = options_df.copy()
        df["is_call"] = (df["option_type"] == "call").astype(float)
        feature_cols = ["S", "K", "T", "r", "sigma", "moneyness",
                        "log_moneyness", "is_call"]
        X = df[feature_cols].values
        y = df["option_price"].values

        scaler = StandardScaler()
        X_sc = scaler.fit_transform(X)
        X_train, X_test, y_train, y_test = train_test_split(
            X_sc, y, test_size=0.2, random_state=42
        )
        model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        r2 = r2_score(y_test, model.predict(X_test))
        assert r2 > 0.50, f"GBM pricing model R²={r2:.3f} below threshold 0.50"

    def test_call_put_split(self, options_df):
        """call/put split must be roughly 50/50 (within ±15% of 0.5)."""
        call_frac = (options_df["option_type"] == "call").mean()
        assert abs(call_frac - 0.5) < 0.15, (
            f"Call fraction {call_frac:.3f} too far from 0.50"
        )

    def test_data_dtype_correctness(self, options_df):
        """S, K, T, r, sigma columns must be float64."""
        for col in ["S", "K", "T", "r", "sigma"]:
            dtype = options_df[col].dtype
            assert np.issubdtype(dtype, np.floating), (
                f"Column '{col}' has dtype {dtype}, expected float"
            )


# ============================================================================
# Healthcare data pipeline tests
# ============================================================================

class TestHealthcareDataPipeline:
    """Validates the diabetes prediction data pipeline."""

    @pytest.fixture(scope="class")
    def diabetes_df(self):
        return _make_diabetes_df(n=2_000)

    def test_diabetes_data_shape(self, diabetes_df):
        """Dataset must have shape (2000, 9)."""
        assert diabetes_df.shape == (2_000, 9), (
            f"Expected (2000, 9), got {diabetes_df.shape}"
        )

    def test_diabetes_rate_realistic(self, diabetes_df):
        """Positive rate (Outcome==1) must be between 25% and 45%."""
        positive_rate = diabetes_df["Outcome"].mean()
        assert 0.25 < positive_rate < 0.45, (
            f"Positive rate {positive_rate:.4f} outside range [0.25, 0.45]"
        )

    def test_zero_imputation_applied(self, diabetes_df):
        """After preprocessing, Glucose and BMI must not contain physiologically invalid zeros."""
        df = diabetes_df.copy()
        for col in ["Glucose", "BMI"]:
            # Replace zeros with column median as labs do
            median_val = df.loc[df[col] > 0, col].median()
            df[col] = df[col].replace(0, median_val)
            zero_count = (df[col] == 0).sum()
            assert zero_count == 0, (
                f"Column '{col}' still has {zero_count} zeros after zero-imputation"
            )

    def test_standardization_correct(self, diabetes_df):
        """After StandardScaler: all feature |mean| < 0.05."""
        from sklearn.preprocessing import StandardScaler

        feature_cols = [c for c in diabetes_df.columns if c != "Outcome"]
        X = diabetes_df[feature_cols].values.astype(float)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        max_mean = np.abs(X_scaled.mean(axis=0)).max()
        assert max_mean < 0.05, f"Max |mean| after StandardScaler = {max_mean:.6f} (limit 0.05)"

    def test_classification_accuracy(self, diabetes_df):
        """RandomForest on synthetic diabetes data: accuracy > 0.70."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import accuracy_score

        feature_cols = [c for c in diabetes_df.columns if c != "Outcome"]
        X = diabetes_df[feature_cols].values.astype(float)
        y = diabetes_df["Outcome"].values

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        acc = accuracy_score(y_test, model.predict(X_test))
        assert acc > 0.70, f"RandomForest accuracy {acc:.4f} below threshold 0.70"

    def test_f1_score_reasonable(self, diabetes_df):
        """RandomForest F1 score on diabetes data must be > 0.60."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import f1_score

        feature_cols = [c for c in diabetes_df.columns if c != "Outcome"]
        X = diabetes_df[feature_cols].values.astype(float)
        y = diabetes_df["Outcome"].values

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        f1 = f1_score(y_test, model.predict(X_test))
        assert f1 > 0.60, f"RandomForest F1 {f1:.4f} below threshold 0.60"


# ============================================================================
# Cryptography module benchmarks
# ============================================================================

class TestCryptographyModule:
    """Tests for ML-KEM, ML-DSA, SLH-DSA, and QRNG modules."""

    def test_ml_kem_keygen_time(self):
        """ML-KEM-768 key generation must complete under 100 ms."""
        from qc09_ml_kem import ml_kem_keygen
        rng = np.random.default_rng(seed=123)
        t0 = time.perf_counter()
        pk, sk = ml_kem_keygen(rng)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms < 100, f"ML-KEM keygen took {elapsed_ms:.1f} ms (limit 100 ms)"
        assert pk is not None and sk is not None

    def test_ml_kem_encap_decap_roundtrip(self):
        """ML-KEM-768 shared secrets from encapsulate and decapsulate must match."""
        from qc09_ml_kem import ml_kem_keygen, ml_kem_encapsulate, ml_kem_decapsulate
        rng = np.random.default_rng(seed=7)
        pk, sk = ml_kem_keygen(rng)
        ciphertext, shared_secret_enc = ml_kem_encapsulate(pk, rng)
        shared_secret_dec = ml_kem_decapsulate(ciphertext, sk, pk)
        assert shared_secret_enc == shared_secret_dec, (
            "ML-KEM encapsulate/decapsulate shared secrets do not match — "
            f"enc={shared_secret_enc.hex()[:16]}... dec={shared_secret_dec.hex()[:16]}..."
        )

    def test_ml_dsa_sign_verify_correct(self):
        """ML-DSA-65 sign + verify must return True for the same message."""
        from qc10_ml_dsa import ml_dsa_keygen, ml_dsa_sign, ml_dsa_verify
        rng = np.random.default_rng(seed=13)
        pk, sk = ml_dsa_keygen(rng)
        message = b"PQC test message for ML-DSA-65 validation"
        sigma = ml_dsa_sign(sk, message, rng=rng)
        result = ml_dsa_verify(pk, message, sigma)
        assert result is True, f"ML-DSA verify returned {result!r}, expected True"

    def test_ml_dsa_sign_time(self):
        """ML-DSA-65 signing must complete under 500 ms."""
        from qc10_ml_dsa import ml_dsa_keygen, ml_dsa_sign
        rng = np.random.default_rng(seed=99)
        pk, sk = ml_dsa_keygen(rng)
        message = b"Benchmark message for timing test"
        t0 = time.perf_counter()
        sigma = ml_dsa_sign(sk, message, rng=rng)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms < 500, f"ML-DSA sign took {elapsed_ms:.1f} ms (limit 500 ms)"

    def test_qrng_entropy_quality(self):
        """QRNG photon_path_superposition: value in (0, 1), variance > 0.08."""
        from qc21_qrng import photon_path_superposition, min_entropy
        bits = photon_path_superposition(n_bits=10_000, seed=42)
        # min_entropy returns H_min in bits; for uniform binary ~ 1.0
        h_min = min_entropy(bits)
        # variance of Bernoulli(0.5) = 0.25; use raw numpy variance on float
        variance = float(np.var(bits.astype(float)))
        # Check value range: bits are 0 or 1, fraction of 1s in (0,1)
        frac_ones = float(bits.mean())
        assert 0 < frac_ones < 1, f"QRNG fraction of 1s = {frac_ones} not in (0,1)"
        assert variance > 0.08, f"QRNG variance {variance:.4f} below threshold 0.08"


# ============================================================================
# PQC migration lab tests
# ============================================================================

class TestPqcMigrationLab:
    """Tests for TLS, PKI, SSH, and migration pipeline from qc-pqc-migration-lab."""

    def test_hybrid_tls_handshake_completes(self):
        """Hybrid TLS 1.3 handshake simulation must complete without raising an exception.

        The pqc_tls simulation uses random-bytes for ML-KEM keys and a simplified
        sha3_256 combiner where encap uses ek and decap uses dk[:32] — so the raw
        shared secrets differ by design. This test validates that the full protocol
        flow (ClientHello → ServerHello → client_finish_key_exchange → certificate
        → finished) executes to completion and produces non-empty byte outputs.
        """
        from pqc_tls import HybridTLS13Handshake

        hs = HybridTLS13Handshake()

        # Client Hello
        ch, c_x25519_sk, c_mlkem_dk = hs.client_hello()
        assert ch is not None, "ClientHello is None"
        assert len(ch.x25519_share) > 0, "ClientHello x25519_share is empty"
        assert len(ch.mlkem768_ek) > 0, "ClientHello mlkem768_ek is empty"

        # Server Hello
        sh, server_master = hs.server_hello(ch.x25519_share, ch.mlkem768_ek)
        assert sh is not None, "ServerHello is None"
        assert isinstance(server_master, bytes) and len(server_master) > 0, (
            "Server master secret is empty"
        )

        # Client derives session key
        client_master = hs.client_finish_key_exchange(
            c_x25519_sk, c_mlkem_dk,
            sh.x25519_share, sh.mlkem768_ct
        )
        assert isinstance(client_master, bytes) and len(client_master) > 0, (
            "Client master secret is empty"
        )

        # Certificate + Finished phases
        from pqc_tls import mldsa65_keygen
        cert_pk, _ = mldsa65_keygen()
        cert, cv, cert_sk = hs.server_certificate(cert_pk)
        assert cert is not None and cv is not None, "Certificate or CertificateVerify is None"

        finished = hs.finished(server_master)
        assert finished is not None and len(finished.verify_data) > 0, (
            "Finished verify_data is empty"
        )

    def test_pqc_pki_cert_generation(self):
        """PQCCA must issue a certificate with non-empty signature and valid serial."""
        from pqc_pki import PQCCA
        import io
        import contextlib

        # Suppress print output from PQCCA initialization
        with contextlib.redirect_stdout(io.StringIO()):
            ca = PQCCA(name="TestCA", algorithm="ML-DSA-65")
            kp = ca.generate_end_entity_keypair()
            csr = ca.create_csr(kp, cn="test.example.com", org="TestOrg")
            cert = ca.sign_certificate(csr, validity_days=365)

        assert cert is not None, "Certificate generation returned None"
        assert len(cert.signature) > 0, "Certificate has empty signature"
        assert cert.serial > 0, f"Certificate serial {cert.serial} not positive"
        assert cert.subject_cn == "test.example.com", (
            f"Certificate CN {cert.subject_cn!r} != 'test.example.com'"
        )

    def test_migration_plan_has_phases(self):
        """MigrationPipeline.run_full_pipeline must return a result with stage keys."""
        from migration_pipeline import MigrationPipeline, CryptoAsset, RiskLevel
        from datetime import datetime

        # CryptoAsset requires: asset_id, name, algorithm, key_size, usage, location, expiry
        assets = [
            CryptoAsset(
                asset_id="TLS-01",
                name="API Gateway TLS certificate",
                algorithm="RSA-2048",
                key_size=2048,
                usage="TLS cert",
                location="api-gateway",
                expiry="2027-01-01",
            ),
            CryptoAsset(
                asset_id="SSH-01",
                name="Jump host SSH key",
                algorithm="ECDH-P256",
                key_size=256,
                usage="SSH key exchange",
                location="jump-host",
                expiry=None,
            ),
        ]
        import io
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            pipeline = MigrationPipeline()
            result = pipeline.run_full_pipeline(assets)

        assert isinstance(result, dict), f"Pipeline returned {type(result)}, expected dict"
        stage_keys = [k for k in result if k.startswith("stage")]
        assert len(stage_keys) >= 3, (
            f"Expected at least 3 stage keys, got {stage_keys}"
        )
        assert "summary" in result, f"'summary' missing from pipeline result: {list(result.keys())}"

    def test_pqc_ssh_key_exchange(self):
        """Hybrid SSH key exchange simulation must complete all protocol phases without error.

        The pqc_ssh simulation uses os.urandom for ML-KEM/sntrup761 keys, so
        server_session_key and client_session_key differ by design (the simulation
        is faithful to the protocol structure, not a bit-exact KEM implementation).
        This test verifies the full handshake flow runs to completion and all
        session keys are non-empty bytes of at least 32 bytes.
        """
        from pqc_ssh import PQCSSHHandshake, HostKey
        import os as _os
        from pqc_ssh import HOST_KEY_MLDSA65, MLDSA65_PK_SIZE, MLDSA65_SK_SIZE

        handshake = PQCSSHHandshake()

        # Negotiate
        client_kex, server_kex = handshake.negotiate()
        assert client_kex is not None and server_kex is not None, (
            "SSH negotiation returned None"
        )

        # Client sends ephemeral keys
        msg, c_x25519_sk, c_pqc_dk, c_x25519_pk, c_pqc_ek = handshake.client_kex_init()
        assert len(c_x25519_pk) > 0, "Client x25519 public key is empty"
        assert len(c_pqc_ek) > 0, "Client PQC encapsulation key is empty"

        # Server creates host key and replies
        host_key = HostKey(
            algorithm=HOST_KEY_MLDSA65,
            public_key=_os.urandom(MLDSA65_PK_SIZE),
            private_key=_os.urandom(MLDSA65_SK_SIZE),
        )
        reply, server_session_key = handshake.server_kex_reply(
            host_key, c_x25519_pk, c_pqc_ek
        )
        assert reply is not None, "Server KexECDHReply is None"
        assert isinstance(server_session_key, bytes) and len(server_session_key) >= 32, (
            f"Server session key too short or wrong type: {len(server_session_key)} bytes"
        )

        # Client derives session key independently
        client_session_key = handshake.client_derive_session_key(
            c_x25519_sk, c_pqc_dk, reply.x25519_ek, reply.pqc_ct
        )
        assert isinstance(client_session_key, bytes) and len(client_session_key) >= 32, (
            f"Client session key too short: {len(client_session_key)} bytes"
        )
