import sys
from common.imports import os, logging, Path, time, yaml, pd, plt, traceback
from common.project_imports import (
    extract_cell_id, extract_sample_name, Features, DQDVAnalysis,
    CellDatabase, NewarePlotter, FileSelector,
    configure_logging, DataLoader
)

sys.path.append(str(Path(__file__).parent))

# Define the path where all the python files are located. This is the directory where the logging
# will be saved
base_directory = os.getcwd()

# Load logger configuration
configure_logging(base_directory)

# Log the start of the program
logging.debug("MAIN. QC Neware Reader Started")


def process_files(ndax_file_list,
                  db,
                  selected_cycles=None,
                  enable_plotting=True,
                  gui_callback=None):
    """
    Process a list of NDAX files and return the extracted features dataframe.

    Args:
        ndax_file_list: List of NDAX files to process
        db: CellDatabase instance
        selected_cycles: List of 3 cycle numbers to process and display (default: [1, 2, 3])
        enable_plotting: Whether to generate plots
        gui_callback: Callback function for updating GUI

    Returns:
        DataFrame containing extracted features
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

    # Initialize DataLoader and load all files upfront
    data_loader = DataLoader()
    logging.debug("MAIN. Loading all NDAX files...")
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

    # Initialize containers for results
    all_features = []
    dqdv_data = {}

    # Process each file using cached data
    for file in ndax_file_list:
        # Skip files that failed to load
        if not data_loader.is_loaded(file):
            logging.warning(f"MAIN. Skipping file {os.path.basename(file)} - not loaded")
            continue

        filename_stem = Path(file).stem
        cell_ID = extract_cell_id(filename_stem)
        logging.debug(f"MAIN.Processing cell ID: {cell_ID}")

        sample_name = extract_sample_name(filename_stem)
        logging.debug(f"Main.Processing sample: {sample_name}")

        # Get data from DataLoader instead of reading file
        df = data_loader.get_data(file)
        if df is None:
            logging.warning(f"MAIN. No data available for {filename_stem}")
            continue

        # Extract active mass
        mass = db.get_mass(cell_ID)
        if mass is None or mass <= 0:
            logging.warning(f'MAIN.No mass found for cell {cell_ID}, using 1.0g')
            mass = 1.0
        else:
            logging.debug(f'MAIN.Mass for cell {cell_ID} is {mass}g')

        # Create a Features object once per file
        features_obj = Features(file)

        # Create a DQDVAnalysis object once per file
        dqdvanalysis_obj = DQDVAnalysis(file)

        # Initialize dQ/dV data dictionary for this file
        dqdv_data[filename_stem] = {}

        # Process each of the selected cycles
        for cycle in selected_cycles:
            logging.debug(f"MAIN.Extracting features for CYCLE {cycle}")

            # Check if cycle exists in the data
            if cycle not in df['Cycle'].unique():
                logging.debug(f"MAIN.Cycle {cycle} not found in file {filename_stem}, skipping")
                continue

            # Extract all features in one call
            feature_df = features_obj.extract(df, cycle, mass)

            # Add file name and cycle number to the DataFrame
            feature_df["cell ID"] = cell_ID
            feature_df["sample name"] = sample_name
            feature_df["Cycle"] = cycle
            feature_df["mass (g)"] = mass
            feature_df["file"] = filename_stem

            # Append results to list
            all_features.append(feature_df)

            # Calculate dQ/dV data for this cycle
            dqdv_result = dqdvanalysis_obj.extract_dqdv(df, cycle, mass)

            if dqdv_result:
                dqdv_data[filename_stem][cycle] = dqdv_result

    # Combine all results into a single DataFrame
    if all_features:
        final_features_df = pd.concat(all_features, ignore_index=True)

        # Generate plots if enabled
        if enable_plotting and ndax_file_list:
            try:
                logging.debug("MAIN.Generating capacity plots...")
                plotter = NewarePlotter(db)

                # Pass DataLoader to plotter instead of local cache
                fig = plotter.plot_ndax_files_with_loader(
                    data_loader,
                    ndax_file_list,
                    display_plot=False,
                    gui_callback=gui_callback,
                    selected_cycles=selected_cycles
                )

                # Generate dQ/dV plots
                logging.debug("MAIN.Generating dQ/dV plots...")
                dqdv_fig = plotter.plot_dqdv_curves_with_loader(
                    data_loader,
                    ndax_file_list,
                    dqdv_data=dqdv_data,
                    display_plot=False,
                    gui_callback=None,
                    selected_cycles=selected_cycles
                )

                # FIX: Update GUI with both plots and features data
                if gui_callback:
                    logging.debug(f"MAIN.GUI callback exists: {gui_callback}")

                    # Call the main plot update (this already works)
                    gui_callback(fig)

                    # Update the analysis table with features data
                    if hasattr(gui_callback.__self__, '_update_analysis_table'):
                        logging.debug("MAIN.Updating analysis table with features data")
                        gui_callback.__self__._update_analysis_table(final_features_df)

                    # Update dQ/dV tab if we have the figure
                    if dqdv_fig and hasattr(gui_callback.__self__, 'update_dqdv_plot'):
                        logging.debug("MAIN.GUI callback has update_dqdv_plot method")
                        # Extract plateau statistics using DQDVAnalysis batch method
                        dqdv_analyzer = DQDVAnalysis("plateau_extractor")
                        plateau_stats = dqdv_analyzer.extract_plateaus_batch(data_loader, db, ndax_file_list,
                                                                             selected_cycles)
                        # Extract plateau statistics
                        #plateau_stats = extract_plateau_stats_with_loader(data_loader, db, ndax_file_list,
                                                                          #selected_cycles)
                        logging.debug(f"MAIN.Extracted {len(plateau_stats)} plateau stats entries")
                        # Call the update method
                        try:
                            logging.debug("MAIN.Calling update_dqdv_plot method")
                            gui_callback.__self__.update_dqdv_plot(dqdv_fig, plateau_stats)
                            logging.debug("MAIN.update_dqdv_plot method call completed")
                        except Exception as e:
                            logging.debug(f"MAIN.Error in update_dqdv_plot: {e}")
                            logging.debug(traceback.format_exc())

                logging.debug("MAIN.Plotting complete.")

            except Exception as e:
                logging.debug(f"MAIN.Error during plotting: {e}")

        # Clean up DataLoader when done
        data_loader.clear_cache()
        logging.debug("MAIN.DataLoader cache cleared")

        logging.debug("MAIN.Features extracted, process_files finished")
        return final_features_df
    else:
        # Clean up DataLoader even if no features extracted
        data_loader.clear_cache()
        logging.debug("MAIN.No features extracted, process_files func finished.")
        return pd.DataFrame()

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
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)

    # Import paths
    data_path = config["data_path"]
    cell_database = config["cell_database_path"]
    output_file = config.get("output_file", "extracted_features.xlsx")
    enable_plotting = config.get("enable_plotting", True)  # New config option for plotting
    plots_dir = config.get("plots_directory", "plots")  # New config option for plot save directory

    # Load cell database with active mass (only once)
    logging.debug("MAIN. Loading cell database...")
    start_time = time.time()
    db = CellDatabase.get_instance()
    db.load_database(cell_database)
    elapsed = time.time() - start_time
    logging.debug(f"MAIN. Database loaded in {elapsed:.2f} seconds")

    # Keep all processed features
    all_processed_features = []

    # Create the file selector instance
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

        # Process files with plotting enabled
        features_df = process_files(
            ndax_file_list,
            db,
            selected_cycles=selected_cycles,  # Pass the selected cycles
            enable_plotting=enable_plotting,
            gui_callback=file_selector_instance.update_plot
        )

        if not features_df.empty:
            all_processed_features.append(features_df)
            logging.debug(f"MAIN.Features processed successfully")

            # Return the current batch features DataFrame
            return features_df

        return None

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