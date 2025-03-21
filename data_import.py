import re
import NewareNDA
import logging
from io import StringIO
import pandas as pd
import os


def extract_active_mass(file_path):
    """
    Extracts the active mass value from a Neware NDA file.

    The function assumes the mass in the original file is in mg

    This function reads the given `.ndax` file using `NewareNDA.read()`, captures
    the logging output, and searches for the "Active mass" value using a regular expression.
    If extraction fails, an error message is printed instead of crashing.

    Args:
        file_path (str): The full path to the `.ndax` file.

    Returns:
        float or None: The extracted active mass in g if found, otherwise None.

    Example:
        >>> extract_active_mass("C:\\path\\to\\file.ndax")
        23.826
    """

    try:
        # Clear previous logging handlers to ensure fresh log capture
        logger = logging.getLogger()
        for handler in logger.handlers[:]:  # Remove all existing handlers
            logger.removeHandler(handler)

        # Setup logging capture
        log_stream = StringIO()
        logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler(log_stream)])

        # Read file (this triggers logging)
        NewareNDA.read(file_path)

        # Extract log contents
        log_contents = log_stream.getvalue()

        # Regex to find active mass
        match = re.search(r"Active mass:\s*([\d.]+)\s*mg", log_contents)

        if match:
            return float(match.group(1))/1000  # Return active mass as a float

        # If no match found, raise an exception
        # If no match is found, return 1
        return 1


    except Exception as e:

        print(f"[ERROR] Failed to extract active mass from {file_path}: {e}")

        return 1  # Return 1 in case of an error


def extract_cell_id(filename):
    """
        Extracts the cell ID from a filename. It assumes the cell ID are the digits before the first
        underscore '_'. If it doesn't find an underscore, it then tries to extract the cell ID before
        the first hyphen '-'

        Args:
            filename (str): The filename string to process. It cannot be a path.

        Returns:
            str or None: The extracted cell ID as a string if found, otherwise None.

        """
    try:
        # First attempt: Extract digits before '_'
        match = re.match(r"^(\d+)[_]", filename)
        if not match:
            # Second attempt: Extract digits before '-'
            match = re.match(r"^(\d+)[-]", filename)
        return match.group(1) if match else None
    except Exception as e:
        print(f"Error processing filename '{filename}': {e}")
        return None


def extract_sample_name(filename):
    # Split on first occurrence of '_' or '-'
    parts = re.split(r'[_-]', filename, maxsplit=2)

    # Ensure there is a second group to return
    return parts[1] if len(parts) > 1 else None


def find_active_mass(file_path, search_id):
    search_id_str = str(search_id).strip()
    required_cols = ['Name/ID', 'Active mass (mg)']

    with pd.ExcelFile(file_path) as xls:
        for sheet_name in xls.sheet_names:
            # First, read only the column names to check if required columns exist
            df_header = pd.read_excel(xls, sheet_name=sheet_name, nrows=0)
            clean_cols = [col.strip() for col in df_header.columns]

            # Skip sheets that don't have required columns
            if not all(col in clean_cols for col in required_cols):
                continue

            # Get column indices for required columns
            col_indices = [clean_cols.index(col) for col in required_cols]

            # Read only required columns using usecols
            df = pd.read_excel(
                xls,
                sheet_name=sheet_name,
                usecols=col_indices,
                dtype={col_indices[0]: str}  # Name/ID column as string
            )

            df.columns = required_cols  # Assign clean column names

            # Find matching row without type conversion
            mask = df['Name/ID'].str.strip() == search_id_str
            match = df[mask]

            if not match.empty:
                try:
                    # Process only the matching value
                    value = match['Active mass (mg)'].iloc[0]
                    if isinstance(value, str):
                        value = value.replace(',', '.')
                    return round(float(value) / 1000, 5)
                except (ValueError, AttributeError):
                    print(f"Conversion error: {value}")
                    return None

    return None


def find_ndax_files(data_directory):
    """
    Recursively searches for .ndax files in the given directory.

    Parameters:
        data_directory (str): The path of the directory to search.

    Returns:
        list: A list of full file paths for all .ndax files found.
    """
    ndax_file_list = []
    for root, _, files in os.walk(data_directory):
        for filename in files:
            if filename.endswith(".ndax"):
                ndax_file_list.append(os.path.join(root, filename))
    return ndax_file_list