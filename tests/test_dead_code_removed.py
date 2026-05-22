"""
Tests verifying dead code has been removed (Step 3B).
"""
import pytest


def test_extract_active_mass_not_importable():
    """extract_active_mass must no longer exist in data_import."""
    import data_import
    assert not hasattr(data_import, "extract_active_mass"), (
        "extract_active_mass should have been deleted from data_import"
    )


def test_extract_active_mass_not_in_project_imports():
    """extract_active_mass must not be re-exported from common.project_imports."""
    import common.project_imports as pi
    assert not hasattr(pi, "extract_active_mass"), (
        "extract_active_mass should have been removed from common.project_imports"
    )


def test_find_transition_voltage_not_present():
    """DQDVAnalysis.find_transition_voltage must have been deleted."""
    from features import DQDVAnalysis
    assert not hasattr(DQDVAnalysis, "find_transition_voltage"), (
        "DQDVAnalysis.find_transition_voltage should have been deleted"
    )


def test_display_matplotlib_figure_not_present():
    """FileSelector.display_matplotlib_figure must have been deleted."""
    import sys
    # Import without starting tkinter
    import importlib
    # We can check the source rather than instantiating FileSelector (which needs a display)
    import inspect
    from file_selector import FileSelector
    assert not hasattr(FileSelector, "display_matplotlib_figure"), (
        "FileSelector.display_matplotlib_figure should have been deleted"
    )


def test_calculate_real_c_rate_not_present():
    """DQDVAnalysis.calculate_real_c_rate must have been deleted."""
    from features import DQDVAnalysis
    assert not hasattr(DQDVAnalysis, "calculate_real_c_rate"), (
        "DQDVAnalysis.calculate_real_c_rate should have been deleted"
    )


def test_preprocess_ndax_not_present():
    """NewarePlotter.preprocess_ndax_file_with_loader must have been deleted."""
    from neware_plotter import NewarePlotter
    assert not hasattr(NewarePlotter, "preprocess_ndax_file_with_loader"), (
        "NewarePlotter.preprocess_ndax_file_with_loader should have been deleted"
    )


def test_detect_fusi_steps_old_not_present():
    """Module-level _detect_fusi_steps_OLD must have been deleted from file_selector."""
    import file_selector
    assert not hasattr(file_selector, "_detect_fusi_steps_OLD"), (
        "file_selector._detect_fusi_steps_OLD should have been deleted"
    )


def test_cleanup_not_present():
    """FileSelector._cleanup must have been deleted."""
    from file_selector import FileSelector
    assert not hasattr(FileSelector, "_cleanup"), (
        "FileSelector._cleanup should have been deleted"
    )


def test_cell_db_loading_level_not_present():
    """CellDatabase.get_loading_level must have been deleted."""
    from cell_database import CellDatabase
    assert not hasattr(CellDatabase, "get_loading_level"), (
        "CellDatabase.get_loading_level should have been deleted"
    )


def test_cell_db_rebuild_cache_not_present():
    """CellDatabase.rebuild_cache must have been deleted."""
    from cell_database import CellDatabase
    assert not hasattr(CellDatabase, "rebuild_cache"), (
        "CellDatabase.rebuild_cache should have been deleted"
    )


def test_dataloader_get_by_stem_not_present():
    """DataLoader.get_data_by_stem must have been deleted."""
    from data_loader import DataLoader
    assert not hasattr(DataLoader, "get_data_by_stem"), (
        "DataLoader.get_data_by_stem should have been deleted"
    )


def test_dataloader_get_cached_stems_not_present():
    """DataLoader.get_cached_stems must have been deleted."""
    from data_loader import DataLoader
    assert not hasattr(DataLoader, "get_cached_stems"), (
        "DataLoader.get_cached_stems should have been deleted"
    )
