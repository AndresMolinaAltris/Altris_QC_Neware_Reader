from common.imports import os, np, pd, logging, Path
from scipy.signal import savgol_filter, find_peaks
from data_import import extract_cell_id
from constants import (
    STATUS_CC_CHARGE, STATUS_CC_DISCHARGE, STATUS_REST,
    CHARGE_STATUSES, DISCHARGE_STATUSES,
    COL_CYCLE, COL_STEP, COL_STATUS, COL_VOLTAGE, COL_CURRENT, COL_TIME,
    COL_CHARGE_CAPACITY, COL_DISCHARGE_CAPACITY
)

class Features:
    """
    A class to extract various electrochemical features from a given Neware dataset.
    Handles missing data by assigning NaN to failed extractions.
    """

    def __init__(self, input_key):
        """
        Initializes the Features class with a given input key.

        :param input_key: Key used to identify input data.
        """
        self.input_key = input_key

    def extract(self, df, cycle, mass=1.0):
        """
        Extracts multiple electrochemical features from the given dataset.

        :param df: pandas DataFrame containing experimental data.
        :param cycle: Integer representing the cycle number to extract data from.
        :param mass: Float representing the mass of active material (default: 1.0 g).
        :return: pandas DataFrame containing extracted features.
        """
        features = {}

        # List of feature extraction functions and their arguments
        functions = [
            (self.extract_charge_capacity, (df, features, cycle, mass)),
            (self.extract_discharge_capacity, (df, features, cycle, mass)),
            (self.extract_internal_resistance_soc_100, (df, features, cycle)),
            (self.extract_internal_resistance_soc_0, (df, features, cycle)),
            (self.extract_coulombic_efficiency, (df, features, cycle))  # Add the new function
        ]

        # Attempt to extract features, handling errors
        for func, args in functions:
            try:
                func(*args)
            except Exception:
                # Generate a feature name dynamically from function name
                feature_name = func.__name__.replace("extract_", "").replace("_", " ").title()
                features[feature_name] = np.nan  # Assign NaN in case of an error

        return pd.DataFrame(features, index=[0])

    def extract_internal_resistance_soc_0(self, df, features, cycle):
        label = "Internal Resistance at SOC 0 (Ohms)"
        try:
            cycle = int(cycle)
            cycle_data = df[df["Cycle"] == cycle].copy()
            if cycle_data.empty:
                features[label] = np.nan;
                return
            cycle_data = cycle_data.sort_index()

            if cycle == 1:
                idx = (df[COL_CYCLE] == 1) & (df[COL_STEP] == 1) & (df[COL_STATUS] == STATUS_REST)
            else:
                rest_steps, prev_status = [], None
                for _, row in cycle_data.iterrows():
                    if row[COL_STATUS] == STATUS_REST and prev_status in DISCHARGE_STATUSES:
                        rest_steps.append(row[COL_STEP])
                    prev_status = row[COL_STATUS]
                if not rest_steps:
                    features[label] = np.nan;
                    return
                target_step = rest_steps[-1]
                idx = (df[COL_CYCLE] == cycle) & (df[COL_STEP] == target_step) & (df[COL_STATUS] == STATUS_REST)

            if not idx.any():
                features[label] = np.nan;
                return
            index = df[idx].index[-1]
            pos = df.index.get_loc(index)
            if pos + 1 >= len(df):
                features[label] = np.nan;
                return

            ocv = float(df[COL_VOLTAGE].iloc[pos])
            ocv_dV = float(df[COL_VOLTAGE].iloc[pos + 1])
            delta_current = abs(float(df[COL_CURRENT].iloc[pos + 1]) - float(df[COL_CURRENT].iloc[pos]))
            if delta_current == 0:
                features[label] = np.nan;
                return

            features[label] = round(abs(ocv_dV - ocv) / (delta_current / 1000), 4)
        except Exception:
            features[label] = np.nan

    def extract_internal_resistance_soc_100(self, df, features, cycle):
        label = "Internal Resistance at SOC 100 (Ohms)"
        try:
            cycle = int(cycle)
            cycle_data = df[df["Cycle"] == cycle].copy()
            if cycle_data.empty:
                features[label] = np.nan;
                return
            cycle_data = cycle_data.sort_index()

            rest_steps, prev_status = [], None
            for _, row in cycle_data.iterrows():
                if row[COL_STATUS] == STATUS_REST and prev_status in CHARGE_STATUSES:
                    rest_steps.append(row[COL_STEP])
                prev_status = row[COL_STATUS]
            if not rest_steps:
                features[label] = np.nan;
                return

            target_step = rest_steps[-1]
            idx = (df[COL_CYCLE] == cycle) & (df[COL_STEP] == target_step) & (df[COL_STATUS] == STATUS_REST)
            if not idx.any():
                features[label] = np.nan;
                return

            index = df[idx].index[-1]
            pos = df.index.get_loc(index)
            if pos + 1 >= len(df):
                features[label] = np.nan;
                return

            ocv = float(df[COL_VOLTAGE].iloc[pos])
            ocv_dV = float(df[COL_VOLTAGE].iloc[pos + 1])
            delta_current = abs(float(df[COL_CURRENT].iloc[pos + 1]) - float(df[COL_CURRENT].iloc[pos]))
            if delta_current == 0:
                features[label] = np.nan;
                return

            features[label] = round(abs(ocv_dV - ocv) / (delta_current / 1000), 4)
        except Exception:
            features[label] = np.nan

    def extract_charge_capacity(self, df, features, cycle, mass=1.0):
        """
        Extracts charge capacity and specific charge capacity.

        :param df: pandas DataFrame containing experimental data.
        :param features: Dictionary to store extracted features.
        :param cycle: Integer representing the cycle number.
        :param mass: Float representing the mass of active material (default: 1.0 g).
        """
        try:
            idx = np.logical_and(df[COL_STATUS] == STATUS_CC_CHARGE, df[COL_CYCLE] == int(cycle))
            initial_charge_capacity = df[idx][COL_CHARGE_CAPACITY].max()
            initial_specific_charge_capacity = initial_charge_capacity / mass
            features["Charge Capacity (mAh)"] = round(initial_charge_capacity, 3)
            features["Specific Charge Capacity (mAh/g)"] = round(initial_specific_charge_capacity, 1)
        except Exception:
            features["Charge Capacity (mAh)"] = np.nan
            features["Specific Charge Capacity (mAh/g)"] = np.nan

    def extract_discharge_capacity(self, df, features, cycle, mass=1.0):
        """
        Extracts discharge capacity and specific discharge capacity.

        :param df: pandas DataFrame containing experimental data.
        :param features: Dictionary to store extracted features.
        :param cycle: Integer representing the cycle number.
        :param mass: Float representing the mass of active material (default: 1.0 g).
        """
        try:
            idx = np.logical_and(df[COL_STATUS] == STATUS_CC_DISCHARGE, df[COL_CYCLE] == int(cycle))
            initial_discharge_capacity = df[idx][COL_DISCHARGE_CAPACITY].max()
            initial_specific_discharge_capacity = initial_discharge_capacity / mass
            features["Discharge Capacity (mAh)"] = round(initial_discharge_capacity, 3)
            features["Specific Discharge Capacity (mAh/g)"] = round(initial_specific_discharge_capacity, 1)
        except Exception:
            features["Discharge Capacity (mAh)"] = np.nan
            features["Specific Discharge Capacity (mAh/g)"] = np.nan

    def extract_coulombic_efficiency(self, df, features, cycle):
        """
        Calculates coulombic efficiency (discharge capacity / charge capacity * 100).

        :param df: pandas DataFrame containing experimental data.
        :param features: Dictionary to store extracted features.
        :param cycle: Integer representing the cycle number.
        """
        try:
            # Get the charge and discharge capacities
            charge_capacity = features.get("Charge Capacity (mAh)", 0)
            discharge_capacity = features.get("Discharge Capacity (mAh)", 0)

            # Calculate coulombic efficiency (avoid division by zero)
            if charge_capacity > 0:
                coulombic_efficiency = (discharge_capacity / charge_capacity) * 100
                features["Coulombic Efficiency (%)"] = round(coulombic_efficiency, 1)
            else:
                features["Coulombic Efficiency (%)"] = np.nan
        except Exception:
            features["Coulombic Efficiency (%)"] = np.nan


class DQDVAnalysis:
    """
        A class to extract differential capacity  features from a given Neware dataset.
        Handles missing data by assigning NaN to failed extractions.
        """

    # C-rate dependent voltage ranges for plateau detection
    # As C-rate increases, charge peaks shift to higher potentials (overpotential)
    # and discharge peaks shift to lower potentials
    # Format: c_rate: ((charge_min, charge_max), (discharge_min, discharge_max))
    #
    # CALIBRATION STATUS:
    # - 0.1-0.2C: Experimentally validated from 136 samples (Form-Rate protocols)
    #   Observed peaks: charge 2.9-3.4V, discharge 2.9-3.3V
    # - 0.33-10C: Extrapolated from electrochemical principles (~50-100mV/C overpotential)
    #   REQUIRES VALIDATION with actual high-rate experimental data
    VOLTAGE_RANGES_BY_CRATE = {
        0.1:  ((2.9, 3.6), (2.9, 3.6)),   # Calibrated: n=136 samples, mean peaks ~3.2-3.3V
        0.2:  ((2.9, 3.6), (2.9, 3.6)),   # Calibrated: minimal overpotential increase from 0.1C
        0.33: ((2.8, 3.7), (2.8, 3.6)),   # Extrapolated: ~50mV charge shift, ~50mV discharge shift
        0.5:  ((2.8, 3.7), (2.7, 3.6)),   # Extrapolated: ~100mV charge shift, ~100mV discharge shift
        1.0:  ((2.7, 3.8), (2.6, 3.6)),   # Extrapolated: ~150mV shifts (literature-based)
        2.0:  ((2.6, 3.9), (2.4, 3.6)),   # Extrapolated: ~250mV shifts
        3.0:  ((2.5, 4.0), (2.3, 3.6)),   # Extrapolated: ~350mV shifts
        5.0:  ((2.4, 4.2), (2.1, 3.6)),   # Extrapolated: ~500mV shifts
        10.0: ((2.2, 4.4), (1.8, 3.6)),   # Extrapolated: ~700mV shifts (extreme rates)
    }

    def __init__(self, input_key):
        self.input_key = input_key

    @staticmethod
    def get_voltage_ranges(c_rate):
        """
        Get appropriate voltage ranges for plateau detection based on C-rate.

        As C-rate increases, overpotential causes charge peaks to shift to higher
        voltages and discharge peaks to shift to lower voltages. This method
        returns expanded voltage windows for higher C-rates.

        Args:
            c_rate: Float representing the C-rate (e.g., 0.1, 1.0, 5.0)
                   Can be None, in which case returns default (2.5, 3.5) ranges

        Returns:
            Tuple of (charge_voltage_range, discharge_voltage_range)
            where each range is a tuple (min_voltage, max_voltage)
        """
        if c_rate is None:
            # Default to low C-rate ranges
            logging.debug("DQDVAnalysis.get_voltage_ranges: c_rate is None, using default (2.5, 3.5)")
            return ((2.5, 3.5), (2.5, 3.5))

        # If exact match exists, use it
        if c_rate in DQDVAnalysis.VOLTAGE_RANGES_BY_CRATE:
            ranges = DQDVAnalysis.VOLTAGE_RANGES_BY_CRATE[c_rate]
            logging.debug(f"DQDVAnalysis.get_voltage_ranges: c_rate={c_rate} (exact match), ranges={ranges}")
            return ranges

        # Find nearest standard C-rate
        standard_rates = sorted(DQDVAnalysis.VOLTAGE_RANGES_BY_CRATE.keys())
        nearest = min(standard_rates, key=lambda x: abs(x - c_rate))
        ranges = DQDVAnalysis.VOLTAGE_RANGES_BY_CRATE[nearest]
        logging.debug(f"DQDVAnalysis.get_voltage_ranges: c_rate={c_rate} -> nearest={nearest}, ranges={ranges}")
        return ranges

    def _calculate_dqdv(self, data, direction, mass=1.0, smoothing_method='sma', window_length=15, weights=None,
                        pre_smooth=True):

        """
        Helper method to calculate dQ/dV for either charge or discharge data.
        Option to skip smoothing entirely for high C-rate discharge.

        Args:
            data: DataFrame containing either charge or discharge data
            direction: String indicating 'charge' or 'discharge'
            mass: Active material mass in g
            smoothing_method: Type of smoothing to apply
            window_length: Window length for smoothing
            weights: Optional weights for weighted moving average
            pre_smooth: Whether to apply pre-smoothing

        Returns:
            Dictionary with voltage, dQ/dV data and smoothed dQ/dV data
        """
        # Handle none mass
        if mass is None or mass <= 0:
            logging.debug("DQDVAnalysis: Invalid mass provided, using default 1.0g")
            mass = 1.0

        if data.empty or len(data) < 10:
            return None

        # Sort by voltage to ensure proper calculation
        if direction == 'charge':
            data = data.sort_values(COL_VOLTAGE, ascending=True)
            capacity_col = COL_CHARGE_CAPACITY
        else:
            data = data.sort_values(COL_VOLTAGE, ascending=False)
            capacity_col = COL_DISCHARGE_CAPACITY

        # Drop duplicates to reduce noise
        data = data.drop_duplicates(subset=[COL_VOLTAGE])
        data = data.reset_index(drop=True)

        # Get voltage and capacity data
        voltage = data[COL_VOLTAGE].values
        capacity = data[capacity_col].values

        # Check if this is high C-rate discharge data
        skip_smoothing = False
        if direction == 'discharge' and COL_TIME in data.columns and len(data) > 10:
            # Calculate average time step between measurements
            time_steps = data[COL_TIME].diff().dropna()
            avg_time_step = time_steps.mean()

            # Detect if this is high C-rate discharge (fast acquisition)
            is_high_crate = avg_time_step < 1.0  # Threshold of 6 seconds based on analysis of the data
            if is_high_crate:
                # For high C-rate discharge, skip smoothing entirely
                skip_smoothing = True
                logging.debug(f"High C-rate discharge detected: {avg_time_step:.2f} sec/sample")
                logging.debug(f"Skipping smoothing to preserve features")

        # Apply pre-smoothing to capacity data before differentiation
        # Skip this step for high C-rate discharge
        if pre_smooth and not skip_smoothing:
            # Standard pre-smoothing window
            pre_smooth_window = min(window_length, max(5, len(capacity) // 10))

            if smoothing_method == 'savgol':
                # Make sure window length is odd for Savitzky-Golay
                if pre_smooth_window % 2 == 0:
                    pre_smooth_window += 1

                # Use standard polynomial order
                capacity = self._apply_savgol_filter(capacity, pre_smooth_window, 2)
            else:
                # Use SMA for pre-smoothing as a safe default
                capacity = self._apply_moving_average(
                    capacity,
                    window_length=pre_smooth_window,
                    method='sma'
                )

            logging.debug(f"Applied pre-smoothing to capacity data with window size {pre_smooth_window}")

        # Calculate differences
        dv = np.diff(voltage)
        dq = np.diff(capacity)

        # Prevent division by zero
        mask = np.abs(dv) > 1e-10

        if not np.any(mask):
            return None

        # Calculate dQ/dV
        dqdv = np.zeros_like(dv)
        dqdv[mask] = dq[mask] / dv[mask]

        # Use voltage midpoints
        v_mid = (voltage[:-1] + voltage[1:]) / 2

        # Remove invalid values (infinity, NaN)
        valid_mask = np.isfinite(dqdv)
        v_mid = v_mid[valid_mask]
        dqdv = dqdv[valid_mask]

        # Further filtering (optional)
        if direction == 'charge':
            filter_mask = dqdv >= 0  # Keep positive dQ/dV for charge
        else:
            filter_mask = dqdv <= 0  # Keep negative dQ/dV for discharge

        v_mid = v_mid[filter_mask]
        dqdv = dqdv[filter_mask]

        # Normalize by mass if needed
        specific_dqdv = dqdv / mass

        # For high C-rate discharge, use raw data (no smoothing)
        if skip_smoothing:
            smoothed_dqdv = specific_dqdv  # Use raw data without smoothing
        else:
            # Apply smoothing based on method
            if smoothing_method == 'savgol':
                smoothed_dqdv = self._apply_savgol_filter(specific_dqdv, window_length)
            elif smoothing_method in ['sma', 'wma', 'ema']:
                smoothed_dqdv = self._apply_moving_average(
                    specific_dqdv,
                    window_length=window_length,
                    method=smoothing_method,
                    weights=weights)

        return {
            'voltage': v_mid,
            'dqdv': specific_dqdv,
            'smoothed_dqdv': smoothed_dqdv
        }

    def extract_dqdv(self, df, cycle, mass=1.0):
        """
        Calculates differential capacity (dQ/dV) for both charge and discharge cycles.

        Uses methodology adapted from DiffCapAnalyzer for robust dQ/dV calculations
        with appropriate data cleaning and smoothing.

        Args:
            df: pandas DataFrame containing experimental data
            cycle: Integer representing the cycle number to extract data from
            mass: Float representing the mass of active material (default: 1.0 g)

        Returns:
            Dictionary containing dQ/dV data for charge and discharge
        """
        try:
            # Filter data for the specified cycle
            cycle_df = df[df[COL_CYCLE] == int(cycle)].copy()

            # Define a minimum number of points required for proper calculation
            if len(cycle_df) < 10:
                return None

            # Separate charge and discharge data
            charge_data = cycle_df[cycle_df[COL_STATUS] == STATUS_CC_CHARGE].copy()
            discharge_data = cycle_df[cycle_df[COL_STATUS] == STATUS_CC_DISCHARGE].copy()

            # Get dQ/dV data for charge and discharge
            charge_dqdv = self._calculate_dqdv(charge_data, 'charge', mass, pre_smooth=True)
            discharge_dqdv = self._calculate_dqdv(discharge_data, 'discharge', mass, pre_smooth=True)

            return {
                'charge': charge_dqdv,
                'discharge': discharge_dqdv
            }

        except Exception as e:
            logging.debug(f"Error calculating dQ/dV: {e}")
            return None

    def _apply_savgol_filter(self, data, window_length=15, polyorder=3):
        """
        Apply Savitzky-Golay filter to smooth dQ/dV data.

        Args:
            data: Array of dQ/dV values to smooth
            window_length: Window length for filter (must be odd)
            polyorder: Polynomial order for filter

        Returns:
            Smoothed data array
        """

        # Ensure we have enough data points for the filter
        if len(data) < window_length:
            return data

        # Ensure window length is odd
        if window_length % 2 == 0:
            window_length += 1

        # Apply filter
        try:
            smoothed = savgol_filter(data, window_length, polyorder)
            return smoothed
        except Exception:
            # If filtering fails, return original data
            return data

    def _apply_moving_average(self, data, window_length=15, method='sma', weights=None):
        """
        Apply different types of moving averages to smooth data.

        Args:
            data (np.ndarray): Input data array to be smoothed
            window_length (int): Size of the moving window (must be odd)
            method (str): Type of moving average - 'sma', 'wma', or 'ema'
            weights (list, optional): Custom weights for Weighted Moving Average

        Returns:
            np.ndarray: Smoothed data array
        """

        # Ensure we have enough data points for filtering
        if len(data) < window_length:
            return data

        # Ensure window length is odd
        if window_length % 2 == 0:
            window_length += 1

        # Half window for symmetric padding
        half_window = window_length // 2

        try:
            if method == 'sma':
                # Simple Moving Average
                smoothed = np.convolve(data, np.ones(window_length) / window_length, mode='same')

            elif method == 'wma':
                # Weighted Moving Average
                if weights is None:
                    # Default: linear increasing weights
                    weights = np.arange(1, window_length + 1)

                # Normalize weights
                weights = np.array(weights) / np.sum(weights)

                # Pad the data symmetrically
                padded_data = np.pad(data, (half_window, half_window), mode='reflect')

                # Compute weighted moving average
                smoothed = np.zeros_like(data)
                for i in range(len(data)):
                    window = padded_data[i:i + window_length]
                    smoothed[i] = np.sum(window * weights)

            elif method == 'ema':
                # Exponential Moving Average
                alpha = 2 / (window_length + 1)
                smoothed = np.zeros_like(data)
                smoothed[0] = data[0]

                for i in range(1, len(data)):
                    smoothed[i] = alpha * data[i] + (1 - alpha) * smoothed[i - 1]

            else:
                raise ValueError(f"Unsupported moving average method: {method}")

            return smoothed

        except Exception as e:
            # If filtering fails, return original data
            print(f"Moving average smoothing failed: {e}")
            return data

    def extract_plateaus(self, df,
                         cycle,
                         mass=1.0,
                         transition_voltage=None,
                         charge_voltage_range=None,
                         discharge_voltage_range=None,
                         c_rate=None):
        """
        Extracts the capacities for the 1st and 2nd plateaus during charge and discharge.

        First plateau is defined as: Capacity from initial voltage to transition voltage
        Second plateau is defined as: Capacity from transition voltage to final voltage

        Args:
            df: pandas DataFrame containing experimental data
            cycle: Integer representing the cycle number to extract data from
            mass: Float representing the mass of active material (default: 1.0 g)
            transition_voltage: Optional float to specify the transition voltage
                If None, will use inflection point detection or default to 3.2V
            charge_voltage_range: Tuple with min and max voltage for charge inflection point detection
                If None, will be resolved from c_rate parameter
            discharge_voltage_range: Tuple with min and max voltage for discharge inflection point detection
                If None, will be resolved from c_rate parameter
            c_rate: Optional float representing the C-rate for this cycle
                Used to automatically determine appropriate voltage ranges if not explicitly provided

        Returns:
            Dictionary containing plateau capacities for both charge and discharge
        """
        logging.debug("FEATURES.extract_plateaus started")

        try:
            # Resolve voltage ranges from c_rate if not explicitly provided
            if charge_voltage_range is None or discharge_voltage_range is None:
                resolved_charge, resolved_discharge = self.get_voltage_ranges(c_rate)
                if charge_voltage_range is None:
                    charge_voltage_range = resolved_charge
                if discharge_voltage_range is None:
                    discharge_voltage_range = resolved_discharge
                logging.debug(f"extract_plateaus: Using c_rate={c_rate} -> charge_range={charge_voltage_range}, discharge_range={discharge_voltage_range}")

            # Define default transition voltage
            default_transition_voltage = 3.2  # V

            # If transition_voltage is not provided, try inflection point detection
            if transition_voltage is None:
                # Try to find inflection points using new method with separate voltage ranges
                inflection_result = self.find_inflection_point(df, cycle, charge_voltage_range, discharge_voltage_range)

                if inflection_result:
                    # Use inflection points if available
                    charge_transition = inflection_result.get('charge_inflection_voltage')
                    discharge_transition = inflection_result.get('discharge_inflection_voltage')

                    # Log which values we're using
                    if charge_transition:
                        logging.debug(f"Using inflection point for charge transition: {charge_transition:.4f}V")
                    else:
                        logging.debug(f"No charge inflection point found, using default: {default_transition_voltage}V")
                        charge_transition = default_transition_voltage

                    if discharge_transition:
                        logging.debug(f"Using inflection point for discharge transition: {discharge_transition:.4f}V")
                    else:
                        logging.debug(
                            f"No discharge inflection point found, using default: {default_transition_voltage}V")
                        discharge_transition = default_transition_voltage
                else:
                    # If inflection detection failed, use default for both
                    charge_transition = default_transition_voltage
                    discharge_transition = default_transition_voltage
                    logging.debug(f"Inflection point detection failed, using default: {default_transition_voltage}V")
            else:
                # Use the provided transition voltage for both charge and discharge
                charge_transition = transition_voltage
                discharge_transition = transition_voltage
                logging.debug(f"Using provided transition voltage: {transition_voltage:.4f}V")

            # Filter data for the specified cycle
            cycle_df = df[df[COL_CYCLE] == int(cycle)].copy()

            # Initialize result dictionary
            result = {}

            # Process charge data
            charge_data = cycle_df[cycle_df[COL_STATUS] == STATUS_CC_CHARGE].copy()
            if not charge_data.empty:
                # Sort by voltage to ensure proper calculation
                charge_data = charge_data.sort_values(COL_VOLTAGE, ascending=True)

                # Get initial and final capacity values
                initial_capacity = charge_data[COL_CHARGE_CAPACITY].iloc[0]
                final_capacity = charge_data[COL_CHARGE_CAPACITY].iloc[-1]

                # Find the nearest point to transition voltage
                transition_idx = (charge_data[COL_VOLTAGE] - charge_transition).abs().idxmin()
                transition_capacity = charge_data.loc[transition_idx, COL_CHARGE_CAPACITY]

                # Calculate plateau capacities
                first_plateau = (transition_capacity - initial_capacity) / mass
                second_plateau = (final_capacity - transition_capacity) / mass

                # Add to results
                result["Charge 1st Plateau (mAh/g)"] = round(first_plateau, 4)
                result["Charge 2nd Plateau (mAh/g)"] = round(second_plateau, 4)
                result["Charge Total (mAh/g)"] = round((final_capacity - initial_capacity) / mass, 4)
                result["Charge Transition Voltage (V)"] = round(charge_transition, 4)

            # Process discharge data
            discharge_data = cycle_df[cycle_df[COL_STATUS] == STATUS_CC_DISCHARGE].copy()
            if not discharge_data.empty:
                # Sort by voltage to ensure proper calculation
                discharge_data = discharge_data.sort_values(COL_VOLTAGE, ascending=False)

                # Get initial and final capacity values
                initial_capacity = discharge_data[COL_DISCHARGE_CAPACITY].iloc[0]
                final_capacity = discharge_data[COL_DISCHARGE_CAPACITY].iloc[-1]

                # Find the nearest point to transition voltage
                transition_idx = (discharge_data[COL_VOLTAGE] - discharge_transition).abs().idxmin()
                transition_capacity = discharge_data.loc[transition_idx, COL_DISCHARGE_CAPACITY]

                # Calculate plateau capacities
                first_plateau = (transition_capacity - initial_capacity) / mass
                second_plateau = (final_capacity - transition_capacity) / mass

                # Add to results
                result["Discharge 1st Plateau (mAh/g)"] = round(first_plateau, 4)
                result["Discharge 2nd Plateau (mAh/g)"] = round(second_plateau, 4)
                result["Discharge Total (mAh/g)"] = round((final_capacity - initial_capacity) / mass, 4)
                result["Discharge Transition Voltage (V)"] = round(discharge_transition, 4)

            logging.debug("FEATURES.extract_plateaus finished")
            return result


        except Exception as e:

            logging.debug(f"FEATURES.extract_plateaus finished with error. Error calculating plateau capacities: {e}")

            return {
                "Charge 1st Plateau (mAh/g)": np.nan,
                "Charge 2nd Plateau (mAh/g)": np.nan,
                "Charge Total (mAh/g)": np.nan,
                "Discharge 1st Plateau (mAh/g)": np.nan,
                "Discharge 2nd Plateau (mAh/g)": np.nan,
                "Discharge Total (mAh/g)": np.nan
            }

    @staticmethod
    def _calculate_crate_for_cycle(df, cycle, active_mass_g):
        """
        Calculate C-rate for a specific cycle using current and active mass.

        Args:
            df: DataFrame with battery data
            cycle: Cycle number to calculate C-rate for
            active_mass_g: Active mass in grams

        Returns:
            Float representing C-rate, or None if calculation fails
        """
        if active_mass_g is None or active_mass_g <= 0:
            return None

        SPECIFIC_CAPACITY = 150  # mAh/g - hardcoded for cathode material

        try:
            charge_data = df[(df[COL_CYCLE] == cycle) & (df[COL_STATUS] == STATUS_CC_CHARGE)]
            if not charge_data.empty:
                charge_current = abs(charge_data[COL_CURRENT].mean())
                nominal_capacity = active_mass_g * SPECIFIC_CAPACITY
                c_rate = charge_current / nominal_capacity if nominal_capacity > 0 else None

                # Round to nearest standard C-rate if within 15% tolerance
                standard_rates = [0.1, 0.2, 0.33, 0.5, 1, 2, 3, 5, 10]
                if c_rate is not None:
                    nearest = min(standard_rates, key=lambda x: abs(x - c_rate))
                    if abs(c_rate - nearest) / nearest <= 0.15:
                        return nearest

                return c_rate

            return None

        except Exception as e:
            logging.debug(f"DQDVAnalysis: Error calculating C-rate for cycle {cycle}: {e}")
            return None

    def extract_plateaus_batch(self,
                               data_loader,
                               db,
                               file_list,
                               selected_cycles=None,
                               charge_voltage_range=None,
                               discharge_voltage_range=None,
                               c_rates=None):
        """
        Extract plateau capacity statistics from DataLoader cache for multiple files and cycles.

        Args:
            data_loader: DataLoader instance containing cached NDAX data
            db: CellDatabase instance for mass lookup
            file_list: List of file paths to process
            selected_cycles: List of cycles to extract plateaus for (default: [1, 2, 3])
            charge_voltage_range: Tuple with min and max voltage for charge inflection point detection
                If None, will be resolved from c_rate
            discharge_voltage_range: Tuple with min and max voltage for discharge inflection point detection
                If None, will be resolved from c_rate
            c_rates: Optional dict mapping filename to per-cycle C-rates
                {filename: {cycle: c_rate}} or legacy {filename: c_rate}
                If None, C-rate will be calculated per cycle internally

        Returns:
            List of dictionaries with plateau capacity statistics for GUI display
        """
        logging.debug("DQDVAnalysis.extract_plateaus_batch started")

        # Use default cycles if none provided
        if selected_cycles is None:
            selected_cycles = [1, 2, 3]

        stats = []

        for file_path in file_list:
            # Skip files that failed to load
            if not data_loader.is_loaded(file_path):
                logging.debug(f"File {os.path.basename(file_path)} not loaded, skipping plateau extraction")
                continue

            filename_stem = Path(file_path).stem
            df = data_loader.get_data(file_path)

            if df is None:
                logging.debug(f"No data available for {filename_stem}")
                continue

            # Get cell ID and mass: prefer NDAX metadata (already in memory), fall back to database
            cell_ID = extract_cell_id(filename_stem)
            ndax_mass = df.attrs.get('active_mass')
            if ndax_mass is not None and ndax_mass > 0:
                mass = ndax_mass
                logging.debug(f"Using active mass from NDAX metadata for {cell_ID}: {mass}g")
            else:
                mass = db.get_mass(cell_ID)
                if mass is not None and mass > 0:
                    logging.debug(f"Using active mass from database for {cell_ID}: {mass}g")
                else:
                    logging.warning(f"No mass found for cell ID {cell_ID}, using 1.0g for plateau extraction")
                    mass = 1.0

            # Extract plateaus for each selected cycle
            for cycle in selected_cycles:
                # Skip if cycle doesn't exist in this file
                if cycle not in df['Cycle'].unique():
                    logging.debug(f"Cycle {cycle} not found in file {filename_stem}, skipping plateau extraction")
                    continue

                try:
                    # Calculate C-rate for this specific cycle
                    cycle_c_rate = self._calculate_crate_for_cycle(df, cycle, mass)
                    logging.debug(f"extract_plateaus_batch: Calculated c_rate={cycle_c_rate} for {filename_stem}, cycle {cycle}")

                    # Extract plateau capacities with per-cycle C-rate
                    plateau_data = self.extract_plateaus(df, cycle, mass,
                                                         charge_voltage_range=charge_voltage_range,
                                                         discharge_voltage_range=discharge_voltage_range,
                                                         c_rate=cycle_c_rate)

                    if plateau_data:
                        # Add file and cycle information
                        plateau_data["File"] = cell_ID
                        plateau_data["Cycle"] = cycle

                        # Add to statistics
                        stats.append(plateau_data)
                except Exception as e:
                    logging.debug(f"Error extracting plateau data for {filename_stem}, cycle {cycle}: {e}")

        logging.debug("DQDVAnalysis.extract_plateaus_batch finished")
        return stats

    def find_transition_voltage(self, df,
                                cycle,
                                voltage_range=(2.5, 3.5)):
        """
        Find transition voltage where dQ/dV is flattest (closest to zero).

        Args:
            df: DataFrame with battery data
            cycle: Cycle number to analyze
            voltage_range: Tuple with min and max voltage for analysis range

        Returns:
            Dictionary with charge and discharge transition voltages
        """

        # Get already processed dQ/dV data
        dqdv_data = self.extract_dqdv(df, cycle)
        if not dqdv_data:
            return None

        result = {}

        # Process charge data
        if 'charge' in dqdv_data and dqdv_data['charge']:
            charge_data = dqdv_data['charge']
            # Filter to voltage range
            mask = (charge_data['voltage'] >= voltage_range[0]) & (charge_data['voltage'] <= voltage_range[1])
            if np.any(mask):
                filtered_voltage = charge_data['voltage'][mask]
                filtered_dqdv = charge_data['smoothed_dqdv'][mask]
                # Find where absolute value of dQ/dV is minimum (flattest point)
                flattest_idx = np.argmin(np.abs(filtered_dqdv))
                result['charge_transition_voltage'] = float(filtered_voltage[flattest_idx])

        # Process discharge data
        if 'discharge' in dqdv_data and dqdv_data['discharge']:
            discharge_data = dqdv_data['discharge']
            # Filter to voltage range
            mask = (discharge_data['voltage'] >= voltage_range[0]) & (discharge_data['voltage'] <= voltage_range[1])
            if np.any(mask):
                filtered_voltage = discharge_data['voltage'][mask]
                filtered_dqdv = discharge_data['smoothed_dqdv'][mask]
                # Find where absolute value of dQ/dV is minimum (flattest point)
                flattest_idx = np.argmin(np.abs(filtered_dqdv))
                result['discharge_transition_voltage'] = float(filtered_voltage[flattest_idx])

        return result

    def find_inflection_point(self,
                              df,
                              cycle,
                              charge_voltage_range=(2.5, 3.5),
                              discharge_voltage_range=(2.5, 3.5)):
        """
        Find inflection point using dV/dQ gradient analysis with peak detection.
        Uses capacity constraints (35-65% of total capacity) followed by voltage range filtering.

        Args:
            df: DataFrame with battery data
            cycle: Cycle number to analyze
            charge_voltage_range: Tuple with min and max voltage for charge analysis range
            discharge_voltage_range: Tuple with min and max voltage for discharge analysis range

        Returns:
            Dictionary with charge and discharge inflection voltages
        """
        logging.debug(
            f"DQDVAnalysis.find_inflection_point started with charge_range: {charge_voltage_range}, discharge_range: {discharge_voltage_range}")

        # Filter data for the specified cycle
        cycle_df = df[df[COL_CYCLE] == int(cycle)].copy()

        if cycle_df.empty:
            logging.debug(f"No data found for cycle {cycle}")
            return None

        result = {}

        # Process charge and discharge separately with their respective voltage ranges
        processing_params = [
            (STATUS_CC_CHARGE, COL_CHARGE_CAPACITY, charge_voltage_range, 'charge'),
            (STATUS_CC_DISCHARGE, COL_DISCHARGE_CAPACITY, discharge_voltage_range, 'discharge')
        ]

        for status, capacity_col, voltage_range, key_prefix in processing_params:
            seg_data = cycle_df[cycle_df[COL_STATUS] == status].copy()

            if len(seg_data) < 10:
                logging.debug(f"Insufficient data for {status} in cycle {cycle}")
                continue

            # Sort data appropriately
            if status == STATUS_CC_CHARGE:
                seg_data = seg_data.sort_values(COL_VOLTAGE, ascending=True)
            else:
                seg_data = seg_data.sort_values(COL_VOLTAGE, ascending=False)

            # Get voltage and capacity arrays
            volt = seg_data[COL_VOLTAGE].values
            cap = seg_data[capacity_col].values

            # STEP 1: Apply capacity constraint (35-65% of total capacity change)
            total_capacity_change = cap[-1] - cap[0]
            capacity_35_percent = cap[0] + 0.35 * total_capacity_change
            capacity_65_percent = cap[0] + 0.65 * total_capacity_change

            # Create capacity mask
            if status == STATUS_CC_CHARGE:
                # For charge, capacity increases
                capacity_mask = (cap >= capacity_35_percent) & (cap <= capacity_65_percent)
            else:
                # For discharge, capacity increases but we want the middle region
                capacity_mask = (cap >= capacity_35_percent) & (cap <= capacity_65_percent)

            capacity_indices = np.where(capacity_mask)[0]

            if len(capacity_indices) < 5:
                logging.debug(f"Insufficient data after capacity constraint for {status}, using fallback voltage 3.2V")
                result[f'{key_prefix}_inflection_voltage'] = 3.2
                continue

            # Apply capacity constraint to data
            cap_constrained = cap[capacity_indices]
            volt_constrained = volt[capacity_indices]

            # Calculate dV/dQ derivative on capacity-constrained data
            dV_dQ = np.gradient(volt_constrained, cap_constrained)

            # Apply smoothing with 15-point moving average
            smoothing_window = min(15, len(dV_dQ))
            if smoothing_window >= 3:
                dV_dQ_smooth = np.convolve(dV_dQ, np.ones(smoothing_window) / smoothing_window, mode='same')
            else:
                dV_dQ_smooth = dV_dQ

            # STEP 2: Apply voltage range filter within capacity-constrained data
            voltage_mask = (volt_constrained >= voltage_range[0]) & (volt_constrained <= voltage_range[1])
            valid_indices = np.where(voltage_mask)[0]

            if len(valid_indices) < 5:
                logging.debug(f"Insufficient data after voltage constraint for {status}, using fallback voltage 3.2V")
                result[f'{key_prefix}_inflection_voltage'] = 3.2
                continue

            # Extract data in both capacity and voltage ranges
            sub_dv = dV_dQ_smooth[valid_indices]
            sub_cap = cap_constrained[valid_indices]
            sub_volt = volt_constrained[valid_indices]

            # Exclude edges (5% from each end) of the final filtered data
            min_idx = max(0, int(len(sub_dv) * 0.05))
            max_idx = min(len(sub_dv), int(len(sub_dv) * 0.95))

            if max_idx <= min_idx + 2:
                logging.debug(f"Insufficient data after edge exclusion for {status}, using fallback voltage 3.2V")
                result[f'{key_prefix}_inflection_voltage'] = 3.2
                continue

            # Find peaks in derivative
            try:
                if status == STATUS_CC_CHARGE:
                    # For charge, find positive peaks in dV/dQ
                    peaks, _ = find_peaks(sub_dv[min_idx:max_idx])
                else:
                    # For discharge, find negative peaks (invert signal)
                    peaks, _ = find_peaks(-sub_dv[min_idx:max_idx])

                if len(peaks) > 0:
                    # Adjust peak indices to original array
                    peaks += min_idx

                    # Select the peak with maximum absolute derivative value
                    best_peak_idx = peaks[np.argmax(np.abs(sub_dv[peaks]))]

                    # Get inflection point values
                    inflection_voltage = sub_volt[best_peak_idx]
                    inflection_capacity = sub_cap[best_peak_idx]

                    # Store result
                    result[f'{key_prefix}_inflection_voltage'] = float(inflection_voltage)
                    result[f'{key_prefix}_inflection_capacity'] = float(inflection_capacity)

                    logging.debug(
                        f"Found {status} inflection at {inflection_voltage:.3f}V, {inflection_capacity:.3f}mAh using capacity constraint (35-65%) + voltage range {voltage_range}")
                else:
                    logging.debug(f"No peaks found for {status} in cycle {cycle}, using fallback voltage 3.2V")
                    result[f'{key_prefix}_inflection_voltage'] = 3.2

            except Exception as e:
                logging.debug(f"Error in peak detection for {status}: {e}, using fallback voltage 3.2V")
                result[f'{key_prefix}_inflection_voltage'] = 3.2
                continue

        logging.debug("DQDVAnalysis.find_inflection_point finished")
        return result if result else None