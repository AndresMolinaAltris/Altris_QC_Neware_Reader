from common.imports import np, pd

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
            (self.extract_internal_resistance_soc_0, (df, features, cycle))
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
