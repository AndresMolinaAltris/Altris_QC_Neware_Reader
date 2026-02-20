"""
Tests for vectorized IR extraction (Step 2).
Verifies timing improvement and numerical correctness.
"""
import time
import pytest


def test_ir_extraction_is_fast(loaded_df, sample_ndax_path):
    from features import Features
    f = Features(sample_ndax_path)
    cycle = int(loaded_df["Cycle"].iloc[0])
    features = {}
    t0 = time.perf_counter()
    f.extract_internal_resistance_soc_100(loaded_df, features, cycle)
    f.extract_internal_resistance_soc_0(loaded_df, features, cycle)
    elapsed = time.perf_counter() - t0
    print(f"\n[STEP2] ir_extraction_both_methods: {elapsed:.4f}s")
    assert elapsed < 0.1, f"IR extraction took {elapsed:.4f}s (limit 0.1s)"


def test_ir_produces_non_nan_or_graceful(loaded_df, sample_ndax_path):
    """IR methods should either return a numeric value or np.nan — never raise."""
    import numpy as np
    from features import Features
    f = Features(sample_ndax_path)
    cycle = int(loaded_df["Cycle"].iloc[0])
    features = {}
    f.extract_internal_resistance_soc_100(loaded_df, features, cycle)
    f.extract_internal_resistance_soc_0(loaded_df, features, cycle)
    for key, val in features.items():
        assert val is None or isinstance(val, float), (
            f"{key} returned unexpected type {type(val)}"
        )
