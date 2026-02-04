from common.imports import pd, os, pickle, time, hashlib


class CellDatabase:
    _instance = None

    def __init__(self):
        self.mass_data = {}         # Extract electrode mass
        self.loading_data = {}      # Extract electrode loading level
        self._lowercase_keys = {}   # Maps lowercase cell_id to actual key for fast case-insensitive lookup
        self._is_loaded = False
        self._database_path = None  # Stored for lazy loading
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

    def set_database_path(self, excel_path):
        """Store the database path for lazy loading. Does not load the database."""
        self._database_path = excel_path

    def _ensure_loaded(self):
        """Load the database if a path was set but not yet loaded."""
        if not self._is_loaded and self._database_path:
            self.load_database(self._database_path)

    def load_database(self, excel_path, force_reload=False):
        """Load and cache the entire cell database at once"""
        self._database_path = excel_path
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

                # Rebuild lowercase key mapping from loaded data
                self._lowercase_keys = {k.lower(): k for k in self.mass_data.keys()}

                self._is_loaded = True
                elapsed = time.time() - start_time
                print(f"Database loaded from cache with {len(self.mass_data)} entries in {elapsed:.2f} seconds")
                return
            except Exception as e:
                print(f"Error loading cache: {e}. Loading from Excel file instead.")

        # If no cache or cache loading failed, load from Excel
        print("Loading cell database from Excel (this may take a while)...")
        start_time = time.time()

        # Use openpyxl engine with read_only mode for better performance
        try:
            xls = pd.ExcelFile(excel_path, engine='openpyxl')
        except Exception as e:
            print(f"Error opening Excel file: {e}")
            try:
                # Fallback to default engine if openpyxl fails
                xls = pd.ExcelFile(excel_path)
            except Exception as e2:
                print(f"Error: Could not open Excel file with any engine: {e2}")
                raise RuntimeError(f"Failed to open database file '{excel_path}'. Check if the file is corrupted or in use.")

        total_entries = 0
        skipped_sheets = []
        error_summary = []

        # Process each sheet that has the required columns
        for sheet_name in xls.sheet_names:
            try:
                # First check headers to avoid loading unnecessary data
                try:
                    df_header = pd.read_excel(xls, sheet_name=sheet_name, nrows=0)
                except Exception as e:
                    skipped_sheets.append(f"{sheet_name} (header read error: {str(e)[:50]})")
                    continue

                clean_headers = {col.strip(): col for col in df_header.columns if isinstance(col, str)}

                # Skip sheets without required columns
                if 'Name/ID' not in clean_headers and 'Active mass (mg)' not in clean_headers:
                    # Check case-insensitive
                    has_name = any(col.lower() == 'name/id' for col in clean_headers.keys())
                    has_mass = any(col.lower() == 'active mass (mg)' for col in clean_headers.keys())
                    if not (has_name and has_mass):
                        continue

                # Get actual column names from file (handling case sensitivity and whitespace)
                name_col = clean_headers.get('Name/ID') or next((col for col in clean_headers.keys()
                                                                 if col.lower() == 'name/id'), None)
                mass_col = clean_headers.get('Active mass (mg)') or next((col for col in clean_headers.keys()
                                                                          if col.lower() == 'active mass (mg)'), None)

                if not name_col or not mass_col:
                    continue

                # Build list of columns to read (include loading level if present)
                cols_to_read = [name_col, mass_col]
                loading_col = next((col for col in df_header.columns if isinstance(col, str) and col.lower().strip() == 'loading level(mg/cm^2)'), None)
                if loading_col:
                    cols_to_read.append(loading_col)

                # Read the sheet - vectorized operation
                try:
                    df = pd.read_excel(
                        xls,
                        sheet_name=sheet_name,
                        usecols=cols_to_read,
                        dtype={name_col: str}
                    )
                except Exception as e:
                    skipped_sheets.append(f"{sheet_name} (data read error: {str(e)[:50]})")
                    continue

                # Standardize column names
                df.columns = [col.strip() if isinstance(col, str) else str(col) for col in df.columns]
                df = df.rename(columns={name_col: 'Name/ID', mass_col: 'Active mass (mg)'})
                if loading_col:
                    df = df.rename(columns={loading_col: 'Loading level(mg/cm^2)'})

                initial_row_count = len(df)

                # Remove rows with missing cell IDs
                df = df[df['Name/ID'].notna() & (df['Name/ID'].astype(str).str.strip() != '')]

                # Clean cell IDs: remove non-printable characters and extra whitespace
                df['Name/ID'] = df['Name/ID'].astype(str).str.replace(r'[\x00-\x1f\x7f-\x9f]', '', regex=True).str.strip()
                df = df[df['Name/ID'] != '']

                # Vectorized conversion of mass from mg to g with robust string cleaning
                mass_series = df['Active mass (mg)'].astype(str)
                # Remove common problematic characters
                mass_series = mass_series.str.replace(',', '.', regex=False)  # European decimal separator
                mass_series = mass_series.str.replace(' ', '', regex=False)   # Remove spaces
                mass_series = mass_series.str.replace('\u00a0', '', regex=False)  # Non-breaking space
                mass_series = mass_series.str.replace(r'[^\d.]', '', regex=True)  # Keep only digits and periods

                df['Active mass (mg)'] = pd.to_numeric(mass_series, errors='coerce') / 1000
                df['Active mass (mg)'] = df['Active mass (mg)'].round(5)

                # Remove rows with invalid mass values (NaN, zero, or negative)
                df = df[df['Active mass (mg)'].notna() & (df['Active mass (mg)'] > 0)]

                rows_processed = len(df)
                rows_skipped = initial_row_count - rows_processed

                if rows_skipped > 0:
                    error_summary.append(f"  {sheet_name}: {rows_skipped} rows skipped (invalid data)")

                # Convert mass data to dictionary in one operation (vectorized)
                try:
                    mass_dict = df.set_index('Name/ID')['Active mass (mg)'].to_dict()
                    self.mass_data.update(mass_dict)
                    total_entries += len(mass_dict)
                except Exception as e:
                    error_summary.append(f"  {sheet_name}: Failed to convert to dict ({str(e)[:50]})")
                    continue

                # Handle loading level if column exists
                if loading_col and 'Loading level(mg/cm^2)' in df.columns:
                    try:
                        # Clean and convert loading level data
                        loading_series = df['Loading level(mg/cm^2)'].astype(str)
                        loading_series = loading_series.str.replace(',', '.', regex=False)
                        loading_series = loading_series.str.replace(' ', '', regex=False)
                        loading_series = loading_series.str.replace('\u00a0', '', regex=False)
                        loading_series = loading_series.str.replace(r'[^\d.]', '', regex=True)
                        df['Loading level(mg/cm^2)'] = pd.to_numeric(loading_series, errors='coerce')

                        # Store tuple of (mass, loading_level) for each cell
                        loading_dict = df.set_index('Name/ID')['Loading level(mg/cm^2)'].to_dict()
                        # Update mass_data with tuples containing both mass and loading
                        for cell_id, mass in mass_dict.items():
                            loading = loading_dict.get(cell_id)
                            self.mass_data[cell_id] = (mass, loading)
                    except Exception as e:
                        # If loading level fails, keep the mass data
                        error_summary.append(f"  {sheet_name}: Loading level processing failed ({str(e)[:50]})")

            except Exception as e:
                # Catch-all for any unexpected errors in sheet processing
                skipped_sheets.append(f"{sheet_name} (unexpected error: {str(e)[:50]})")
                continue

        # Build lowercase key mapping for O(1) case-insensitive lookups
        self._lowercase_keys = {k.lower(): k for k in self.mass_data.keys()}

        self._is_loaded = True
        elapsed = time.time() - start_time
        print(f"Database loaded with {total_entries} entries in {elapsed:.2f} seconds")

        # Report any issues encountered
        if skipped_sheets:
            print(f"Warning: {len(skipped_sheets)} sheets could not be processed:")
            for sheet_info in skipped_sheets[:5]:  # Show first 5
                print(f"  - {sheet_info}")
            if len(skipped_sheets) > 5:
                print(f"  ... and {len(skipped_sheets) - 5} more")

        if error_summary:
            print("Data quality issues found:")
            for error_info in error_summary[:10]:  # Show first 10
                print(error_info)
            if len(error_summary) > 10:
                print(f"  ... and {len(error_summary) - 10} more issues")

        if total_entries == 0:
            raise RuntimeError(f"No valid data loaded from '{excel_path}'. Check that the file contains sheets with 'Name/ID' and 'Active mass (mg)' columns.")

        # Save to cache for future use
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(self.mass_data, f, protocol=pickle.HIGHEST_PROTOCOL)
            print(f"Database cache saved to {cache_path}")
        except Exception as e:
            print(f"Warning: Could not save database cache: {e}")

    def get_mass(self, cell_id):
        """Quick lookup of cell mass from cache. Lazy-loads database if path was set."""
        if not self._is_loaded:
            self._ensure_loaded()
        if not self._is_loaded:
            return None

        # Try to find with exact match first
        cell_id_str = str(cell_id).strip()
        entry = self.mass_data.get(cell_id_str)

        # If not found, try case-insensitive search using pre-built mapping (O(1))
        if entry is None:
            actual_key = self._lowercase_keys.get(cell_id_str.lower())
            if actual_key:
                entry = self.mass_data[actual_key]

        # Extract mass value (handle both tuple and scalar formats for backward compatibility)
        if isinstance(entry, tuple):
            return entry[0]  # (mass, loading)
        return entry
    
    def get_loading_level(self, cell_id):
        """
        Separate function to retrieve only the loading level (mg/cm²).
        Returns float if found, None if missing or database not loaded.
        """
        if not self._is_loaded:
            return None

        cell_id_str = str(cell_id).strip()
        entry = self.mass_data.get(cell_id_str)

        # Case-insensitive fallback using pre-built mapping (O(1))
        if entry is None:
            actual_key = self._lowercase_keys.get(cell_id_str.lower())
            if actual_key:
                entry = self.mass_data[actual_key]

        if entry is None:
            return None

        # entry is a tuple: (mass_g, loading_mg_per_cm2) or just mass_g in old files
        if isinstance(entry, tuple) and len(entry) == 2:
            return entry[1] if entry[1] is not None else None
        return None

    def clear_cache(self):
        """Clear the cached data"""
        self.mass_data = {}
        self._lowercase_keys = {}
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