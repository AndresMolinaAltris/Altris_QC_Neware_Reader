"""
Tests for DataLoader (Step 3A).
Verifies copy=False default, copy=True behaviour, no mutation from features, and speed.
"""
import time
import pytest


def test_get_data_no_copy_returns_same_object(data_loader, sample_ndax_path):
    """Default get_data() returns the cached object directly (no copy)."""
    df1 = data_loader.get_data(sample_ndax_path)
    df2 = data_loader.get_data(sample_ndax_path)
    assert df1 is df2, "Expected the same object on repeated get_data() calls"


def test_get_data_copy_is_different_object(data_loader, sample_ndax_path):
    """get_data(copy=True) returns a new object each time."""
    df1 = data_loader.get_data(sample_ndax_path, copy=True)
    df2 = data_loader.get_data(sample_ndax_path, copy=True)
    assert df1 is not df2, "Expected distinct copies for get_data(copy=True)"


def test_get_data_no_mutation_from_features_extract(data_loader, sample_ndax_path):
    """Running Features.extract should not mutate the cached DataFrame."""
    from features import Features
    df_before = data_loader.get_data(sample_ndax_path)
    original_len = len(df_before)
    f = Features(sample_ndax_path)
    # extract works on a copy internally — cached df should be unaffected
    cycle = int(df_before["Cycle"].iloc[0])
    mass = df_before.attrs.get("active_mass") or 0.025
    f.extract(df_before, cycle, mass)
    df_after = data_loader.get_data(sample_ndax_path)
    assert len(df_after) == original_len, "Cached DataFrame length changed after Features.extract"


def test_repeated_get_data_is_fast(data_loader, sample_ndax_path):
    """100 repeated get_data() calls complete in under 0.01s total."""
    t0 = time.perf_counter()
    for _ in range(100):
        data_loader.get_data(sample_ndax_path)
    elapsed = time.perf_counter() - t0
    print(f"\n[STEP3A] 100x get_data: {elapsed:.4f}s")
    assert elapsed < 0.01, f"100 get_data calls took {elapsed:.4f}s (limit 0.01s)"
