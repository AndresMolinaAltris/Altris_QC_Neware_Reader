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
