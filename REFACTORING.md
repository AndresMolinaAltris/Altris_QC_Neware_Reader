# QC Neware Reader — Systematic Performance Refactoring Plan

## Context

The program currently computes everything on every "Process Files" click — dQ/dV curves, transition voltages, and plateau statistics — even though the user only needs them on demand. The IR extraction uses Python `iterrows()` loops instead of vectorized pandas. There are ~150 lines of dead code. No tests exist. The goal is to make the program measurably faster through a sequence of focused, testable steps that can be individually verified before proceeding.

---

## Step 1 — Create Test Infrastructure and Measure Baseline

**Goal:** Establish the test harness and baseline timings before touching any production code.

**Create `tests/conftest.py`:**
- `NDAX_DIR` → `Path(__file__).parent.parent / "test_ndax_files"`
- `pytest.fixture sample_ndax_path` → first `.ndax` file in that dir
- `pytest.fixture loaded_df` → calls `read_ndax(path)`, returns DataFrame
- `pytest.fixture data_loader` → creates `DataLoader`, calls `load_files([path])`, yields, clears cache on teardown

**Create `tests/test_baseline_timing.py`** with four tests, each printing `[BASELINE] name: X.XXXs`:
1. `test_dataloader_load_single_file` — assert < 30s
2. `test_features_extract_single_cycle` — `Features(key).extract(df, 1, 0.025)`, assert < 5s *(exposes slow `iterrows()` baseline)*
3. `test_dqdv_extract_single_cycle` — `DQDVAnalysis(key).extract_dqdv(df, 1, 0.025)`, assert < 10s
4. `test_extract_plateaus_single_cycle` — `DQDVAnalysis(key).extract_plateaus(df, 1, 0.025)`, assert < 15s

**Run:** `pytest tests/ -s` — all tests must pass and print durations.

**Do not touch:** Any production code.

---

## Step 2 — Vectorize `iterrows()` in IR Extraction

**Goal:** Eliminate Python-loop row iteration in the two IR methods.

**File:** `features.py:75–159` — `extract_internal_resistance_soc_0()` and `extract_internal_resistance_soc_100()`

**Algorithm (same for both):**
1. Filter `cycle_data` to only the relevant statuses (DISCHARGE/REST or CHARGE/REST)
2. `.shift(1)` on `COL_STATUS` column to get previous status per row
3. Find REST rows where `prev_status in DISCHARGE_STATUSES` (or `CHARGE_STATUSES`)
4. Extract `COL_STEP` from those rows — rest of function logic unchanged
5. The `cycle == 1` branch in `extract_internal_resistance_soc_0` is **not iterrows** — leave it alone

**Add to `tests/test_baseline_timing.py`:**
- `test_ir_extraction_is_fast` — assert both IR calls complete in < 0.1s total
- `test_ir_produces_same_result` — keep old version temporarily as `_old_ir_soc100`, verify numerical match within `1e-6`, then delete old version

**Success criteria:** IR timing drops from ~1–3s to < 0.1s per cycle.

---

## Step 3A — Fix DataLoader `.copy()` Default

**Goal:** Stop duplicating full DataFrames on every `get_data()` call.

**File:** `data_loader.py:117`

Change signature: `def get_data(self, file_path: str, copy: bool = False)` — default becomes `copy=False`.

All callers verified safe: they don't mutate the top-level DataFrame; internal slicing already uses `.copy()`.

Also remove the duplicate `self._cache[file_path] = df` on line 81 (exact duplicate of line 78).

**Create `tests/test_data_loader.py`:**
- `test_get_data_no_copy_returns_same_object` — `get_data(p) is get_data(p)`
- `test_get_data_copy_is_different_object` — `get_data(p, copy=True) is not get_data(p, copy=True)`
- `test_get_data_no_mutation_from_features_extract` — run `Features.extract`, assert `len(df)` unchanged
- `test_repeated_get_data_is_fast` — 100 calls in < 0.01s total

---

## Step 3B — Remove Dead Code

**Goal:** Delete confirmed-dead functions to reduce codebase size by ~200 lines.

| File | Lines | Dead code | Why |
|---|---|---|---|
| `data_import.py` | 4–56 | `extract_active_mass()` | Replaced by `df.attrs`; never called |
| `common/project_imports.py` | line 7 | `extract_active_mass` import | Remove from this import too |
| `features.py` | 852–898 | `DQDVAnalysis.find_transition_voltage()` | Superseded; never called |
| `file_selector.py` | 1418–1435 | `FileSelector.display_matplotlib_figure()` | Never called |
| `data_loader.py` | 81 | Duplicate `self._cache[file_path] = df` | Done in Step 3A |

**Create `tests/test_dead_code_removed.py`:**
- `test_extract_active_mass_not_importable` — `pytest.raises(ImportError)` on import
- `test_find_transition_voltage_not_present` — `not hasattr(DQDVAnalysis, 'find_transition_voltage')`
- `test_display_matplotlib_figure_not_present` — `not hasattr(FileSelector, 'display_matplotlib_figure')`

---

## Step 4 — Make dQ/dV and Transition Voltage On-Demand

**Goal:** Tab 3 shows buttons; nothing dQ/dV-related runs until the user asks.

### 4A: Strip from `process_files()` in `main.py`

Current `process_files()` (lines 260–285) computes dQ/dV curves and plateau stats unconditionally. Changes:
- Remove `plot_dqdv_curves_with_loader()` call (lines 262–270)
- Remove `extract_plateaus_batch()` call (lines 277–285)
- Change `_extract_features_from_files` call: `extract_dqdv_curves=False`
- Remove `warmup_scipy()` from the main extract path — move it into the new on-demand compute functions
- **Do NOT call `data_loader.clear_cache()` at the end** — store the loader for on-demand use
- In `process_file_callback()`: store `data_loader` on `file_selector_instance._data_loader = data_loader`; enable `calc_dqdv_btn`

Add two new public functions to `main.py`:
```python
def compute_dqdv(ndax_file_list, db, selected_cycles, data_loader) -> tuple:
    # warmup_scipy() here
    # calls _extract_features_from_files(..., extract_dqdv_curves=True)
    # calls plotter.plot_dqdv_curves_with_loader(...)
    # returns (dqdv_fig, dqdv_data)

def compute_transition_voltages(ndax_file_list, db, selected_cycles, data_loader) -> list:
    # calls DQDVAnalysis(key).extract_plateaus_batch(...)
    # returns plateau_stats list
```

Cache lifecycle: `_data_loader` is cleared when user changes file selection or clicks "Clear Selection".

### 4B: Add buttons to Tab 3 in `file_selector.py`

In `_create_dqdv_tab()` (line 1064), add a button frame containing:
- `self.calc_dqdv_btn` — "Calculate dQ/dV", initially `state="disabled"`, calls `_on_calculate_dqdv()`
- `self.calc_tv_btn` — "Calculate Transition Voltage", initially `state="disabled"`, calls `_on_calculate_transition_voltage()`

Add two methods to `FileSelector`:
- `_on_calculate_dqdv()`: disables button → calls `compute_dqdv(...)` → calls `update_dqdv_plot(fig)` → enables `calc_tv_btn` → re-enables button
- `_on_calculate_transition_voltage()`: disables button → calls `compute_transition_voltages(...)` → updates plateau stats treeview → re-enables button

After "Process Files" succeeds: `self.calc_dqdv_btn.config(state="normal")`.
After clear/new selection: disable both buttons, set `self._data_loader = None`.

**Create `tests/test_on_demand_dqdv.py`:**
- `test_process_files_does_not_return_dqdv` — `result.dqdv_fig is None and result.plateau_stats is None`
- `test_compute_dqdv_returns_figure_and_data` — given loaded DataLoader, returns non-None fig + non-empty dict
- `test_compute_transition_voltages_returns_stats` — returns list with `'Charge Transition Voltage (V)'` key
- `test_process_files_timing_improved` — assert duration < Step 1 baseline × 0.80 (20% faster minimum)

**Success criteria:** "Process Files" only computes capacity features and plots Tab 1. Tab 3 requires explicit button clicks.

---

## Step 5 — Consolidate Duplicate C-Rate Logic

**Goal:** Remove ~110 lines of duplicated C-rate calculation from `file_selector.py`.

**Problem:** `file_selector.py:367–472` contains `_extract_current_data()`, `_calculate_crate_from_time()`, `_round_to_standard_crate()` — only used in `_consolidate_all_metrics()`. `features.py` already has `DQDVAnalysis._calculate_crate_for_cycle()` doing the same thing.

**Change in `_consolidate_all_metrics()`:** Replace the three-method C-rate block with:
```python
charge_crate = DQDVAnalysis._calculate_crate_for_cycle(df, cycle, active_mass_g)
crate_str = f"{charge_crate:.2f}" if charge_crate is not None else "N/A"
```

Then delete all three methods from `file_selector.py`.

**Create `tests/test_crate_consolidation.py`:**
- `test_crate_from_features_matches_expected` — known formation file → result ≈ 0.1
- `test_old_crate_methods_removed` — `not hasattr(FileSelector, '_extract_current_data')` etc.

---

## Execution Order and Dependencies

```
Step 1 (baseline tests)
  → Step 2 (vectorize IR)         — only features.py
  → Step 3A (DataLoader copy)     — only data_loader.py
  → Step 3B (dead code)           — data_import.py, features.py, file_selector.py
  → Step 4 (on-demand dQ/dV)      — main.py + file_selector.py
  → Step 5 (C-rate consolidation) — file_selector.py
```

Steps 2, 3A, 3B are independent of each other and can be done in any order after Step 1.

---

## Critical Files

| File | Steps | Key locations |
|---|---|---|
| `features.py` | 2, 3B | IR methods 75–159; dead `find_transition_voltage` 852–898 |
| `main.py` | 4 | `process_files` 195–300; new `compute_dqdv`, `compute_transition_voltages` |
| `file_selector.py` | 3B, 4, 5 | `_create_dqdv_tab` 1064; dead `display_matplotlib_figure` 1418–1435; C-rate methods 367–472 |
| `data_loader.py` | 3A | `get_data` line 117; duplicate cache line 81 |
| `data_import.py` | 3B | `extract_active_mass` lines 4–56 |
| `common/project_imports.py` | 3B | `extract_active_mass` import line 7 |

---

## Verification Per Step

After each step:
1. Run `pytest tests/ -s` — all prior tests must still pass
2. Launch the app with a test file
3. Check `[TIMING]` lines in the log: `grep "\[TIMING\]" logs/app.log`

Key metrics to track:
- **After Step 2:** `Features.IR_soc100 cycle=N` drops from ~1–3s → ~0.01s
- **After Step 4:** `process_files` no longer logs `plot_dqdv_curves` or `extract_plateaus_batch`
- **After Step 4:** End-to-end "Process Files" at least 20% faster (verified by `test_process_files_timing_improved`)

---

## Step 6 — Add Charge/Discharge Current Columns to Complete Analysis

**Goal:** Show the mean CC charge and discharge currents (in mA, 3 decimal places) for each cycle in the Complete Analysis table.

**Interaction with Step 5:** Step 5 deletes `_extract_current_data()` from `file_selector.py`. To avoid losing raw current access, Step 5 must be amended: instead of deleting `_extract_current_data()` entirely, **move its logic into `features.py`** as a new static method `DQDVAnalysis._extract_cycle_currents(df, cycle) -> tuple[float|None, float|None]` returning `(charge_current_mA, discharge_current_mA)`. Then `_extract_current_data()` in `file_selector.py` can be replaced by a call to this new method.

**Changes to `features.py`:**
- Add `DQDVAnalysis._extract_cycle_currents(df, cycle) -> tuple[Optional[float], Optional[float]]` near `_calculate_crate_for_cycle` (~line 712):
  - Filters `COL_STATUS == STATUS_CC_CHARGE` → `abs(mean(COL_CURRENT))` → `charge_current_mA`
  - Filters `COL_STATUS == STATUS_CC_DISCHARGE` → `abs(mean(COL_CURRENT))` → `discharge_current_mA`
  - Returns `(charge_current_mA, discharge_current_mA)`

**Changes to `file_selector.py`:**
- `complete_columns` list: insert `"Charge Current (mA)"` and `"Discharge Current (mA)"` after the two C-Rate columns (positions 4 and 5, shifting plateau columns right)
- `column_widths` dict: add entries `"Charge Current (mA)": 120` and `"Discharge Current (mA)": 120`
- `_consolidate_all_metrics()`: call `DQDVAnalysis._extract_cycle_currents(df, cycle)` to get `(chg_I, dchg_I)`, then format as `f"{chg_I:.3f}"` (or `"N/A"` if None)

**Success criteria:** Complete Analysis table shows two new mA columns with 3 decimal places. Export/Copy includes the new columns.

---

## Step 7 — Add Rate Capability Tab and Lazy Rate Retention Columns

**Goal:** Add a "Rate Capability" tab (Tab 5) where the user can analyze capacity retention across C-rates. The Complete Analysis table gets two new rate retention columns that default to `N/A` and are only populated when the user explicitly runs Rate Capability analysis.

### Step 7A — Add Rate Retention Columns to Complete Analysis (lazy, always N/A by default)

**Changes to `file_selector.py`:**
- `complete_columns`: append `"Chg Rate Retention (%)"` and `"Dchg Rate Retention (%)"` at the end
- `column_widths` dict: add entries for both at width 130
- `_consolidate_all_metrics()`: add `"N/A"` for both retention columns in every consolidated row
- Add instance variable `self._rate_retention_cache: dict = {}` in `__init__` — keyed by `(cell_id, cycle)` → `{"chg": float|None, "dchg": float|None}`
- Add method `_update_rate_retention_in_table()`:
  - Iterates all rows of `self.complete_table` (the Treeview)
  - For each row, reads `cell_id` (col index 0) and `cycle` (col index 1)
  - Looks up `self._rate_retention_cache.get((cell_id, cycle))`
  - If found, rewrites only the retention columns using `self.complete_table.set(item, col, value)` — avoids full re-generation

### Step 7B — Create Tab 5 "Rate Capability"

**Add Tab 5** in `__init__` after the existing 4 tabs:
```python
self.rate_cap_tab = self._create_rate_capability_tab()
self.notebook.add(self.rate_cap_tab, text="Rate Capability")
```

**`_create_rate_capability_tab()` layout:**

1. **Controls frame** (top, packed):
   - Label: "Direction:" + two `ttk.Radiobutton` ("Charge", "Discharge") bound to `self._rc_direction = tk.StringVar(value="Discharge")`
   - Label: "Normalize to cycle:" + `ttk.Spinbox(from_=1, to=9999, width=6)` → `self._rc_norm_cycle`
   - `self._rc_generate_btn = ttk.Button(text="Generate Rate Capability", command=_on_generate_rate_capability, state="disabled")`
   - Note label: "Requires Complete Analysis to be generated first."

2. **Results Treeview** (below controls, with scrollbars):
   - Columns: `Cell ID | C-Rate | Mean Cap (mAh/g) | Std Cap (mAh/g) | Rate Retention (%)`
   - Populated by `_on_generate_rate_capability()`

**`_on_generate_rate_capability()` logic:**
1. Check `self._complete_analysis_data` is populated (the list returned by `_consolidate_all_metrics` from the last run); if not, show error messagebox.
2. Read `direction` (`self._rc_direction.get()`) → map "Charge" → `"Specific Charge Cap (mAh/g)"`, "Discharge" → `"Specific Discharge Cap (mAh/g)"`.
3. Read `norm_cycle = int(self._rc_norm_cycle.get())`.
4. **Normalizing capacity**: for each cell, find the row where `cycle == norm_cycle`, get that capacity as `cap_ref`. If missing, skip that cell with a warning.
5. **Group by (cell_id, c_rate)**: aggregate `mean` and `std` of the chosen capacity column across all cycles with that C-rate.
6. **Rate retention** = `(mean_cap / cap_ref) × 100` for each (cell, c_rate) group.
7. Populate the results Treeview (clear first, then insert rows).
8. **Update Complete Analysis table**: populate `self._rate_retention_cache` with per-`(cell_id, cycle)` retention values (individual cycle capacity / `cap_ref` × 100), then call `_update_rate_retention_in_table()`. Only the column matching the chosen direction is updated; the other stays `N/A`.

**State management:**
- Store consolidated data: at the end of `_generate_complete_analysis()`, assign `self._complete_analysis_data = consolidated_data` (the list from `_consolidate_all_metrics`).
- Enable `self._rc_generate_btn` when `_generate_complete_analysis()` completes successfully.
- On re-run of "Generate Complete Analysis": clear `self._rate_retention_cache = {}`, reset both retention columns to `N/A` by calling `_update_rate_retention_in_table()` (cache is empty so all cells get N/A), then re-enable `_rc_generate_btn`.

**Success criteria:**
- Complete Analysis shows `N/A` in both retention columns after normal analysis.
- After running Rate Capability (Discharge, normalize=1), "Dchg Rate Retention (%)" fills in; "Chg Rate Retention (%)" stays `N/A`.
- Re-running Complete Analysis resets both retention columns to `N/A`.
- Export/Copy of Complete Analysis includes the populated retention values (they are live in the Treeview).

---

## Execution Order (Steps 6–7)

Steps 6 and 7 depend on Step 5 being complete (C-rate consolidation). Step 6 amends Step 5's deletion plan by moving current extraction into `features.py` instead of simply deleting it. Internally, 7A must precede 7B.

```
Step 5 (C-rate consolidation — amended: move _extract_cycle_currents to features.py)
  → Step 6 (current columns in Complete Analysis)
  → Step 7A (retention columns scaffold, always N/A)
  → Step 7B (Rate Capability tab + lazy fill)
```

---

## Critical Files (Steps 6–7)

| File | Step | Key locations |
|---|---|---|
| `features.py` | 6 | Add `_extract_cycle_currents()` after `_calculate_crate_for_cycle` (~line 751) |
| `file_selector.py` | 6, 7 | `complete_columns` ~line 286; `column_widths` ~line 309; `_consolidate_all_metrics` ~line 534; `__init__` tab creation ~line 201; new `_create_rate_capability_tab()` |
| `file_selector.py` | 7A | Add `self._rate_retention_cache`, `self._complete_analysis_data`; add `_update_rate_retention_in_table()` |
| `file_selector.py` | 7B | `_on_generate_rate_capability()`; state wiring in `_generate_complete_analysis()` |
