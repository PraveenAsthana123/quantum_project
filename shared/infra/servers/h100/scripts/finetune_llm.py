"""
LoRA fine-tuning of Llama-3.1-8B on quantum computing Q&A.
Optimized for H100 GPU with bf16 mixed precision.
"""

import argparse
import json
from pathlib import Path

try:
    import torch
    from transformers import (
        AutoTokenizer, AutoModelForCausalLM,
        TrainingArguments, Trainer, DataCollatorForLanguageModeling,
    )
    from peft import LoraConfig, get_peft_model, TaskType, PeftModel
    from datasets import Dataset
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


QUANTUM_QA = [
    {
        "question": "What is a Variational Quantum Classifier (VQC)?",
        "answer": "A VQC is a hybrid quantum-classical algorithm that uses a parameterized quantum circuit as a feature map, followed by classical optimization. Data is encoded via angle encoding (RY gates per feature), entanglement creates correlations (CNOT ring), and variational layers with trainable parameters are optimized by minimizing binary cross-entropy using COBYLA or Adam.",
    },
    {
        "question": "Why use COBYLA instead of Adam for QPU optimization?",
        "answer": "COBYLA (Constrained Optimization BY Linear Approximation) is a gradient-free optimizer, which is essential for real QPU hardware because backpropagation cannot be computed directly on quantum hardware. Adam requires exact gradients, while COBYLA only needs function evaluations. The parameter-shift rule can compute gradients on QPU but adds 2× shots overhead per parameter.",
    },
    {
        "question": "What is Zero Noise Extrapolation (ZNE)?",
        "answer": "ZNE is an error mitigation technique that runs a quantum circuit at multiple noise levels (1×, 2×, 3× noise by gate folding), measures the expectation value at each noise level, then extrapolates back to zero noise using polynomial or Richardson extrapolation. Implemented via the mitiq library. Overhead: 3× circuit executions. Typical improvement: 20-50% fidelity increase on 10-20 qubit circuits.",
    },
    {
        "question": "How does angle encoding map classical features to qubits?",
        "answer": "Angle encoding applies RY(x_i * π) to qubit i, where x_i is the i-th feature normalized to [0,1]. This rotates each qubit from |0⟩ by an angle proportional to the feature value. For 4 features, 4 qubits are needed. After encoding, CNOT gates create entanglement. The encoded state is Σ α_i |i⟩ where amplitudes depend on the feature values.",
    },
    {
        "question": "What is the barren plateau problem in VQCs?",
        "answer": "Barren plateaus occur in deep VQCs where gradients vanish exponentially with circuit depth and qubit count. The loss landscape becomes flat, making optimization impossible. Solutions: (1) layer-wise training - train one layer at a time; (2) smaller random initialization; (3) local cost functions instead of global; (4) hardware-efficient ansatz designs that avoid excessive entanglement.",
    },
    {
        "question": "How does Grover's algorithm achieve quantum speedup?",
        "answer": "Grover's algorithm searches an unsorted database of N items in O(√N) steps vs classical O(N). It uses amplitude amplification: (1) initialize superposition of all states; (2) apply oracle to flip phase of target state; (3) apply diffusion operator to invert about average amplitude; (4) repeat √N times. After √N iterations, the target state has amplitude ~1, making measurement reliable.",
    },
    {
        "question": "What is the surface code and why is it important?",
        "answer": "The surface code is a topological quantum error-correcting code that encodes 1 logical qubit in a 2D lattice of d×d physical qubits (d is the code distance). It can correct up to ⌊(d-1)/2⌋ errors. The threshold error rate is ~1%, meaning if physical gate error is below 1%, logical error decreases as code distance increases. It is the leading FTQC architecture because only nearest-neighbor gates are needed.",
    },
    {
        "question": "Explain the classical-to-quantum-to-classical (C→Q→C) pipeline.",
        "answer": "C→Q→C: (1) Classical preprocessing: clean 1000-row×1000-col data, impute missing values, remove correlated features, apply PCA to reduce 1000→4 features for quantum encoding; (2) Quantum encoding: angle encoding maps 4 features to 4 qubits via RY gates; (3) VQC: CNOT entanglement + variational layers optimized with COBYLA; (4) Measurement: ⟨Z₀⟩ expectation value; (5) Classical postprocessing: sigmoid → probability → threshold 0.5 → class label.",
    },
]


def build_dataset(tokenizer, max_length: int = 512) -> Dataset:
    """Build a fine-tuning dataset from quantum Q&A pairs."""
    texts = []
    for qa in QUANTUM_QA:
        text = (
            f"<|system|>You are an expert quantum computing assistant.<|end|>\n"
            f"<|user|>{qa['question']}<|end|>\n"
            f"<|assistant|>{qa['answer']}<|end|>"
        )
        texts.append(text)

    def tokenize(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=max_length,
            padding="max_length",
        )

    ds = Dataset.from_dict({"text": texts})
    return ds.map(tokenize, batched=True, remove_columns=["text"])


def train(model_name: str, output_dir: str, epochs: int = 3):
    if not HAS_DEPS:
        print("Missing dependencies: transformers, peft, datasets, torch")
        print("Install: pip install transformers peft datasets torch bitsandbytes")
        return

    print(f"Loading tokenizer: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print(f"Loading model: {model_name}")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.bfloat16,  # bf16 for H100 Tensor Core optimization
        device_map="auto",
        trust_remote_code=True,
    )

    # LoRA configuration
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,                          # rank — higher = more capacity
        lora_alpha=32,                 # scaling factor
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Dataset
    dataset = build_dataset(tokenizer)
    print(f"Dataset: {len(dataset)} training examples")

    # Training arguments (H100 optimized)
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,  # effective batch = 16
        learning_rate=2e-4,
        lr_scheduler_type="cosine",
        warmup_ratio=0.1,
        bf16=True,                     # H100 native bf16
        tf32=True,                     # H100 TF32 for matmuls
        logging_steps=5,
        save_strategy="epoch",
        report_to="none",              # set to "mlflow" to log metrics
        dataloader_num_workers=4,
        optim="adamw_torch_fused",     # fused optimizer for H100
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )

    print("Starting fine-tuning...")
    trainer.train()

    print(f"Saving adapter weights to {output_dir}")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print("Done.")


def main():
    parser = argparse.ArgumentParser(description="LoRA fine-tune LLM on quantum Q&A")
    parser.add_argument("--model", default="meta-llama/Llama-3.1-8B-Instruct")
    parser.add_argument("--output", default="models/quantum-llama-lora")
    parser.add_argument("--epochs", type=int, default=3)
    args = parser.parse_args()

    print("=" * 60)
    print(f"Fine-tuning: {args.model}")
    print(f"Output:      {args.output}")
    print(f"Epochs:      {args.epochs}")
    print(f"Examples:    {len(QUANTUM_QA)}")
    print("=" * 60)

    train(args.model, args.output, args.epochs)


if __name__ == "__main__":
    main()
