# cell_database.py
import pandas as pd


class CellDatabase:
    _instance = None

    def __init__(self):
        self.mass_data = {}
        self._is_loaded = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = CellDatabase()
        return cls._instance

    def load_database(self, excel_path):
        """Load and cache the entire cell database at once"""
        if self._is_loaded:
            return

        print("Loading cell database...")
        with pd.ExcelFile(excel_path) as xls:
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(
                    xls,
                    sheet_name=sheet_name,
                    dtype={'Name/ID': str}
                )

                # Clean column names
                df.columns = df.columns.str.strip()

                if 'Name/ID' in df.columns and 'Active mass (mg)' in df.columns:
                    for _, row in df.iterrows():
                        cell_id = str(row['Name/ID']).strip()
                        try:
                            mass_value = row['Active mass (mg)']
                            if isinstance(mass_value, str):
                                mass_value = mass_value.replace(',', '.')
                            mass_value = round(float(mass_value) / 1000, 5)  # Convert mg to g
                            self.mass_data[cell_id] = mass_value
                        except (ValueError, AttributeError):
                            continue

        self._is_loaded = True
        print(f"Database loaded with {len(self.mass_data)} entries")

    def get_mass(self, cell_id):
        """Quick lookup of cell mass from cache"""
        if not self._is_loaded:
            raise RuntimeError("Database not loaded. Call load_database() first.")
        return self.mass_data.get(str(cell_id).strip())

    def clear_cache(self):
        """Clear the cached data"""
        self.mass_data = {}
        self._is_loaded = False


# Convenience function for finding active mass
def find_active_mass(file_path, search_id):
    """Backward compatibility function"""
    db = CellDatabase.get_instance()
    if not db._is_loaded:
        db.load_database(file_path)
    return db.get_mass(search_id)