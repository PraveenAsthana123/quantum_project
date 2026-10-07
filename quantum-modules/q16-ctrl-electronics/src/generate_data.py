#!/usr/bin/env python3
"""Control Electronics — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# electronics_specs.csv
with open(DATA_DIR / "electronics_specs.csv", "w", newline="") as _f:
    _f.writelines(['component,vendor,sample_rate_GSps,bandwidth_GHz,latency_ns\n', 'AWG,Zurich Instruments HDAWG,2.4,0.75,10\n', 'AWG,Keysight M8195A,65.0,25.0,5\n', 'FPGA,Xilinx UltraScale+,0.5,0.25,100\n', 'ADC,Zurich Instruments UHFQA,1.8,0.6,20\n'])
print(f"  Saved → {DATA_DIR / "electronics_specs.csv"}")

print("Data generation complete.")
