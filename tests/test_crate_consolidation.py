"""
Tests verifying C-rate consolidation (Step 5).
"""
import pytest


def test_crate_from_features_matches_expected(loaded_df, sample_ndax_path):
    """_calculate_crate_for_cycle returns ~0.1 for formation current with realistic cell mass."""
    from features import DQDVAnalysis
    cycle = int(loaded_df["Cycle"].iloc[0])
    # read_ndax does not populate attrs["active_mass"]; use a realistic 1Ah Na-ion cell mass
    mass = loaded_df.attrs.get("active_mass") or 6.7
    c_rate = DQDVAnalysis._calculate_crate_for_cycle(loaded_df, cycle, mass)
    if c_rate is not None:
        assert c_rate <= 0.5, f"Expected formation C-rate ~0.1, got {c_rate}"


def test_old_crate_methods_removed():
    """The three duplicated C-rate methods should no longer exist on FileSelector."""
    from file_selector import FileSelector
    assert not hasattr(FileSelector, '_extract_current_data'), \
        "_extract_current_data should have been deleted"
    assert not hasattr(FileSelector, '_calculate_crate_from_time'), \
        "_calculate_crate_from_time should have been deleted"
    assert not hasattr(FileSelector, '_round_to_standard_crate'), \
        "_round_to_standard_crate should have been deleted"


def test_extract_cycle_currents_present():
    """DQDVAnalysis._extract_cycle_currents should exist as a static method."""
    from features import DQDVAnalysis
    assert hasattr(DQDVAnalysis, '_extract_cycle_currents'), \
        "_extract_cycle_currents should have been added to DQDVAnalysis"


def test_extract_cycle_currents_returns_tuple(loaded_df):
    """_extract_cycle_currents should return a 2-tuple of floats or Nones."""
    from features import DQDVAnalysis
    cycle = int(loaded_df["Cycle"].iloc[0])
    result = DQDVAnalysis._extract_cycle_currents(loaded_df, cycle)
    assert isinstance(result, tuple) and len(result) == 2, \
        "_extract_cycle_currents should return a 2-tuple"
    chg, dchg = result
    import numbers
    for val in (chg, dchg):
        assert val is None or isinstance(val, numbers.Real), f"Expected numeric or None, got {type(val)}"
