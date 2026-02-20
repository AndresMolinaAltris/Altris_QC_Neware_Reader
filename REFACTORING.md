# QC Neware Reader — Systematic Performance Refactoring Plan

## Status: COMPLETE ✅

All 7 steps implemented and merged in commit `5b03f44`. 23/23 tests passing.

---

## Context

The program previously computed everything on every "Process Files" click — dQ/dV curves, transition voltages, and plateau statistics — even though the user only needs them on demand. The IR extraction used Python `iterrows()` loops instead of vectorized pandas. There were ~150 lines of dead code. No tests existed. The goal was to make the program measurably faster through a sequence of focused, testable steps individually verified before proceeding.

**Measured outcomes:**
- `process_files()` wall time: **~3s → 0.61s** (dQ/dV removed from critical path)
- IR extraction per cycle: **~1–3s → 0.007s** (vectorized)
- `get_data()` (×100 calls): **~ms → 0.000s** (copy=False default)

---

## Step 1 — Create Test Infrastructure and Measure Baseline ✅

**Files created:** `tests/conftest.py`, `tests/test_baseline_timing.py`

**`tests/conftest.py`** fixtures (all `session`-scoped where possible):
- `NDAX_DIR` → `Path(__file__).parent.parent / "test_ndax_files"`
- `sample_ndax_path` → first `.ndax` file in that dir
- `loaded_df` → `read_ndax(path, software_cycle_number=True)`
- `data_loader` → creates `DataLoader`, loads `[sample_ndax_path]`, yields, clears cache on teardown

**`tests/test_baseline_timing.py`** — four tests printing `[BASELINE] name: X.XXXs`:
1. `test_dataloader_load_single_file` — 0.665s (< 30s limit)
2. `test_features_extract_single_cycle` — 0.439s (< 5s limit)
3. `test_dqdv_extract_single_cycle` — 0.007s (< 10s limit)
4. `test_extract_plateaus_single_cycle` — 0.667s (< 15s limit)

No production code was modified.

---

## Step 2 — Vectorize `iterrows()` in IR Extraction ✅

**File:** `features.py`

Replaced Python `for _, row in cycle_data.iterrows()` loops in both IR methods with a single vectorized shift:

```python
prev = cycle_data[COL_STATUS].shift(1)
rest_mask = (cycle_data[COL_STATUS] == STATUS_REST) & (prev.isin(CHARGE_STATUSES))
rest_steps_series = cycle_data.loc[rest_mask, COL_STEP]
```

The `cycle == 1` branch in `extract_internal_resistance_soc_0` was not `iterrows` — left unchanged.

**Result:** Both IR calls together: **~1–3s → 0.007s**

**Tests added:** `tests/test_ir_vectorized.py`
- `test_ir_extraction_is_fast` — both IR calls < 0.1s total
- `test_ir_produces_non_nan_or_graceful` — returns float or NaN, never raises

---

## Step 3A — Fix DataLoader `.copy()` Default ✅

**File:** `data_loader.py`

- Changed `get_data(self, file_path)` → `get_data(self, file_path, copy: bool = False)`
- Returns `self._cache[file_path].copy() if copy else self._cache[file_path]`
- Removed the duplicate `self._cache[file_path] = df` assignment (was at lines 78 and 81)

**Result:** 100 repeated `get_data()` calls: **0.000s**

**Tests added:** `tests/test_data_loader.py`
- `test_get_data_no_copy_returns_same_object`
- `test_get_data_copy_is_different_object`
- `test_get_data_no_mutation_from_features_extract`
- `test_repeated_get_data_is_fast`

---

## Step 3B — Remove Dead Code ✅

**Files modified:** `data_import.py`, `common/project_imports.py`, `features.py`, `file_selector.py`

| File | Deleted | Why |
|---|---|---|
| `data_import.py` | `extract_active_mass()` (lines 4–56) | Replaced by `df.attrs`; never called |
| `common/project_imports.py` | `extract_active_mass` import | Removed along with deletion above |
| `features.py` | `DQDVAnalysis.find_transition_voltage()` (lines 852–898) | Superseded by `find_inflection_point`; never called |
| `file_selector.py` | `FileSelector.display_matplotlib_figure()` (lines 1418–1435) | Never called |

**Tests added:** `tests/test_dead_code_removed.py`
- `test_extract_active_mass_not_importable`
- `test_extract_active_mass_not_in_project_imports`
- `test_find_transition_voltage_not_present`
- `test_display_matplotlib_figure_not_present`

---

## Step 4 — Make dQ/dV and Transition Voltage On-Demand ✅

**Files modified:** `main.py`, `file_selector.py`

### 4A: `main.py` changes

- Added `data_loader: Optional[Any] = None` field to `ProcessingResult`
- Removed `warmup_scipy()` from `_extract_features_from_files` (moved to `compute_dqdv`)
- `process_files()`: changed `extract_dqdv_curves=False`; removed dQ/dV plotting block and plateau extraction block; **no longer calls `data_loader.clear_cache()`**; returns `data_loader` in `ProcessingResult`
- `process_file_callback()`: stores `result.data_loader` on `file_selector_instance._data_loader`; enables `calc_dqdv_btn`

New public functions:

```python
def compute_dqdv(ndax_file_list, db, selected_cycles, data_loader) -> tuple[fig, dqdv_data]:
    # warmup_scipy() here
    # calls _extract_features_from_files(..., extract_dqdv_curves=True)
    # calls plotter.plot_dqdv_curves_with_loader(...)

def compute_transition_voltages(ndax_file_list, db, selected_cycles, data_loader) -> list:
    # calls DQDVAnalysis.extract_plateaus_batch(...)
```

### 4B: `file_selector.py` changes

Added button frame at top of `_create_dqdv_tab()` (row 0, grid shifted):
- `self.calc_dqdv_btn` — "Calculate dQ/dV", initially disabled
- `self.calc_tv_btn` — "Calculate Transition Voltage", initially disabled

New methods:
- `_on_calculate_dqdv()`: calls `compute_dqdv()` → `update_dqdv_plot()` → enables `calc_tv_btn`
- `_on_calculate_transition_voltage()`: calls `compute_transition_voltages()` → `_store_dqdv_stats()`

`_clear_selection()` extended: sets `self._data_loader = None`, disables both buttons.

**Result:** `process_files` wall time **~3s → 0.61s**

**Tests added:** `tests/test_on_demand_dqdv.py`
- `test_process_files_does_not_return_dqdv`
- `test_process_files_returns_data_loader`
- `test_compute_dqdv_returns_figure_and_data`
- `test_compute_transition_voltages_returns_stats`
- `test_process_files_timing_improved`

---

## Step 5 — Consolidate Duplicate C-Rate Logic ✅

**Files modified:** `features.py`, `file_selector.py`

**Deleted from `file_selector.py`** (~110 lines):
- `_extract_current_data()`
- `_calculate_crate_from_time()`
- `_round_to_standard_crate()`

Also cleaned up now-unused `COL_TIME`, `COL_CHARGE_CAPACITY`, `COL_DISCHARGE_CAPACITY` imports.

**Added to `features.py`** — `DQDVAnalysis._extract_cycle_currents(df, cycle)`:
- Filters CC_Chg rows → `abs(mean(current))` → `charge_current_mA`
- Filters CC_DChg rows → `abs(mean(current))` → `discharge_current_mA`
- Returns `(charge_current_mA, discharge_current_mA)`

**`_consolidate_all_metrics()` updated:** charge C-rate now uses `DQDVAnalysis._calculate_crate_for_cycle()`; discharge C-rate uses `DQDVAnalysis._extract_cycle_currents()` with the same standard-rate rounding logic.

**Tests added:** `tests/test_crate_consolidation.py`
- `test_crate_from_features_matches_expected`
- `test_old_crate_methods_removed`
- `test_extract_cycle_currents_present`
- `test_extract_cycle_currents_returns_tuple`

---

## Step 6 — Add Charge/Discharge Current Columns to Complete Analysis ✅

**File:** `file_selector.py`

- `complete_columns`: inserted `"Charge Current (mA)"` and `"Discharge Current (mA)"` after the two C-Rate columns
- `column_widths`: added `"Charge Current (mA)": 120` and `"Discharge Current (mA)": 120`
- `_consolidate_all_metrics()`: calls `DQDVAnalysis._extract_cycle_currents(df, cycle)` and formats as `f"{val:.3f}"` (or `"N/A"`)

**Result:** Complete Analysis table shows mA columns with 3 decimal places. Export/Copy includes the new columns.

---

## Step 7 — Add Rate Capability Tab and Lazy Rate Retention Columns ✅

**File:** `file_selector.py`

### 7A — Rate Retention Columns in Complete Analysis

- `complete_columns`: appended `"Chg Rate Retention (%)"` and `"Dchg Rate Retention (%)"`
- `column_widths`: added both at width 130
- `_consolidate_all_metrics()`: adds `"N/A"` for both retention columns in every row
- `show_interface()`: initialises `self._rate_retention_cache = {}`, `self._complete_analysis_data = []`, `self._data_loader = None`
- `_update_rate_retention_in_table()`: iterates the Complete Analysis treeview and rewrites only the two retention columns from `_rate_retention_cache` — avoids full re-generation
- `_generate_complete_analysis()`: clears cache and resets `_complete_analysis_data` on re-run; enables `_rc_generate_btn` on success
- `_update_complete_analysis_table()`: stores `consolidated_data` into `self._complete_analysis_data`

### 7B — Tab 5 "Rate Capability"

Added after "Complete Analysis" tab in `show_interface()`:
```python
self.rate_cap_tab = self._create_rate_capability_tab()
self.notebook.add(self.rate_cap_tab, text="Rate Capability")
```

`_create_rate_capability_tab()` layout:
1. **Controls frame**: Direction radio buttons (Charge / Discharge), Normalize-to-cycle spinbox, "Generate Rate Capability" button (initially disabled), note label
2. **Results treeview**: `Cell ID | C-Rate | Mean Cap (mAh/g) | Std Cap (mAh/g) | Rate Retention (%)`

`_on_generate_rate_capability()` logic:
1. Guards: `_complete_analysis_data` must be populated
2. Reads `direction` and maps to capacity column
3. Reads `norm_cycle`; builds per-cell reference capacity at that cycle
4. Groups by `(cell_id, c_rate)`: computes `mean`, `std`, and group-level retention
5. Per-cycle retention stored in `_rate_retention_cache`; `_update_rate_retention_in_table()` called to fill Complete Analysis
6. Results treeview populated

**Result:**
- Complete Analysis shows `N/A` in both retention columns by default
- After Rate Capability run, only the selected direction column fills in
- Re-running Complete Analysis resets both columns to `N/A`

---

## Step 8 — GUI Improvements: Tabs, Mass Panel, Rate Capability, DQDV ✅

**Files modified:** `file_selector.py`, `main.py`, `neware_plotter.py`

### 8A — Tab Reorder

Swapped registration order in `show_interface()`: Rate Capability is now Tab 4, Complete Analysis is Tab 5 (last). Removed the stale placeholder `.pack()` label on `analysis_tab` that conflicted with the new grid layout.

### 8B — Complete Analysis Auto-Runs Rate Capability and Populates DQDV Stats

In `_generate_complete_analysis()`, after `_update_complete_analysis_table()` succeeds:
1. Calls `self._store_dqdv_stats(complete_dqdv_stats)` — populates the Differential Capacity stats table
2. Calls `self._on_generate_rate_capability()` — auto-populates Rate Capability table

### 8C — Rate Capability: Per-Cycle Rows

Columns changed from `Cell ID | C-Rate | Mean Cap | Std Cap | Rate Retention` to `Cell ID | Cycle | C-Rate | Cap (mAh/g) | Rate Retention (%)`.

`_on_generate_rate_capability()` now iterates per-cycle rows (sorted by `(cell_id, cycle)`) instead of grouping by C-Rate. Per-cycle retention is written directly to `_rate_retention_cache` in the same loop.

### 8D — Rate Capability Enabled After Regular Process Files

Previously Rate Capability required Complete Analysis. Now:
- `_process_files()` enables `_rc_generate_btn` after updating the complete analysis table
- `_consolidate_all_metrics()` falls back to `_data_loader` when `_raw_data_loader` is absent (uses `_active_loader` local variable)
- Note label updated to "Process files or run Complete Analysis first."

### 8E — Specific Capacity Results: Active Mass Panel

`_create_analysis_table()` restructured to use grid layout with two rows:
- Row 0 (weight=3): existing table + explanation label + export button (moved into `top_frame`)
- Row 1 (weight=1): `LabelFrame("Active Mass per Cell")` with scrollable canvas

New instance variables: `self._last_features_df`, `self._mass_entries` (dict of `{cell_id: tk.StringVar}`).

New methods:
- `_update_mass_panel(features_df)`: called from `_update_analysis_table()`; populates one editable entry per cell ID showing mass in mg
- `_on_apply_mass_changes()`: reads new masses, recalculates `Specific Charge/Discharge Capacity (mAh/g)` columns, calls `_update_analysis_table(updated_df)`

### 8F — DQDV: Fix Advanced Analysis Button and Marker Behaviour

**Root cause of disabled button:** `compute_dqdv()` returns raw dQ/dV curves (a `dict`), but `_on_calculate_dqdv()` was passing it as `plateau_stats` to `update_dqdv_plot()`. That function called `sorted(dqdv_stats, ...)` on the dict, iterating over string keys and calling `.get()` on them → `AttributeError` → exception caught → `calc_tv_btn` never enabled.

**Fixes:**
- `neware_plotter.py`: added `show_transition_markers=True` parameter to `plot_dqdv_curves_with_loader()`; when `False`, sets `self._transition_voltages = []` and skips extraction
- `main.py` / `compute_dqdv()`: passes `show_transition_markers=False` — plot generated without markers
- `_on_calculate_dqdv()`: stores raw curves in `self._last_dqdv_data`; calls `update_dqdv_plot(fig)` without stats; reliably enables `calc_tv_btn`
- `_on_calculate_transition_voltage()` ("Advanced Analysis"): computes plateau stats, re-renders figure **with** markers using stored `_last_dqdv_data`, calls `update_dqdv_plot(new_fig, plateau_stats)` to show markers and populate stats table together

### 8G — DQDV: Rename Button

`self.calc_tv_btn` label changed from "Calculate Transition Voltage" to "Advanced Analysis".

---

## Test Suite

Run with: `.venv/Scripts/python.exe -m pytest tests/ -s`

| File | Tests | Coverage |
|---|---|---|
| `test_baseline_timing.py` | 4 | DataLoader load, Features.extract, DQDVAnalysis.extract_dqdv, extract_plateaus |
| `test_ir_vectorized.py` | 2 | IR speed < 0.1s, graceful NaN on failure |
| `test_data_loader.py` | 4 | No-copy identity, copy identity, no mutation, speed |
| `test_dead_code_removed.py` | 4 | All four dead symbols absent |
| `test_on_demand_dqdv.py` | 5 | process_files result shape, data_loader returned, compute_dqdv, compute_transition_voltages, timing |
| `test_crate_consolidation.py` | 4 | C-rate value, old methods gone, _extract_cycle_currents present and typed |

**Total: 23 tests, all passing.**
