import pandas as pd
import os
import pickle
import time
import hashlib


class CellDatabase:
    _instance = None

    def __init__(self):
        self.mass_data = {}
        self._is_loaded = False
        self._cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")

        # Create cache directory if it doesn't exist
        if not os.path.exists(self._cache_dir):
            os.makedirs(self._cache_dir)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = CellDatabase()
        return cls._instance

    def _get_cache_path(self, excel_path):
        """Generate a unique cache file path based on the Excel file path and modification time"""
        excel_stats = os.stat(excel_path)
        mod_time = excel_stats.st_mtime
        file_size = excel_stats.st_size

        # Create a hash based on file path, size and modification time
        unique_id = f"{excel_path}_{file_size}_{mod_time}"
        hash_id = hashlib.md5(unique_id.encode()).hexdigest()

        return os.path.join(self._cache_dir, f"cell_db_cache_{hash_id}.pkl")

    def load_database(self, excel_path, force_reload=False):
        """Load and cache the entire cell database at once"""
        if self._is_loaded and not force_reload:
            return

        cache_path = self._get_cache_path(excel_path)

        # Try to load from cache first if not forcing reload
        if os.path.exists(cache_path) and not force_reload:
            try:
                start_time = time.time()
                print("Loading cell database from cache...")
                with open(cache_path, 'rb') as f:
                    self.mass_data = pickle.load(f)

                self._is_loaded = True
                elapsed = time.time() - start_time
                print(f"Database loaded from cache with {len(self.mass_data)} entries in {elapsed:.2f} seconds")
                return
            except Exception as e:
                print(f"Error loading cache: {e}. Loading from Excel file instead.")

        # If no cache or cache loading failed, load from Excel
        print("Loading cell database from Excel (this may take a while)...")
        start_time = time.time()

        # Use pandas ExcelFile for better performance
        with pd.ExcelFile(excel_path) as xls:
            # Process each sheet that has the required columns
            for sheet_name in xls.sheet_names:
                # First check headers to avoid loading unnecessary data
                df_header = pd.read_excel(xls, sheet_name=sheet_name, nrows=0)
                clean_headers = {col.strip(): col for col in df_header.columns}

                # Skip sheets without required columns
                if 'Name/ID' not in clean_headers and 'Active mass (mg)' not in clean_headers:
                    continue

                # Get actual column names from file (handling case sensitivity and whitespace)
                name_col = clean_headers.get('Name/ID') or next((col for col in clean_headers.keys()
                                                                 if col.lower() == 'name/id'), None)
                mass_col = clean_headers.get('Active mass (mg)') or next((col for col in clean_headers.keys()
                                                                          if col.lower() == 'active mass (mg)'), None)

                if not name_col or not mass_col:
                    continue

                # Read only needed columns for better performance
                col_indices = [df_header.columns.get_loc(name_col), df_header.columns.get_loc(mass_col)]

                # Read the sheet in one go since chunksize isn't supported in read_excel
                df = pd.read_excel(
                    xls,
                    sheet_name=sheet_name,
                    usecols=col_indices,
                    dtype={name_col: str}
                )

                # Rename columns for consistency
                df.columns = [col.strip() for col in df.columns]
                df = df.rename(columns={name_col: 'Name/ID', mass_col: 'Active mass (mg)'})

                # Process rows in batches for better memory management
                batch_size = 1000
                total_rows = len(df)

                for start_idx in range(0, total_rows, batch_size):
                    end_idx = min(start_idx + batch_size, total_rows)
                    batch = df.iloc[start_idx:end_idx]

                    for _, row in batch.iterrows():
                        cell_id = str(row['Name/ID']).strip()
                        if not cell_id:
                            continue

                        try:
                            mass_value = row['Active mass (mg)']
                            if isinstance(mass_value, str):
                                mass_value = mass_value.replace(',', '.')
                            mass_value = round(float(mass_value) / 1000, 5)  # Convert mg to g
                            self.mass_data[cell_id] = mass_value
                        except (ValueError, AttributeError):
                            continue

        self._is_loaded = True
        elapsed = time.time() - start_time
        print(f"Database loaded with {len(self.mass_data)} entries in {elapsed:.2f} seconds")

        # Save to cache for future use
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(self.mass_data, f, protocol=pickle.HIGHEST_PROTOCOL)
            print(f"Database cache saved to {cache_path}")
        except Exception as e:
            print(f"Warning: Could not save database cache: {e}")

    def get_mass(self, cell_id):
        """Quick lookup of cell mass from cache"""
        if not self._is_loaded:
            raise RuntimeError("Database not loaded. Call load_database() first.")

        # Try to find with exact match first
        cell_id_str = str(cell_id).strip()
        mass = self.mass_data.get(cell_id_str)

        # If not found, try case-insensitive search
        if mass is None:
            cell_id_lower = cell_id_str.lower()
            for key, value in self.mass_data.items():
                if str(key).lower() == cell_id_lower:
                    return value

        return mass

    def clear_cache(self):
        """Clear the cached data"""
        self.mass_data = {}
        self._is_loaded = False

    def rebuild_cache(self, excel_path):
        """Force rebuild the cache from the Excel file"""
        self.clear_cache()
        self.load_database(excel_path, force_reload=True)


# Convenience function for finding active mass
def find_active_mass(file_path, search_id):
    """Backward compatibility function"""
    db = CellDatabase.get_instance()
    if not db._is_loaded:
        db.load_database(file_path)
    return db.get_mass(search_id)