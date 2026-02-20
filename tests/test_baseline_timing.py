"""
Baseline timing tests — establish performance benchmarks before any refactoring.
All tests print [BASELINE] <name>: X.XXXs and assert upper-bound thresholds.
"""
import time
import pytest


def test_dataloader_load_single_file(sample_ndax_path):
    from data_loader import DataLoader
    loader = DataLoader()
    t0 = time.perf_counter()
    loader.load_files([sample_ndax_path])
    elapsed = time.perf_counter() - t0
    loader.clear_cache()
    print(f"\n[BASELINE] dataloader_load_single_file: {elapsed:.3f}s")
    assert elapsed < 30, f"File load took {elapsed:.3f}s (limit 30s)"


def test_features_extract_single_cycle(loaded_df, sample_ndax_path):
    from features import Features
    f = Features(sample_ndax_path)
    cycle = int(loaded_df["Cycle"].iloc[0])
    mass = loaded_df.attrs.get("active_mass") or 0.025
    t0 = time.perf_counter()
    result = f.extract(loaded_df, cycle, mass)
    elapsed = time.perf_counter() - t0
    print(f"\n[BASELINE] features_extract_single_cycle: {elapsed:.3f}s")
    assert elapsed < 5, f"Features.extract took {elapsed:.3f}s (limit 5s)"
    assert not result.empty


def test_dqdv_extract_single_cycle(loaded_df, sample_ndax_path):
    from features import DQDVAnalysis
    dqdv = DQDVAnalysis(sample_ndax_path)
    cycle = int(loaded_df["Cycle"].iloc[0])
    mass = loaded_df.attrs.get("active_mass") or 0.025
    t0 = time.perf_counter()
    result = dqdv.extract_dqdv(loaded_df, cycle, mass)
    elapsed = time.perf_counter() - t0
    print(f"\n[BASELINE] dqdv_extract_single_cycle: {elapsed:.3f}s")
    assert elapsed < 10, f"DQDVAnalysis.extract_dqdv took {elapsed:.3f}s (limit 10s)"


def test_extract_plateaus_single_cycle(loaded_df, sample_ndax_path):
    from features import DQDVAnalysis
    dqdv = DQDVAnalysis(sample_ndax_path)
    cycle = int(loaded_df["Cycle"].iloc[0])
    mass = loaded_df.attrs.get("active_mass") or 0.025
    t0 = time.perf_counter()
    result = dqdv.extract_plateaus(loaded_df, cycle, mass)
    elapsed = time.perf_counter() - t0
    print(f"\n[BASELINE] extract_plateaus_single_cycle: {elapsed:.3f}s")
    assert elapsed < 15, f"DQDVAnalysis.extract_plateaus took {elapsed:.3f}s (limit 15s)"
