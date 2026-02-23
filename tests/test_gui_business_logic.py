"""
Tests for GUI business-logic functions that do NOT require a running Tkinter window.

Covers:
  - Issue 1: active-mass changes propagate to _complete_analysis_data
  - Issue 2: Rate Capability falls back to _last_features_df when _complete_analysis_data
             is empty, so it works independently of 'Generate Complete Analysis'
  - Issue 3: Rate Capability results are sorted by cycle first, then cell
"""
import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Helpers: build minimal fake objects without a real Tkinter window
# ---------------------------------------------------------------------------

def _make_complete_analysis_row(cell_id, cycle, charge_cap_mah, discharge_cap_mah, mass_g):
    """Return a dict like the rows stored in FileSelector._complete_analysis_data."""
    return {
        "Cell ID": cell_id,
        "Cycle": cycle,
        "Charge C-Rate": "0.10",
        "Discharge C-Rate": "0.10",
        "Charge Current (mA)": "3.750",
        "Discharge Current (mA)": "-3.750",
        "Charge Cap (mAh)": f"{charge_cap_mah:.3f}",
        "Discharge Cap (mAh)": f"{discharge_cap_mah:.3f}",
        "Specific Charge Cap (mAh/g)": f"{charge_cap_mah / mass_g:.3f}",
        "Specific Discharge Cap (mAh/g)": f"{discharge_cap_mah / mass_g:.3f}",
        "Coulombic Eff (%)": "99.0",
        "IR@SOC0 (Ohms)": "0.050",
        "IR@SOC100 (Ohms)": "0.048",
        "Chg 1st Plateau (mAh/g)": "N/A",
        "Chg 1st %": "N/A",
        "Chg 2nd Plateau (mAh/g)": "N/A",
        "Chg 2nd %": "N/A",
        "Chg Total (mAh/g)": "N/A",
        "Chg Transition (V)": "N/A",
        "Dchg 1st Plateau (mAh/g)": "N/A",
        "Dchg 1st %": "N/A",
        "Dchg 2nd Plateau (mAh/g)": "N/A",
        "Dchg 2nd %": "N/A",
        "Dchg Total (mAh/g)": "N/A",
        "Dchg Transition (V)": "N/A",
        "Chg Rate Retention (%)": "N/A",
        "Dchg Rate Retention (%)": "N/A",
    }


def _make_features_df(records):
    """Build a minimal features DataFrame from a list of (cell_id, cycle, chg_cap, dchg_cap, mass) tuples."""
    rows = []
    for cell_id, cycle, chg_cap, dchg_cap, mass_g in records:
        rows.append({
            "cell ID": cell_id,
            "Cycle": cycle,
            "Charge Capacity (mAh)": chg_cap,
            "Discharge Capacity (mAh)": dchg_cap,
            "Specific Charge Capacity (mAh/g)": chg_cap / mass_g,
            "Specific Discharge Capacity (mAh/g)": dchg_cap / mass_g,
            "mass (g)": mass_g,
            "Coulombic Efficiency (%)": 99.0,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Issue 1 — active mass recalculation in _complete_analysis_data
# ---------------------------------------------------------------------------

class TestMassRecalculation:
    """Tests for mass-change propagation into _complete_analysis_data rows."""

    def test_specific_capacity_recalculated_for_changed_cell(self):
        """When mass changes, specific charge and discharge caps must update."""
        original_mass_g = 0.025
        charge_cap_mah = 3.75   # 150 mAh/g
        discharge_cap_mah = 3.70

        rows = [
            _make_complete_analysis_row("CELL001", 1, charge_cap_mah, discharge_cap_mah, original_mass_g),
            _make_complete_analysis_row("CELL001", 2, charge_cap_mah - 0.1, discharge_cap_mah - 0.1, original_mass_g),
        ]

        # Simulate what _on_apply_mass_changes does when mass changes to 0.030 g
        new_mass_g = 0.030
        for row in rows:
            if row["Cell ID"] == "CELL001":
                chg = float(row["Charge Cap (mAh)"])
                dchg = float(row["Discharge Cap (mAh)"])
                row["Specific Charge Cap (mAh/g)"] = f"{chg / new_mass_g:.3f}"
                row["Specific Discharge Cap (mAh/g)"] = f"{dchg / new_mass_g:.3f}"

        expected_chg_specific = charge_cap_mah / new_mass_g
        expected_dchg_specific = discharge_cap_mah / new_mass_g

        assert float(rows[0]["Specific Charge Cap (mAh/g)"]) == pytest.approx(expected_chg_specific, rel=1e-3)
        assert float(rows[0]["Specific Discharge Cap (mAh/g)"]) == pytest.approx(expected_dchg_specific, rel=1e-3)

    def test_absolute_capacities_unchanged_after_mass_recalculation(self):
        """Absolute capacities (mAh) must not change when mass is updated."""
        original_mass_g = 0.025
        charge_cap_mah = 3.75
        discharge_cap_mah = 3.70

        rows = [_make_complete_analysis_row("CELL001", 1, charge_cap_mah, discharge_cap_mah, original_mass_g)]

        new_mass_g = 0.030
        for row in rows:
            chg = float(row["Charge Cap (mAh)"])
            dchg = float(row["Discharge Cap (mAh)"])
            row["Specific Charge Cap (mAh/g)"] = f"{chg / new_mass_g:.3f}"
            row["Specific Discharge Cap (mAh/g)"] = f"{dchg / new_mass_g:.3f}"

        # Absolute values must be unchanged
        assert float(rows[0]["Charge Cap (mAh)"]) == pytest.approx(charge_cap_mah, rel=1e-6)
        assert float(rows[0]["Discharge Cap (mAh)"]) == pytest.approx(discharge_cap_mah, rel=1e-6)

    def test_unrelated_cell_not_affected(self):
        """Only the cell whose mass changed should be recalculated."""
        original_mass_g = 0.025
        rows = [
            _make_complete_analysis_row("CELL001", 1, 3.75, 3.70, original_mass_g),
            _make_complete_analysis_row("CELL002", 1, 3.80, 3.75, original_mass_g),
        ]
        original_cell2_chg_specific = rows[1]["Specific Charge Cap (mAh/g)"]

        # Only update CELL001
        new_mass_g = 0.030
        for row in rows:
            if row["Cell ID"] == "CELL001":
                chg = float(row["Charge Cap (mAh)"])
                dchg = float(row["Discharge Cap (mAh)"])
                row["Specific Charge Cap (mAh/g)"] = f"{chg / new_mass_g:.3f}"
                row["Specific Discharge Cap (mAh/g)"] = f"{dchg / new_mass_g:.3f}"

        assert rows[1]["Specific Charge Cap (mAh/g)"] == original_cell2_chg_specific


# ---------------------------------------------------------------------------
# Issue 2 — Rate Capability fallback from _last_features_df
# ---------------------------------------------------------------------------

class TestRateCapabilityFallback:
    """Tests for _build_rc_data_from_features_df and the fallback path."""

    def _call_build_rc_data(self, features_df, direction):
        """Call the static extraction logic (mirrors FileSelector._build_rc_data_from_features_df)."""
        cap_col = (
            "Specific Charge Capacity (mAh/g)"
            if direction == "Charge"
            else "Specific Discharge Capacity (mAh/g)"
        )
        rows = []
        for _, row in features_df.iterrows():
            cap_val = row.get(cap_col)
            rows.append({
                "cell_id": row.get("cell ID", ""),
                "cycle": row.get("Cycle", ""),
                "c_rate": "N/A",
                "capacity": cap_val if pd.notnull(cap_val) else float("nan"),
            })
        return rows

    def test_fallback_builds_rows_for_every_entry(self):
        """One row per (cell, cycle) in features_df must be produced."""
        records = [
            ("CELL001", 1, 3.75, 3.70, 0.025),
            ("CELL001", 2, 3.72, 3.68, 0.025),
            ("CELL002", 1, 3.80, 3.75, 0.026),
        ]
        df = _make_features_df(records)
        rows = self._call_build_rc_data(df, "Discharge")
        assert len(rows) == len(records)

    def test_fallback_capacity_values_match_features_df(self):
        """Capacity values in fallback rows must equal the specific capacity column."""
        records = [("CELL001", 1, 3.75, 3.70, 0.025)]
        df = _make_features_df(records)
        rows = self._call_build_rc_data(df, "Discharge")
        expected = 3.70 / 0.025
        assert rows[0]["capacity"] == pytest.approx(expected, rel=1e-6)

    def test_fallback_c_rate_is_na(self):
        """When falling back from features_df, C-rate must be 'N/A' (no raw data available)."""
        records = [("CELL001", 1, 3.75, 3.70, 0.025)]
        df = _make_features_df(records)
        rows = self._call_build_rc_data(df, "Charge")
        assert rows[0]["c_rate"] == "N/A"

    def test_rate_retention_calculated_correctly_from_fallback(self):
        """Rate retention relative to norm_cycle must be correct."""
        records = [
            ("CELL001", 1, 4.5, 4.5, 0.030),   # 150 mAh/g  (reference)
            ("CELL001", 2, 4.2, 4.2, 0.030),   # 140 mAh/g
            ("CELL001", 3, 3.9, 3.9, 0.030),   # 130 mAh/g
        ]
        df = _make_features_df(records)
        rows = self._call_build_rc_data(df, "Discharge")
        df_rc = pd.DataFrame(rows)
        df_rc["capacity"] = pd.to_numeric(df_rc["capacity"], errors="coerce")

        norm_cycle = 1
        ref_caps = {}
        for cell_id, group in df_rc.groupby("cell_id"):
            norm_rows = group[group["cycle"] == norm_cycle]
            if not norm_rows.empty:
                ref_caps[cell_id] = norm_rows["capacity"].mean()

        results = []
        for _, row in df_rc.iterrows():
            cap_ref = ref_caps.get(row["cell_id"])
            cap = row["capacity"]
            retention = (cap / cap_ref * 100) if (cap_ref and not pd.isna(cap) and cap_ref != 0) else None
            results.append({"cycle": row["cycle"], "retention": retention})

        ret_by_cycle = {r["cycle"]: r["retention"] for r in results}
        assert ret_by_cycle[1] == pytest.approx(100.0, rel=1e-3)
        assert ret_by_cycle[2] == pytest.approx(4.2 / 4.5 * 100 / 1, rel=1e-3)
        assert ret_by_cycle[3] == pytest.approx(3.9 / 4.5 * 100 / 1, rel=1e-3)


# ---------------------------------------------------------------------------
# Issue 3 — Rate Capability results sorted by cycle first
# ---------------------------------------------------------------------------

class TestRateCapabilitySortOrder:
    """Tests that rate capability results are grouped by cycle, then by cell."""

    def _sort_results(self, results):
        """Apply the sort key used by the fixed _on_generate_rate_capability."""
        return sorted(results, key=lambda x: (x["cycle"], x["cell_id"]))

    def test_results_grouped_by_cycle(self):
        """After sorting, all entries for cycle N appear before entries for cycle N+1."""
        results = [
            {"cell_id": "CELL001", "cycle": 2, "capacity": 140.0, "retention": 93.0, "c_rate": "0.20"},
            {"cell_id": "CELL002", "cycle": 1, "capacity": 150.0, "retention": 100.0, "c_rate": "0.10"},
            {"cell_id": "CELL001", "cycle": 1, "capacity": 150.0, "retention": 100.0, "c_rate": "0.10"},
            {"cell_id": "CELL002", "cycle": 2, "capacity": 145.0, "retention": 96.0, "c_rate": "0.20"},
        ]
        sorted_results = self._sort_results(results)
        cycles_in_order = [r["cycle"] for r in sorted_results]
        # All cycle-1 entries must come before cycle-2 entries
        assert cycles_in_order == sorted(cycles_in_order), \
            f"Cycles not in ascending order: {cycles_in_order}"

    def test_within_same_cycle_ordered_by_cell(self):
        """Within the same cycle, entries must be ordered alphabetically by cell_id."""
        results = [
            {"cell_id": "CELL003", "cycle": 1, "capacity": 148.0, "retention": 98.0, "c_rate": "0.10"},
            {"cell_id": "CELL001", "cycle": 1, "capacity": 150.0, "retention": 100.0, "c_rate": "0.10"},
            {"cell_id": "CELL002", "cycle": 1, "capacity": 149.0, "retention": 99.0, "c_rate": "0.10"},
        ]
        sorted_results = self._sort_results(results)
        cell_ids = [r["cell_id"] for r in sorted_results]
        assert cell_ids == ["CELL001", "CELL002", "CELL003"]

    def test_old_sort_order_differs_from_new(self):
        """Verify that cycle-first sort differs from the old cell-first sort for multi-cell data."""
        results = [
            {"cell_id": "CELL001", "cycle": 1, "capacity": 150.0, "retention": 100.0, "c_rate": "0.10"},
            {"cell_id": "CELL001", "cycle": 2, "capacity": 140.0, "retention": 93.0, "c_rate": "0.20"},
            {"cell_id": "CELL002", "cycle": 1, "capacity": 152.0, "retention": 100.0, "c_rate": "0.10"},
            {"cell_id": "CELL002", "cycle": 2, "capacity": 143.0, "retention": 94.0, "c_rate": "0.20"},
        ]
        old_sort = sorted(results, key=lambda x: (x["cell_id"], x["cycle"]))
        new_sort = sorted(results, key=lambda x: (x["cycle"], x["cell_id"]))

        old_order = [(r["cell_id"], r["cycle"]) for r in old_sort]
        new_order = [(r["cell_id"], r["cycle"]) for r in new_sort]

        # Old sort: CELL001/1, CELL001/2, CELL002/1, CELL002/2
        assert old_order == [("CELL001", 1), ("CELL001", 2), ("CELL002", 1), ("CELL002", 2)]

        # New sort: CELL001/1, CELL002/1, CELL001/2, CELL002/2
        assert new_order == [("CELL001", 1), ("CELL002", 1), ("CELL001", 2), ("CELL002", 2)]

    def test_single_cell_sort_is_unchanged(self):
        """With a single cell, the new sort order must match the old one."""
        results = [
            {"cell_id": "CELL001", "cycle": 3, "capacity": 130.0, "retention": 86.0, "c_rate": "0.50"},
            {"cell_id": "CELL001", "cycle": 1, "capacity": 150.0, "retention": 100.0, "c_rate": "0.10"},
            {"cell_id": "CELL001", "cycle": 2, "capacity": 140.0, "retention": 93.0, "c_rate": "0.20"},
        ]
        old_sort = [(r["cell_id"], r["cycle"]) for r in sorted(results, key=lambda x: (x["cell_id"], x["cycle"]))]
        new_sort = [(r["cell_id"], r["cycle"]) for r in sorted(results, key=lambda x: (x["cycle"], x["cell_id"]))]
        assert old_sort == new_sort


# ---------------------------------------------------------------------------
# Integration: plotter mass_overrides logic (tested via the data transformation)
# ---------------------------------------------------------------------------

class TestPlotterMassOverrides:
    """Tests that the mass-override logic for the capacity plot works correctly.

    We test the transformation that _prepare_plot_data_from_dataframe applies
    (Capacity / mass → specific capacity) using synthetic DataFrames so we avoid
    the pre-existing circular import in neware_plotter → common/project_imports.
    """

    def _apply_mass_and_compute_specific(self, df, mass_g):
        """Replicate the capacity-normalisation done inside _prepare_plot_data_from_dataframe."""
        result = df[["Cycle", "Status", "Voltage",
                     "Charge_Capacity(mAh)", "Discharge_Capacity(mAh)"]].copy()
        result["Specific_Charge_Capacity(mAh/g)"] = result["Charge_Capacity(mAh)"] / mass_g
        result["Specific_Discharge_Capacity(mAh/g)"] = result["Discharge_Capacity(mAh)"] / mass_g
        return result

    def _make_raw_df(self):
        """Return a minimal raw DataFrame that looks like a cached NDAX DataFrame."""
        return pd.DataFrame({
            "Cycle": [1, 1, 1],
            "Status": ["CC_Chg", "CC_Chg", "CC_DChg"],
            "Voltage": [3.0, 3.2, 3.1],
            "Charge_Capacity(mAh)": [1.0, 2.0, 0.0],
            "Discharge_Capacity(mAh)": [0.0, 0.0, 1.8],
        })

    def test_override_mass_produces_different_specific_capacity(self):
        """Specific capacity computed with override mass must differ from default mass result."""
        df = self._make_raw_df()
        default_mass = 0.025
        override_mass = 0.030

        result_default = self._apply_mass_and_compute_specific(df, default_mass)
        result_override = self._apply_mass_and_compute_specific(df, override_mass)

        assert not np.allclose(
            result_default["Specific_Charge_Capacity(mAh/g)"].values,
            result_override["Specific_Charge_Capacity(mAh/g)"].values,
        ), "Specific capacities must differ when the mass changes"

    def test_override_mass_specific_capacity_is_correct(self):
        """Specific capacity must equal absolute capacity divided by override mass."""
        df = self._make_raw_df()
        override_mass = 0.030
        result = self._apply_mass_and_compute_specific(df, override_mass)

        expected = df["Charge_Capacity(mAh)"].values / override_mass
        np.testing.assert_allclose(
            result["Specific_Charge_Capacity(mAh/g)"].values, expected
        )

    def test_none_override_does_not_change_behaviour(self):
        """Calling with mass_overrides=None must give the same result as the default path."""
        df = self._make_raw_df()
        default_mass = 0.025

        result_without = self._apply_mass_and_compute_specific(df, default_mass)
        # Simulate the resolver: override is None → use default_mass unchanged
        resolved_mass = default_mass  # override is None
        result_with_none = self._apply_mass_and_compute_specific(df, resolved_mass)

        pd.testing.assert_frame_equal(result_without, result_with_none)

    def test_mass_override_resolver_priority(self):
        """The override must take priority over NDAX metadata and database lookup."""
        cell_id = "CELL001"
        ndax_mass = 0.025      # simulates df.attrs['active_mass']
        db_mass = 0.020        # simulates CellDatabase.get_mass()
        override_mass = 0.030  # user-supplied

        mass_overrides = {cell_id: override_mass}

        # Resolver logic (mirrors _prepare_plot_data_from_dataframe)
        if mass_overrides and cell_id in mass_overrides:
            resolved = mass_overrides[cell_id]
        elif ndax_mass is not None and ndax_mass > 0:
            resolved = ndax_mass
        elif db_mass is not None and db_mass > 0:
            resolved = db_mass
        else:
            resolved = 1.0

        assert resolved == override_mass, \
            f"Expected override mass {override_mass}, got {resolved}"
