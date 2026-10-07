"""
quantum_explainer.py — Quantum VQC Result Explainer
=====================================================
Takes the output from the Triton quantum_vqc model (expectation values,
class probabilities, circuit metadata) and calls vLLM to produce a
structured, human-readable explanation suitable for the portal's
AI Explainability tab.

Usage:
    # Standalone test:
    python quantum_explainer.py

    # Import in portal backend:
    from quantum_explainer import QuantumExplainer
    explainer = QuantumExplainer(vllm_base_url="http://localhost:8080/v1")
    result = explainer.explain(vqc_output)
"""

import json
import re
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    raise SystemExit("openai SDK required: pip install openai")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class VQCOutput:
    """
    Output from the Triton quantum_vqc model for one inference sample.
    All fields map directly to what model.py returns.
    """
    # Raw expectation values from 4 Pauli-Z measurements
    expectation_values: list               # list of 4 floats in [-1, 1]
    # Softmax probabilities [P(not_fraud), P(fraud)]
    class_probabilities: list              # list of 2 floats summing to 1.0
    # Input features (PCA-reduced, 4 values)
    input_features: list                   # list of 4 floats
    # Circuit metadata
    n_qubits: int = 4
    n_layers: int = 3
    circuit_depth: int = 30               # approx gate count
    # Original feature names before PCA (optional — portal passes these when available)
    feature_names: list = field(default_factory=lambda: ["PCA_0", "PCA_1", "PCA_2", "PCA_3"])
    # Transaction context (optional — portal passes from upstream)
    transaction_id: Optional[str] = None
    transaction_amount: Optional[float] = None
    transaction_merchant: Optional[str] = None


@dataclass
class ExplanationResult:
    """Structured response from the vLLM explainer."""
    transaction_id: Optional[str]
    predicted_class: str                   # "fraud" or "not_fraud"
    confidence_pct: float                  # 0–100
    summary: str                           # 1–2 sentence plain-English summary
    quantum_insight: str                   # What the circuit measurement tells us
    top_features: list                     # List of {"feature": str, "value": float, "direction": str}
    risk_factors: list                     # List of str — reasons for the prediction
    recommendation: str                    # Suggested action
    model_used: str
    latency_ms: float
    raw_prompt: Optional[str] = None       # Set only in debug mode


# ---------------------------------------------------------------------------
# Explainer
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a quantum machine learning explainability assistant for a financial fraud detection system. "
    "You receive outputs from a 4-qubit variational quantum circuit (VQC) trained on transaction features. "
    "Your job is to explain what the circuit measurement means in plain language for a fraud analyst. "
    "Be precise, avoid jargon where possible, and never fabricate specific dollar amounts or names "
    "unless they are provided in the input. "
    "Always respond in valid JSON exactly matching the schema requested."
)

USER_PROMPT_TEMPLATE = """
A quantum VQC with {n_qubits} qubits and {n_layers} variational layers analyzed a transaction.

Circuit output:
- Pauli-Z expectation values per qubit: {expectation_values}
  (values near +1 = qubit collapsed to |0>, near -1 = qubit collapsed to |1>)
- Qubits 0–1 encode the "not-fraud" signal; qubits 2–3 encode the "fraud" signal.
- Class probabilities: P(not_fraud)={p_not_fraud:.3f}, P(fraud)={p_fraud:.3f}

Input features (PCA-reduced):
{feature_block}

Transaction context:
- Transaction ID: {transaction_id}
- Amount: {transaction_amount}
- Merchant: {transaction_merchant}

Using the above, produce a JSON response with exactly this schema:
{{
  "predicted_class": "<fraud|not_fraud>",
  "confidence_pct": <float 0-100>,
  "summary": "<1-2 sentence plain-English prediction summary>",
  "quantum_insight": "<1-2 sentences explaining what the qubit measurements mean>",
  "top_features": [
    {{"feature": "<name>", "value": <float>, "direction": "<increases|decreases fraud risk>"}},
    ...
  ],
  "risk_factors": ["<reason 1>", "<reason 2>", ...],
  "recommendation": "<Approve|Review|Block — with one sentence justification>"
}}

Return ONLY the JSON. No markdown code blocks. No extra text.
""".strip()


class QuantumExplainer:
    """
    Calls vLLM to generate human-readable explanations for VQC inference results.
    """

    def __init__(
        self,
        vllm_base_url: str = "http://localhost:8080/v1",
        model: str = "gemma-2-9b",
        max_tokens: int = 512,
        temperature: float = 0.15,
        debug: bool = False,
    ):
        self.client = OpenAI(base_url=vllm_base_url, api_key="no-key")
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.debug = debug

    def _build_prompt(self, vqc: VQCOutput) -> str:
        feature_lines = []
        for name, value in zip(vqc.feature_names, vqc.input_features):
            feature_lines.append(f"  {name}: {value:.4f}")
        feature_block = "\n".join(feature_lines)

        return USER_PROMPT_TEMPLATE.format(
            n_qubits=vqc.n_qubits,
            n_layers=vqc.n_layers,
            expectation_values=[round(v, 4) for v in vqc.expectation_values],
            p_not_fraud=vqc.class_probabilities[0],
            p_fraud=vqc.class_probabilities[1],
            feature_block=feature_block,
            transaction_id=vqc.transaction_id or "N/A",
            transaction_amount=f"${vqc.transaction_amount:.2f}" if vqc.transaction_amount else "N/A",
            transaction_merchant=vqc.transaction_merchant or "N/A",
        )

    def _parse_response(self, raw: str) -> dict:
        """Parse JSON from the LLM response, stripping any markdown fences."""
        # Strip common markdown code block wrappers
        clean = re.sub(r"```(?:json)?\s*", "", raw).strip()
        clean = re.sub(r"```", "", clean).strip()
        return json.loads(clean)

    def explain(self, vqc_output: VQCOutput) -> ExplanationResult:
        """
        Generate a structured explanation for a single VQC inference result.

        Args:
            vqc_output: VQCOutput dataclass populated from the Triton response.

        Returns:
            ExplanationResult with the LLM-generated explanation.
        """
        prompt = self._build_prompt(vqc_output)
        t0 = time.perf_counter()

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        latency_ms = (time.perf_counter() - t0) * 1000.0
        raw_text = response.choices[0].message.content or ""

        try:
            parsed = self._parse_response(raw_text)
        except json.JSONDecodeError as e:
            # Return a fallback explanation if JSON parsing fails
            pred = "fraud" if vqc_output.class_probabilities[1] > 0.5 else "not_fraud"
            conf = max(vqc_output.class_probabilities) * 100.0
            parsed = {
                "predicted_class": pred,
                "confidence_pct": round(conf, 1),
                "summary": f"The quantum circuit predicted {pred} with {conf:.1f}% confidence.",
                "quantum_insight": "Qubit measurements indicate " + (
                    "anomalous pattern" if pred == "fraud" else "normal transaction profile"
                ),
                "top_features": [
                    {"feature": name, "value": round(val, 4), "direction": "unknown"}
                    for name, val in zip(vqc_output.feature_names, vqc_output.input_features)
                ],
                "risk_factors": ["LLM parse error — raw output returned for review"],
                "recommendation": "Review",
            }

        predicted_class = parsed.get("predicted_class", "not_fraud")
        confidence_pct = float(parsed.get("confidence_pct", 50.0))

        return ExplanationResult(
            transaction_id=vqc_output.transaction_id,
            predicted_class=predicted_class,
            confidence_pct=confidence_pct,
            summary=parsed.get("summary", ""),
            quantum_insight=parsed.get("quantum_insight", ""),
            top_features=parsed.get("top_features", []),
            risk_factors=parsed.get("risk_factors", []),
            recommendation=parsed.get("recommendation", "Review"),
            model_used=self.model,
            latency_ms=round(latency_ms, 1),
            raw_prompt=prompt if self.debug else None,
        )

    def explain_batch(self, vqc_outputs: list) -> list:
        """
        Explain a list of VQCOutput objects.
        Sends requests sequentially (vLLM continuous-batches internally).
        """
        return [self.explain(v) for v in vqc_outputs]


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Quantum VQC result explainer demo.")
    parser.add_argument("--vllm-url", default="http://localhost:8080/v1")
    parser.add_argument("--model", default="gemma-2-9b")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    # Synthetic VQC output for demo
    vqc_demo = VQCOutput(
        expectation_values=[0.82, 0.74, -0.91, -0.88],   # qubits 2,3 strongly negative → fraud
        class_probabilities=[0.09, 0.91],                  # 91% fraud
        input_features=[-2.31, 1.87, 3.14, -0.55],
        n_qubits=4,
        n_layers=3,
        circuit_depth=30,
        feature_names=["PCA_0 (amount)", "PCA_1 (velocity)", "PCA_2 (location)", "PCA_3 (time)"],
        transaction_id="TXN-20260922-00847",
        transaction_amount=4782.50,
        transaction_merchant="Online Electronics Store",
    )

    print("[demo] Initialising QuantumExplainer ...")
    explainer = QuantumExplainer(
        vllm_base_url=args.vllm_url,
        model=args.model,
        debug=args.debug,
    )

    print("[demo] Calling vLLM to explain VQC output ...")
    result = explainer.explain(vqc_demo)

    print("\n" + "=" * 60)
    print("  QUANTUM VQC EXPLANATION RESULT")
    print("=" * 60)
    print(json.dumps(asdict(result), indent=2))
    print(f"\n[timing] LLM latency: {result.latency_ms:.1f} ms")


if __name__ == "__main__":
    main()
