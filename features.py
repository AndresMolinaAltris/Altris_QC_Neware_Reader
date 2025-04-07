import logging

from common.imports import np, pd
from scipy.signal import savgol_filter

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

    def extract_internal_resistance_soc_100(self, df, features, cycle):
        """
        Extracts internal resistance at SOC = 100% from the dataset.

        :param df: pandas DataFrame containing experimental data.
        :param features: Dictionary to store extracted features.
        :param cycle: Integer representing the cycle number.
        """
        try:
            idx = (df["Status"] == "Rest") & (df["Cycle"] == int(cycle)) & (df["Step"] == 3)
            index = df[idx].index[-1]
            ocv = round(df["Voltage"][index], 4)
            ocv_dV = round(df["Voltage"][index + 1], 4)
            delta_current = abs(df["Current(mA)"][index + 1] - df["Current(mA)"][index])
            delta_V = abs(ocv_dV - ocv)
            internal_resistance = delta_V / (delta_current / 1000)
            features["Internal Resistance at SOC 100 (Ohms)"] = round(internal_resistance, 4)
        except Exception:
            features["Internal Resistance at SOC 100 (Ohms)"] = np.nan

    def extract_internal_resistance_soc_0(self, df, features, cycle):
        """
        Extracts internal resistance at SOC = 0% from the dataset.

        :param df: pandas DataFrame containing experimental data.
        :param features: Dictionary to store extracted features.
        :param cycle: Integer representing the cycle number.
        """
        try:
            #idx = (df["Status"] == "Rest") & (df["Cycle"] == int(cycle)) & (df["Step"] == 5)
            idx = (df["Status"] == "Rest") & (df["Cycle"] == int(cycle)) & (df["Step"] == 1)
            index = df[idx].index[-1]
            ocv = round(df["Voltage"][index], 4)
            ocv_dV = round(df["Voltage"][index + 1], 4)
            delta_current = abs(df["Current(mA)"][index + 1] - df["Current(mA)"][index])
            delta_V = abs(ocv_dV - ocv)
            internal_resistance = delta_V / (delta_current / 1000)
            features["Internal Resistance at SOC 0 (Ohms)"] = round(internal_resistance, 4)
        except Exception:
            features["Internal Resistance at SOC 0 (Ohms)"] = np.nan

    def extract_charge_capacity(self, df, features, cycle, mass=1.0):
        """
        Extracts charge capacity and specific charge capacity.

        :param df: pandas DataFrame containing experimental data.
        :param features: Dictionary to store extracted features.
        :param cycle: Integer representing the cycle number.
        :param mass: Float representing the mass of active material (default: 1.0 g).
        """
        try:
            idx = np.logical_and(df["Status"] == "CC_Chg", df["Cycle"] == int(cycle))
            initial_charge_capacity = df[idx]["Charge_Capacity(mAh)"].max()
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
            idx = np.logical_and(df["Status"] == "CC_DChg", df["Cycle"] == int(cycle))
            initial_discharge_capacity = df[idx]["Discharge_Capacity(mAh)"].max()
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
            cycle_df = df[df["Cycle"] == int(cycle)].copy()

            # Define a minimum number of points required for proper calculation
            if len(cycle_df) < 10:
                return None

            # Separate charge and discharge data
            charge_data = cycle_df[cycle_df["Status"] == "CC_Chg"].copy()
            discharge_data = cycle_df[cycle_df["Status"] == "CC_DChg"].copy()

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

    def _calculate_dqdv(self, data, direction, mass=1.0, smoothing_method='sma', window_length=15, weights=None,
                        pre_smooth=True):

        """
        Helper method to calculate dQ/dV for either charge or discharge data.

        Args:
            data: DataFrame containing either charge or discharge data
            direction: String indicating 'charge' or 'discharge'
            mass: Active material mass in g

        Returns:
            Dictionary with voltage, dQ/dV data and smoothed dQ/dV data
        """
        if data.empty or len(data) < 10:
            return None

        # Sort by voltage to ensure proper calculation
        if direction == 'charge':
            data = data.sort_values('Voltage', ascending=True)
            capacity_col = 'Charge_Capacity(mAh)'
        else:
            data = data.sort_values('Voltage', ascending=False)
            capacity_col = 'Discharge_Capacity(mAh)'

        # Drop duplicates to reduce noise
        data = data.drop_duplicates(subset=['Voltage'])
        data = data.reset_index(drop=True)

        # Get voltage and capacity data
        voltage = data['Voltage'].values
        capacity = data[capacity_col].values

        # Here we will add a pre-smoothing step
        # Apply pre-smoothing to capacity data before differentiation if enabled
        if pre_smooth:
            # Use a smaller window for pre-smoothing to preserve peak shapes
            pre_smooth_window = min(window_length, max(5, len(capacity) // 10))

            if smoothing_method == 'savgol':
                # Make sure window length is odd for Savitzky-Golay
                if pre_smooth_window % 2 == 0:
                    pre_smooth_window += 1

                # Use a lower polynomial order (2) for capacity smoothing
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

        # Apply Savitzky-Golay filter for smoothing (from DiffCapAnalyzer)
        # smoothed_dqdv = self._apply_savgol_filter(specific_dqdv)

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

    def extract_plateaus(self, df, cycle, mass=1.0, transition_voltage=None):
        """
        Extracts the capacities for the 1st and 2nd plateaus during charge and discharge.

        First plateau is defined as: Capacity from initial voltage to transition voltage
        Second plateau is defined as: Capacity from transition voltage to final voltage

        Args:
            df: pandas DataFrame containing experimental data
            cycle: Integer representing the cycle number to extract data from
            mass: Float representing the mass of active material (default: 1.0 g)
            transition_voltage: Optional float to specify the transition voltage
                If None, will either calculate it or use the default value of 3.2V

        Returns:
            Dictionary containing plateau capacities for both charge and discharge
        """
        try:
            # Define default transition voltage
            default_transition_voltage = 3.2  # V

            # If transition_voltage is not provided, try to calculate it
            if transition_voltage is None:
                # Try to calculate the transition voltage
                transition_result = self.find_transition_voltage(df, cycle)

                if transition_result:
                    # For charge, use the charge transition voltage if available
                    charge_transition = transition_result.get('charge_transition_voltage')
                    discharge_transition = transition_result.get('discharge_transition_voltage')

                    # Log which values we're using
                    if charge_transition:
                        logging.debug(f"Using calculated charge transition voltage: {charge_transition:.4f}V")
                    else:
                        logging.debug(
                            f"No calculated charge transition voltage, using default: {default_transition_voltage}V")

                    if discharge_transition:
                        logging.debug(f"Using calculated discharge transition voltage: {discharge_transition:.4f}V")
                    else:
                        logging.debug(
                            f"No calculated discharge transition voltage, using default: {default_transition_voltage}V")
                else:
                    # If calculation failed, use default
                    charge_transition = default_transition_voltage
                    discharge_transition = default_transition_voltage
                    logging.debug(
                        f"Failed to calculate transition voltages, using default: {default_transition_voltage}V")
            else:
                # Use the provided transition voltage for both charge and discharge
                charge_transition = transition_voltage
                discharge_transition = transition_voltage
                logging.debug(f"Using provided transition voltage: {transition_voltage:.4f}V")

            # Filter data for the specified cycle
            cycle_df = df[df["Cycle"] == int(cycle)].copy()

            # Initialize result dictionary
            result = {}

            # Process charge data
            charge_data = cycle_df[cycle_df["Status"] == "CC_Chg"].copy()
            if not charge_data.empty:
                # Sort by voltage to ensure proper calculation
                charge_data = charge_data.sort_values('Voltage', ascending=True)

                # Get initial and final capacity values
                initial_capacity = charge_data["Charge_Capacity(mAh)"].iloc[0]
                final_capacity = charge_data["Charge_Capacity(mAh)"].iloc[-1]

                # Find the nearest point to transition voltage
                transition_idx = (charge_data['Voltage'] - charge_transition).abs().idxmin()
                transition_capacity = charge_data.loc[transition_idx, "Charge_Capacity(mAh)"]

                # Calculate plateau capacities
                first_plateau = (transition_capacity - initial_capacity) / mass
                second_plateau = (final_capacity - transition_capacity) / mass

                # Add to results
                result["Charge 1st Plateau (mAh/g)"] = round(first_plateau, 4)
                result["Charge 2nd Plateau (mAh/g)"] = round(second_plateau, 4)
                result["Charge Total (mAh/g)"] = round((final_capacity - initial_capacity) / mass, 4)
                result["Charge Transition Voltage (V)"] = round(charge_transition, 4)

            # Process discharge data
            discharge_data = cycle_df[cycle_df["Status"] == "CC_DChg"].copy()
            if not discharge_data.empty:
                # Sort by voltage to ensure proper calculation
                discharge_data = discharge_data.sort_values('Voltage', ascending=False)

                # Get initial and final capacity values
                initial_capacity = discharge_data["Discharge_Capacity(mAh)"].iloc[0]
                final_capacity = discharge_data["Discharge_Capacity(mAh)"].iloc[-1]

                # Find the nearest point to transition voltage
                transition_idx = (discharge_data['Voltage'] - discharge_transition).abs().idxmin()
                transition_capacity = discharge_data.loc[transition_idx, "Discharge_Capacity(mAh)"]

                # Calculate plateau capacities
                first_plateau = (transition_capacity - initial_capacity) / mass
                second_plateau = (final_capacity - transition_capacity) / mass

                # Add to results
                result["Discharge 1st Plateau (mAh/g)"] = round(first_plateau, 4)
                result["Discharge 2nd Plateau (mAh/g)"] = round(second_plateau, 4)
                result["Discharge Total (mAh/g)"] = round((final_capacity - initial_capacity) / mass, 4)
                result["Discharge Transition Voltage (V)"] = round(discharge_transition, 4)

            return result

        except Exception as e:
            logging.debug(f"Error calculating plateau capacities: {e}")
            return {
                "Charge 1st Plateau (mAh/g)": np.nan,
                "Charge 2nd Plateau (mAh/g)": np.nan,
                "Charge Total (mAh/g)": np.nan,
                "Discharge 1st Plateau (mAh/g)": np.nan,
                "Discharge 2nd Plateau (mAh/g)": np.nan,
                "Discharge Total (mAh/g)": np.nan
            }

    def find_transition_voltage(self, df, cycle, voltage_range=(3.15, 3.3)):
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
