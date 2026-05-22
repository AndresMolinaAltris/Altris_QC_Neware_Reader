import timing_logger
from timing_logger import log as tlog

import sys
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from common.imports import os, logging, Path, time, yaml, pd, plt, traceback
from common.project_imports import (
    extract_cell_id, extract_sample_name, Features, DQDVAnalysis,
    CellDatabase, NewarePlotter, FileSelector,
    configure_logging, DataLoader
)
from features import warmup_scipy
from constants import COL_CYCLE


@dataclass
class ProcessingResult:
    """
    Structured result from process_files(), decoupling processing from GUI.

    This allows the caller to decide how to use the results (update GUI, save to file, etc.)
    without the processing logic needing to know about GUI implementation details.
    """
    features_df: pd.DataFrame
    capacity_fig: Optional[Any] = None  # matplotlib Figure
    dqdv_fig: Optional[Any] = None      # matplotlib Figure
    dqdv_data: Optional[Dict] = None    # Raw dQ/dV curves for plotting
    plateau_stats: Optional[List] = None  # Plateau statistics
    data_loader: Optional[Any] = None   # DataLoader kept alive for on-demand dQ/dV

sys.path.append(str(Path(__file__).parent))

# Define the path where all the python files are located. This is the directory where the logging
# will be saved
base_directory = os.getcwd()

# Load logger configuration
configure_logging(base_directory)

# Log the start of the program
logging.debug("MAIN. QC Neware Reader Started")
_startup_elapsed = time.perf_counter() - timing_logger.PROGRAM_START
logging.debug(f"[TIMING] program_startup | duration={_startup_elapsed:.3f}s | elapsed={_startup_elapsed:.3f}s")


def _extract_features_from_files(data_loader, ndax_file_list, db, cycles_to_process=None,
                                  extract_dqdv_curves=False, extract_plateau_stats=False,
                                  inflection_method="dV/dQ", manual_voltages=None):
    """
    Core feature extraction logic shared by processing functions.

    Args:
        data_loader: Initialized DataLoader with files already loaded
        ndax_file_list: List of file paths to process
        db: CellDatabase instance
        cycles_to_process: List of specific cycles, or None to process all available cycles
        extract_dqdv_curves: If True, extract dQ/dV curves (for plotting)
        extract_plateau_stats: If True, extract plateau statistics

    Returns:
        Tuple of (all_features, dqdv_data, plateau_stats)
    """
    all_features = []
    dqdv_data = {} if extract_dqdv_curves else None
    plateau_stats = [] if extract_plateau_stats else None

    for file in ndax_file_list:
        # Skip files that failed to load
        if not data_loader.is_loaded(file):
            logging.warning(f"MAIN. Skipping file {os.path.basename(file)} - not loaded")
            continue

        filename_stem = Path(file).stem
        cell_ID = extract_cell_id(filename_stem)
        sample_name = extract_sample_name(filename_stem)
        logging.debug(f"MAIN. Processing cell ID: {cell_ID}, sample: {sample_name}")

        # Get data from DataLoader
        df = data_loader.get_data(file)
        if df is None:
            logging.warning(f"MAIN. No data available for {filename_stem}")
            continue

        # Extract active mass: prefer NDAX metadata (already in memory), fall back to database
        ndax_mass = df.attrs.get('active_mass')
        if ndax_mass is not None and ndax_mass > 0:
            mass = ndax_mass
            logging.debug(f"MAIN. Using active mass from NDAX metadata for {cell_ID}: {mass}g")
        else:
            mass = db.get_mass(cell_ID)
            if mass is not None and mass > 0:
                logging.debug(f"MAIN. Using active mass from database for {cell_ID}: {mass}g")
            else:
                logging.warning(f"MAIN. No mass found for cell {cell_ID}, using 1.0g")
                mass = 1.0

        # Determine which cycles to process
        if cycles_to_process is None:
            cycles = sorted(df['Cycle'].unique())
            logging.debug(f"MAIN. Processing all {len(cycles)} cycles for {filename_stem}")
        else:
            cycles = cycles_to_process

        # Create feature and dqdv objects once per file
        features_obj = Features(file)
        dqdvanalysis_obj = DQDVAnalysis(file)

        # Initialize dQ/dV data for this file if needed
        if extract_dqdv_curves:
            dqdv_data[filename_stem] = {}

        # Process each cycle
        for cycle in cycles:
            # Check if cycle exists in the data
            if cycle not in df['Cycle'].unique():
                logging.debug(f"MAIN. Cycle {cycle} not found in file {filename_stem}, skipping")
                continue

            logging.debug(f"MAIN. Extracting features for {filename_stem}, cycle {cycle}")

            try:
                # Extract all features
                feature_df = features_obj.extract(df, cycle, mass)

                # Add metadata columns
                feature_df["cell ID"] = cell_ID
                feature_df["sample name"] = sample_name
                feature_df["Cycle"] = cycle
                feature_df["mass (g)"] = mass
                feature_df["file"] = filename_stem

                all_features.append(feature_df)

                # Extract dQ/dV curves if requested (for plotting)
                if extract_dqdv_curves:
                    dqdv_result = dqdvanalysis_obj.extract_dqdv(df, cycle, mass)
                    if dqdv_result:
                        dqdv_data[filename_stem][cycle] = dqdv_result

                # Extract plateau statistics if requested
                if extract_plateau_stats:
                    charge_c_rate, discharge_c_rate = DQDVAnalysis._calculate_crates_for_cycle(df, cycle, mass)
                    manual_tv = manual_voltages.get(cycle) if manual_voltages else None
                    # Unpack tuple (charge_tv, discharge_tv) or treat as legacy single float
                    charge_tv_manual = None
                    discharge_tv_manual = None
                    legacy_tv = None
                    if manual_tv is not None:
                        if isinstance(manual_tv, tuple):
                            charge_tv_manual, discharge_tv_manual = manual_tv
                        else:
                            legacy_tv = manual_tv
                    with tlog(f"DQDVAnalysis.extract_plateaus cycle={cycle}"):
                        plateau_data = dqdvanalysis_obj.extract_plateaus(df, cycle, mass, c_rate=charge_c_rate, discharge_c_rate=discharge_c_rate, inflection_method=inflection_method, transition_voltage=legacy_tv, charge_transition_voltage=charge_tv_manual, discharge_transition_voltage=discharge_tv_manual)
                    if plateau_data:
                        plateau_data["File"] = cell_ID
                        plateau_data["Cycle"] = cycle
                        plateau_stats.append(plateau_data)

            except Exception as e:
                logging.warning(f"MAIN. Error processing {filename_stem}, cycle {cycle}: {e}")

    return all_features, dqdv_data, plateau_stats


def _load_files_to_dataloader(ndax_file_list):
    """
    Initialize DataLoader and load all files.

    Args:
        ndax_file_list: List of file paths to load

    Returns:
        Initialized DataLoader instance
    """
    data_loader = DataLoader()
    logging.debug("MAIN. Loading all NDAX files...")
    with tlog(f"DataLoader.load_files n={len(ndax_file_list)}"):
        data_loader.load_files(ndax_file_list)

    # Log cache info
    cache_info = data_loader.get_cache_info()
    logging.debug(f"MAIN. DataLoader cache: {cache_info['cached_files']} files, "
                  f"{cache_info['total_rows']} total rows, "
                  f"{cache_info['memory_usage_mb']:.1f} MB")

    if cache_info['failed_files'] > 0:
        failed_files = data_loader.get_failed_files()
        logging.warning(f"MAIN. {cache_info['failed_files']} files failed to load: "
                        f"{[os.path.basename(f) for f in failed_files]}")

    return data_loader


def process_files(ndax_file_list,
                  db,
                  selected_cycles=None,
                  enable_plotting=True):
    """
    Process a list of NDAX files and return a structured ProcessingResult.

    Args:
        ndax_file_list: List of NDAX files to process
        db: CellDatabase instance
        selected_cycles: List of 3 cycle numbers to process and display (default: [1, 2, 3])
        enable_plotting: Whether to generate plots

    Returns:
        ProcessingResult containing features_df, figures, and statistics
    """
    logging.debug("MAIN. process_files started")

    # Use default cycles if none provided
    if selected_cycles is None or len(selected_cycles) == 0:
        selected_cycles = [1, 2, 3]

    # Ensure we have exactly 3 cycles (pad or trim as needed)
    while len(selected_cycles) < 3:
        selected_cycles.append(selected_cycles[-1] + 1 if selected_cycles else 1)
    selected_cycles = selected_cycles[:3]  # Limit to first 3 cycles if more provided

    logging.debug(f"MAIN. Using cycles: {selected_cycles}")

    # Load all files into DataLoader
    with tlog(f"process_files._load_files n={len(ndax_file_list)}"):
        data_loader = _load_files_to_dataloader(ndax_file_list)

    # Extract features using shared helper (dQ/dV is on-demand only)
    with tlog(f"process_files._extract_features n_files={len(ndax_file_list)} n_cycles={len(selected_cycles)}"):
        all_features, _, _ = _extract_features_from_files(
            data_loader, ndax_file_list, db,
            cycles_to_process=selected_cycles,
            extract_dqdv_curves=False,
            extract_plateau_stats=False
        )

    # Combine all results into a single DataFrame
    if not all_features:
        data_loader.clear_cache()
        logging.debug("MAIN.No features extracted, process_files func finished.")
        return ProcessingResult(features_df=pd.DataFrame())

    with tlog(f"pd.concat n_chunks={len(all_features)}"):
        final_features_df = pd.concat(all_features, ignore_index=True)

    # Initialize result with features
    capacity_fig = None

    # Generate capacity plot if enabled
    if enable_plotting and ndax_file_list:
        try:
            logging.debug("MAIN.Generating capacity plots...")
            plotter = NewarePlotter(db)

            with tlog(f"NewarePlotter.plot_ndax_files n={len(ndax_file_list)}"):
                capacity_fig = plotter.plot_ndax_files_with_loader(
                    data_loader,
                    ndax_file_list,
                    display_plot=False,
                    gui_callback=None,
                    selected_cycles=selected_cycles
                )

            logging.debug("MAIN.Capacity plot complete.")

        except Exception as e:
            logging.debug(f"MAIN.Error during plotting: {e}")

    # NOTE: data_loader is NOT cleared here — caller keeps it for on-demand dQ/dV
    logging.debug("MAIN.Features extracted, process_files finished")
    return ProcessingResult(
        features_df=final_features_df,
        capacity_fig=capacity_fig,
        data_loader=data_loader,
    )

def process_all_cycles_for_complete_analysis(ndax_file_list,
                                             db,
                                             data_loader=None,
                                             inflection_method="dV/dQ",
                                             manual_voltages=None):
    """
    Process all cycles from all files for complete analysis.
    Extracts both basic features and dQ/dV data for all available cycles.

    Args:
        ndax_file_list: List of NDAX files to process
        db: CellDatabase instance
        data_loader: Optional pre-loaded DataLoader. If provided, files are not
                     reloaded and the cache is not cleared on return.

    Returns:
        Tuple of (features_df, dqdv_stats) for all cycles
    """
    logging.debug("MAIN. process_all_cycles_for_complete_analysis started")

    # Use provided data_loader or load files ourselves
    owns_loader = data_loader is None
    if owns_loader:
        data_loader = _load_files_to_dataloader(ndax_file_list)

    # Extract features using shared helper (cycles_to_process=None means all cycles)
    all_features, _, plateau_stats = _extract_features_from_files(
        data_loader, ndax_file_list, db,
        cycles_to_process=None,  # Process all available cycles
        extract_dqdv_curves=False,
        extract_plateau_stats=True,
        inflection_method=inflection_method,
        manual_voltages=manual_voltages
    )

    # Only clear cache if we created the loader ourselves
    if owns_loader:
        data_loader.clear_cache()

    # Combine all results
    if all_features:
        final_features_df = pd.concat(all_features, ignore_index=True)
        logging.debug(f"MAIN. Complete analysis finished: {len(final_features_df)} total feature records")
        return final_features_df, plateau_stats
    else:
        logging.debug("MAIN. No features extracted for complete analysis")
        return pd.DataFrame(), []

def compute_dqdv(ndax_file_list, db, selected_cycles, data_loader):
    """
    Compute dQ/dV curves on demand and return the figure and raw data.

    Args:
        ndax_file_list: List of NDAX file paths
        db: CellDatabase instance
        selected_cycles: List of cycle numbers to plot
        data_loader: Pre-loaded DataLoader (from process_files result)

    Returns:
        Tuple of (dqdv_fig, dqdv_data) — figure may be None on failure
    """
    logging.debug("MAIN.compute_dqdv started")
    with tlog("warmup_scipy"):
        warmup_scipy()

    _, dqdv_data, _ = _extract_features_from_files(
        data_loader, ndax_file_list, db,
        cycles_to_process=selected_cycles,
        extract_dqdv_curves=True,
        extract_plateau_stats=False
    )

    dqdv_fig = None
    try:
        plotter = NewarePlotter(db)
        with tlog(f"NewarePlotter.plot_dqdv_curves n={len(ndax_file_list)}"):
            dqdv_fig = plotter.plot_dqdv_curves_with_loader(
                data_loader,
                ndax_file_list,
                dqdv_data=dqdv_data,
                display_plot=False,
                gui_callback=None,
                selected_cycles=selected_cycles,
                show_transition_markers=False
            )
    except Exception as e:
        logging.debug(f"MAIN.compute_dqdv plotting error: {e}")

    logging.debug("MAIN.compute_dqdv finished")
    return dqdv_fig, dqdv_data


def compute_transition_voltages(ndax_file_list, db, selected_cycles, data_loader,
                                inflection_method="dV/dQ", manual_voltages=None):
    """
    Compute plateau/transition voltage statistics on demand.

    Args:
        ndax_file_list: List of NDAX file paths
        db: CellDatabase instance
        selected_cycles: List of cycle numbers to analyse
        data_loader: Pre-loaded DataLoader
        manual_voltages: Optional dict mapping cycle number to manual transition voltage

    Returns:
        List of plateau statistics dicts
    """
    logging.debug("MAIN.compute_transition_voltages started")
    dqdv_analyzer = DQDVAnalysis("plateau_extractor")
    with tlog(f"extract_plateaus_batch n_files={len(ndax_file_list)} n_cycles={len(selected_cycles)}"):
        plateau_stats = dqdv_analyzer.extract_plateaus_batch(
            data_loader, db, ndax_file_list, selected_cycles,
            inflection_method=inflection_method,
            manual_voltages=manual_voltages
        )
    logging.debug(f"MAIN.compute_transition_voltages finished: {len(plateau_stats)} entries")
    return plateau_stats


def main():
    """
    Main entry point for the Altris QC Neware Reader.

    Loads configuration from config.yaml, initializes the cell database,
    and processes NDAX files using the GUI file selector. Each batch of
    files is processed separately, with results saved to Excel files.

    Features are extracted from cycles 1-3 for each file, and optionally
    plots are generated based on configuration settings.

    No parameters or return values as this is the application entry point.
    """

    # Import configuration file
    with tlog("main.config_load"):
        with open("config.yaml", "r") as file:
            config = yaml.safe_load(file)

    # Import paths
    data_path = config["data_path"]
    cell_database = config["cell_database_path"]
    output_file = config.get("output_file", "extracted_features.xlsx")
    enable_plotting = config.get("enable_plotting", True)  # New config option for plotting
    plots_dir = config.get("plots_directory", "plots")  # New config option for plot save directory

    # Set cell database path for lazy loading (only loaded when NDAX metadata is missing)
    with tlog("main.database_init"):
        db = CellDatabase.get_instance()
        db.set_database_path(cell_database)
    logging.debug("MAIN. Cell database path set (will load on demand)")

    # Keep all processed features
    all_processed_features = []

    # Create the file selector instance
    with tlog("main.FileSelector_init"):
        file_selector_instance = FileSelector(initial_dir=data_path, default_output_file=output_file)

    # Define a callback function to process files
    def process_file_callback(ndax_file_list):
        """
        Callback function for processing batches of NDAX files.

        Args:
            ndax_file_list (list): List of paths to NDAX files to process

        Returns:
            pd.DataFrame: The extracted features for the current batch
        """
        logging.debug("MAIN.process_file_callback func started")
        nonlocal all_processed_features

        if not ndax_file_list:
            print("No files to process.")
            return None

        # Display summary of selected files
        logging.debug(f"MAIN.Processing {len(ndax_file_list)} files:")
        for i, file in enumerate(ndax_file_list[:5], 1):  # Show first 5 files
            logging.debug(f"MAIN. {i}. {os.path.basename(file)}")
        if len(ndax_file_list) > 5:
            logging.debug(f"MAIN.  ... and {len(ndax_file_list) - 5} more files")

        # Get selected cycles from the file selector
        selected_cycles = file_selector_instance.selected_cycles
        logging.debug(f"MAIN.Using selected cycles: {selected_cycles}")

        # Process files - returns structured ProcessingResult
        with tlog(f"process_files n={len(ndax_file_list)}"):
            result = process_files(
                ndax_file_list,
                db,
                selected_cycles=selected_cycles,
                enable_plotting=enable_plotting
            )

        if result.features_df.empty:
            return None

        # Store features for later use
        all_processed_features.append(result.features_df)
        logging.debug("MAIN.Features processed successfully")

        # Update GUI with results - direct method calls instead of hasattr introspection
        try:
            # Update capacity plot
            if result.capacity_fig:
                with tlog("GUI.update_plot"):
                    file_selector_instance.update_plot(result.capacity_fig)

            # Update analysis table
            with tlog("GUI._update_analysis_table"):
                file_selector_instance._update_analysis_table(result.features_df)

            # Store data_loader for on-demand dQ/dV and enable the button
            if result.data_loader is not None:
                file_selector_instance._data_loader = result.data_loader
                if hasattr(file_selector_instance, 'calc_dqdv_btn'):
                    file_selector_instance.calc_dqdv_btn.config(state="normal")
                if hasattr(file_selector_instance, 'fusi_generate_btn'):
                    file_selector_instance.fusi_generate_btn.config(state="normal")

        except Exception as e:
            logging.debug(f"MAIN.Error updating GUI: {e}")
            logging.debug(traceback.format_exc())

        return result.features_df

    # Main processing path based on configuration
    logging.debug("MAIN. Opening file selector")
    file_selector_instance.show_interface(process_callback=process_file_callback)

    # When the GUI is closed, we're done
    logging.debug("MAIN. File selection window closed. Processing complete.")
    logging.debug("MAIN. Program ending. Attempting to close matplotlib resources.")
    plt.close('all')  # Close all matplotlib figures
    logging.debug("MAIN. Matplotlib figures closed. Program should terminate now.")
    logging.debug("MAIN.Program complete.")


if __name__ == "__main__":
    main()