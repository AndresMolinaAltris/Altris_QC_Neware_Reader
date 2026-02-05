from common.imports import pd, os, logging, Path, Dict, List, Optional
import re
from NewareNDA.NewareNDAx import read_ndax
from cell_database import CellDatabase


class DataLoader:
    """
    Centralized data loader for NDAX files with intelligent caching.

    Designed for small to medium batches (5-10 files) with cache-all approach.
    Eliminates redundant NewareNDA.read() calls across the application.
    """

    def __init__(self):
        """Initialize the data loader with empty cache."""
        self._cache: Dict[str, pd.DataFrame] = {}
        self._file_stems: Dict[str, str] = {}  # Maps full path to filename stem
        self._failed_files: List[str] = []

    def load_files(self, file_paths: List[str]) -> None:
        """
        Load multiple NDAX files into cache.

        Args:
            file_paths: List of full paths to NDAX files

        Raises:
            FileNotFoundError: If any file doesn't exist
            Exception: If NewareNDA.read() fails for any file
        """
        logging.debug(f"DATA_LOADER: Starting to load {len(file_paths)} files")

        self._failed_files.clear()

        for file_path in file_paths:
            try:
                # Validate file exists
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"File not found: {file_path}")

                # Skip if already loaded
                if file_path in self._cache:
                    logging.debug(f"DATA_LOADER: File already cached: {os.path.basename(file_path)}")
                    continue

                # Load the file
                logging.debug(f"DATA_LOADER: Loading file: {os.path.basename(file_path)}")
                df = read_ndax(file_path, software_cycle_number=True)

                # Fallback logic for active mass: use CellDatabase (lazy-loaded singleton)
                if df.attrs.get('active_mass') is None:
                    logging.debug(f"DATA_LOADER: Active mass not found in {os.path.basename(file_path)}, attempting database fallback.")
                    try:
                        filename_stem = Path(file_path).stem
                        match = re.match(r'^(\d+)_', filename_stem)
                        if match:
                            cell_id = match.group(1)
                            db = CellDatabase.get_instance()
                            mass_from_db = db.get_mass(cell_id)
                            if mass_from_db is not None:
                                df.attrs['active_mass'] = mass_from_db
                                logging.debug(f"DATA_LOADER: Fallback successful for {os.path.basename(file_path)}, mass: {mass_from_db:.4f} g")
                            else:
                                logging.warning(f"DATA_LOADER: Fallback failed for {os.path.basename(file_path)}: cell_ID {cell_id} not found in database.")
                        else:
                            logging.warning(f"DATA_LOADER: Fallback failed for {os.path.basename(file_path)}: could not extract cell_ID from filename.")
                    except Exception as e:
                        logging.error(f"DATA_LOADER: Error during active mass fallback for {os.path.basename(file_path)}: {e}")
                
                # Cache the data
                self._cache[file_path] = df

                # Cache the data
                self._cache[file_path] = df

                # Store filename stem for easier lookup
                filename_stem = Path(file_path).stem
                self._file_stems[file_path] = filename_stem

                logging.debug(f"DATA_LOADER: Successfully loaded {os.path.basename(file_path)} "
                              f"with {len(df)} rows")

            except Exception as e:
                logging.error(f"DATA_LOADER: Failed to load {file_path}: {e}")
                self._failed_files.append(file_path)
                # Continue loading other files instead of failing completely

        # Log summary
        successful_count = len(file_paths) - len(self._failed_files)
        logging.debug(f"DATA_LOADER: Loaded {successful_count}/{len(file_paths)} files successfully")

        if self._failed_files:
            logging.warning(f"DATA_LOADER: Failed to load {len(self._failed_files)} files: "
                            f"{[os.path.basename(f) for f in self._failed_files]}")

    def get_data(self, file_path: str) -> Optional[pd.DataFrame]:
        """
        Get cached data for a specific file.

        Args:
            file_path: Full path to the NDAX file

        Returns:
            DataFrame containing the file data, or None if not loaded/failed
        """
        if file_path not in self._cache:
            logging.warning(f"DATA_LOADER: File not in cache: {os.path.basename(file_path)}")
            return None

        return self._cache[file_path].copy()  # Return copy to prevent accidental modification

    def get_data_by_stem(self, filename_stem: str) -> Optional[pd.DataFrame]:
        """
        Get cached data by filename stem (without path and extension).

        Args:
            filename_stem: Filename without path and extension (e.g., "sample_001")

        Returns:
            DataFrame containing the file data, or None if not found
        """
        # Find the full path that matches this stem
        for full_path, stem in self._file_stems.items():
            if stem == filename_stem:
                return self.get_data(full_path)

        logging.warning(f"DATA_LOADER: No file found with stem: {filename_stem}")
        return None

    def is_loaded(self, file_path: str) -> bool:
        """
        Check if a file is loaded in cache.

        Args:
            file_path: Full path to the NDAX file

        Returns:
            True if file is loaded and ready, False otherwise
        """
        return file_path in self._cache

    def get_cached_files(self) -> List[str]:
        """
        Get list of all cached file paths.

        Returns:
            List of full file paths that are currently cached
        """
        return list(self._cache.keys())

    def get_cached_stems(self) -> List[str]:
        """
        Get list of all cached filename stems.

        Returns:
            List of filename stems that are currently cached
        """
        return list(self._file_stems.values())

    def get_failed_files(self) -> List[str]:
        """
        Get list of files that failed to load.

        Returns:
            List of full file paths that failed during loading
        """
        return self._failed_files.copy()

    def clear_cache(self) -> None:
        """Clear all cached data and reset the loader."""
        logging.debug(f"DATA_LOADER: Clearing cache of {len(self._cache)} files")
        self._cache.clear()
        self._file_stems.clear()
        self._failed_files.clear()

    def get_cache_info(self) -> Dict[str, int]:
        """
        Get information about the current cache state.

        Returns:
            Dictionary with cache statistics
        """
        total_rows = sum(len(df) for df in self._cache.values())

        return {
            'cached_files': len(self._cache),
            'failed_files': len(self._failed_files),
            'total_rows': total_rows,
            'memory_usage_mb': sum(df.memory_usage(deep=True).sum() for df in self._cache.values()) / 1024 / 1024
        }

    def __len__(self) -> int:
        """Return number of cached files."""
        return len(self._cache)

    def __contains__(self, file_path: str) -> bool:
        """Check if file path is in cache using 'in' operator."""
        return file_path in self._cache