"""
Constants for Neware battery data processing.

Centralizes status strings and other magic values used across the codebase.
These values come from Neware's data format and should be updated here if
the format changes.
"""

# Status values for charge phases (used for filtering DataFrames)
STATUS_CC_CHARGE = "CC_Chg"      # Constant Current Charge
STATUS_CV_CHARGE = "CV_Chg"      # Constant Voltage Charge
STATUS_CCCV_CHARGE = "CCCV_Chg"  # Combined CC-CV Charge

# Status values for discharge phases
STATUS_CC_DISCHARGE = "CC_DChg"    # Constant Current Discharge
STATUS_CV_DISCHARGE = "CV_DChg"    # Constant Voltage Discharge
STATUS_CCCV_DISCHARGE = "CCCV_DChg"  # Combined CC-CV Discharge

# Status value for rest periods
STATUS_REST = "Rest"

# Alias sets for matching any charge or discharge status
# Used when checking if a previous step was a charge/discharge phase
CHARGE_STATUSES = {"Chg", "CC_Chg", "CV_Chg", "CCCV_Chg", "Charge"}
DISCHARGE_STATUSES = {"DChg", "CC_DChg", "CV_DChg", "CCCV_DChg", "Discharge"}

# Column names in Neware DataFrames
COL_VOLTAGE = "Voltage"
COL_CURRENT = "Current(mA)"
COL_CYCLE = "Cycle"
COL_STEP = "Step"
COL_STATUS = "Status"
COL_TIME = "Time"
COL_CHARGE_CAPACITY = "Charge_Capacity(mAh)"
COL_DISCHARGE_CAPACITY = "Discharge_Capacity(mAh)"
