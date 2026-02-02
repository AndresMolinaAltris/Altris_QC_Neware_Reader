# Claude Code Development Notes

Guidelines and lessons learned for working on this codebase.

## Project Overview

QC Neware Reader - Battery testing data analysis tool for processing Neware NDAX files.

## Key Files

- `constants.py` - Centralized Neware status strings and column names
- `features.py` - Feature extraction (capacity, internal resistance, dQ/dV)
- `main.py` - Application entry point and processing orchestration
- `file_selector.py` - Tkinter GUI
- `neware_plotter.py` - Matplotlib visualizations

## Development Guidelines

### When Modifying Constants Usage

**IMPORTANT**: When adding constants to a file, ensure ALL required constants are imported.

Common constants that are often used together:
```python
from constants import (
    STATUS_CC_CHARGE, STATUS_CC_DISCHARGE, STATUS_REST,
    CHARGE_STATUSES, DISCHARGE_STATUSES,
    COL_CYCLE, COL_STEP, COL_STATUS, COL_VOLTAGE, COL_CURRENT, COL_TIME,
    COL_CHARGE_CAPACITY, COL_DISCHARGE_CAPACITY
)
```

**Lesson learned**: Missing `COL_TIME` import broke the differential capacity panel because `_calculate_dqdv()` uses it for high C-rate detection.

### Testing After Changes

Always test with `Test_file.ndax` before committing:
```bash
.venv\Scripts\python.exe -c "
from NewareNDA import NewareNDA
from features import Features, DQDVAnalysis

df = NewareNDA.read('Test_file.ndax')
features_obj = Features('test')
result = features_obj.extract(df, cycle=1, mass=1.0)
print(result)

dqdv_obj = DQDVAnalysis('test')
dqdv_result = dqdv_obj.extract_dqdv(df, cycle=1, mass=1.0)
print('dQ/dV result:', 'OK' if dqdv_result else 'FAILED')
"
```

### Virtual Environment

Use the project's venv for all Python commands:
```bash
.venv\Scripts\python.exe <script>
```

## Common Pitfalls

1. **Missing imports after refactoring** - When replacing hardcoded strings with constants, grep for ALL usages of that string across the file
2. **GUI callback introspection** - `main.py` uses `hasattr` checks for GUI methods - fragile pattern
3. **Duplicate functions** - Check for `_new` suffix functions that may indicate dead code
