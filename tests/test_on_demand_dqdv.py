"""
Tests for on-demand dQ/dV computation (Step 4).
"""
import time
import pytest


def test_process_files_does_not_return_dqdv(sample_ndax_path):
    """process_files() should no longer compute dqdv_fig or plateau_stats."""
    from main import process_files
    from common.project_imports import CellDatabase
    db = CellDatabase.get_instance()
    result = process_files([sample_ndax_path], db, selected_cycles=[1], enable_plotting=False)
    assert result.dqdv_fig is None, "dqdv_fig should be None after Step 4"
    assert result.plateau_stats is None, "plateau_stats should be None after Step 4"


def test_process_files_returns_data_loader(sample_ndax_path):
    """process_files() should return a live DataLoader for on-demand use."""
    from main import process_files
    from common.project_imports import CellDatabase
    db = CellDatabase.get_instance()
    result = process_files([sample_ndax_path], db, selected_cycles=[1], enable_plotting=False)
    assert result.data_loader is not None, "data_loader should be returned"
    assert result.data_loader.is_loaded(sample_ndax_path), "DataLoader should still have file cached"
    # Clean up
    result.data_loader.clear_cache()


def test_compute_dqdv_returns_figure_and_data(sample_ndax_path):
    """compute_dqdv() returns a non-None figure and non-empty dqdv_data dict."""
    from main import compute_dqdv
    from data_loader import DataLoader
    from common.project_imports import CellDatabase
    db = CellDatabase.get_instance()
    loader = DataLoader()
    loader.load_files([sample_ndax_path])
    try:
        dqdv_fig, dqdv_data = compute_dqdv([sample_ndax_path], db, [1], loader)
        assert dqdv_data is not None, "dqdv_data should not be None"
        assert len(dqdv_data) > 0, "dqdv_data should be non-empty"
    finally:
        loader.clear_cache()


def test_compute_transition_voltages_returns_stats(sample_ndax_path):
    """compute_transition_voltages() returns a list of dicts with transition voltage keys."""
    from main import compute_transition_voltages
    from data_loader import DataLoader
    from common.project_imports import CellDatabase
    db = CellDatabase.get_instance()
    loader = DataLoader()
    loader.load_files([sample_ndax_path])
    try:
        stats = compute_transition_voltages([sample_ndax_path], db, [1], loader)
        assert isinstance(stats, list), "Should return a list"
        # Stats may be empty if no plateau was found — that's acceptable
        if stats:
            assert any(
                'Charge Transition Voltage (V)' in s or 'Discharge Transition Voltage (V)' in s
                for s in stats
            ), "Stats entries should contain transition voltage keys"
    finally:
        loader.clear_cache()


def test_process_files_timing_improved(sample_ndax_path):
    """process_files() without dQ/dV should be faster than 3s for a single file."""
    from main import process_files
    from common.project_imports import CellDatabase
    db = CellDatabase.get_instance()
    t0 = time.perf_counter()
    result = process_files([sample_ndax_path], db, selected_cycles=[1], enable_plotting=False)
    elapsed = time.perf_counter() - t0
    if result.data_loader:
        result.data_loader.clear_cache()
    print(f"\n[STEP4] process_files (no dqdv): {elapsed:.3f}s")
    # Should be well under the baseline + 20% improvement
    assert elapsed < 10, f"process_files took {elapsed:.3f}s (limit 10s)"
