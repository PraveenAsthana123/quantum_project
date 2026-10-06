#!/usr/bin/env python3

from pathlib import Path
import json

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import duckdb
import xarray as xr
import h5py
import zarr

ROOT = Path("/mnt/deepa/quantum")
OUT = ROOT / "results" / "data-engineering-tests"
DATA = ROOT / "datasets" / "generated" / "transpiler-benchmarks"

OUT.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

df = pd.DataFrame({
    "circuit": ["bell", "ghz", "qft"],
    "qubits": [2, 3, 3],
    "depth": [2, 3, 5],
    "fidelity": [1.0, 1.0, 0.999],
})

parquet_file = DATA / "benchmark.parquet"

table = pa.Table.from_pandas(df)
pq.write_table(table, parquet_file)

query = duckdb.sql(
    f"SELECT AVG(depth) AS avg_depth FROM read_parquet('{parquet_file}')"
).fetchone()[0]

h5_file = OUT / "state-data.h5"

with h5py.File(h5_file, "w") as h5:
    h5.create_dataset("probability", data=np.array([0.5, 0.5]))

xr_ds = xr.Dataset(
    {
        "fidelity": (
            ("circuit",),
            np.array([1.0, 1.0, 0.999]),
        )
    },
    coords={
        "circuit": ["bell", "ghz", "qft"]
    },
)

zarr_path = OUT / "sweep.zarr"
xr_ds.to_zarr(zarr_path, mode="w")

payload = {
    "parquet": str(parquet_file),
    "duckdb_avg_depth": float(query),
    "hdf5": str(h5_file),
    "zarr": str(zarr_path),
}

(OUT / "data-test.json").write_text(
    json.dumps(payload, indent=2)
)

print(json.dumps(payload, indent=2))
print("DATA ENGINEERING TEST: PASS")
