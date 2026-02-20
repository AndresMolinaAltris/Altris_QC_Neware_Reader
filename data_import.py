from common.imports import re, logging


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
    logging.debug("DATA_IMPORT.extracting_cell_id func started")
    try:
        # First attempt: Extract digits before '_'
        match = re.match(r"^(\d+)[_]", filename)
        if not match:
            # Second attempt: Extract digits before '-'
            match = re.match(r"^(\d+)[-]", filename)
        return match.group(1) if match else None
    except Exception as e:
        print(f"Error processing filename '{filename}': {e}")

        logging.debug("DATA_IMPORT.extracting_cell_id func finished")
        return None

def extract_sample_name(filename):
    # Split on first occurrence of '_' or '-'
    parts = re.split(r'[_-]', filename, maxsplit=2)

    # Ensure there is a second group to return
    return parts[1] if len(parts) > 1 else None
