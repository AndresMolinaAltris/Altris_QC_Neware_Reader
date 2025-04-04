import sys
from common.imports import os, logging, Path, time, yaml, pd, plt, NewareNDA, np
from common.project_imports import (
    extract_cell_id, extract_sample_name, Features,
    CellDatabase, NewarePlotter, FileSelector,
    configure_logging
)

from scipy.signal import find_peaks

sys.path.append(str(Path(__file__).parent))


# Define the path where all the python files are located. This is the directory where the logging
# will be saved
base_directory = os.getcwd()

# Load logger configuration
configure_logging(base_directory)

# Log the start of the program
logging.debug("MAIN. QC Neware Reader Started")


def process_files(ndax_file_list, db, output_file=None, enable_plotting=True,
                  save_plots_dir=None, gui_callback=None):
    """
    Process a list of NDAX files and return the extracted features dataframe.
    """
    logging.debug("MAIN. process_files started")

    # Initialize an empty DataFrame to store extracted features
    all_features = []

    # Dictionary to store dQ/dV data
    dqdv_data = {}

    # Create a cache for the processed NDAX files
    ndax_data_cache = {}

    # Process each file
    for file in ndax_file_list:
        filename_stem = Path(file).stem
        cell_ID = extract_cell_id(filename_stem)
        logging.debug(f"MAIN.Processing cell ID: {cell_ID}")

        sample_name = extract_sample_name(filename_stem)
        logging.debug(f"Main.Processing sample: {sample_name}")

        # Read data from Neware NDA file - only once
        logging.debug(f"MAIN.Reading file: {file}")
        df = NewareNDA.read(file)

        # Store the processed data in the cache
        ndax_data_cache[filename_stem] = df

        # Extract active mass
        mass = db.get_mass(cell_ID)
        logging.debug(f'MAIN.Mass for cell {cell_ID} is {mass}')

        # Create a Features object once per file
        features_obj = Features(file)

        # Initialize dQ/dV data dictionary for this file
        dqdv_data[filename_stem] = {}

        # Process multiple cycles
        for cycle in range(1, 4):  # Cycles 1, 2, 3
            logging.debug(f"MAIN.Extracting features for CYCLE {cycle}")

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
            dqdv_result = features_obj.extract_dqdv(df, cycle, mass)
            if dqdv_result:
                dqdv_data[filename_stem][cycle] = dqdv_result

    # Combine all results into a single DataFrame
    if all_features:
        final_features_df = pd.concat(all_features, ignore_index=True)

        # Save results if output file is specified
        if output_file:
            logging.debug(f"MAIN.Saving results to {output_file}...")
            final_features_df.to_excel(output_file, index=False)

        # Generate plots if enabled
        if enable_plotting and ndax_file_list:
            try:
                logging.debug("MAIN.Generating capacity plots...")
                plotter = NewarePlotter(db)

                # Pass the cached data to avoid reading files again
                fig = plotter.plot_ndax_files(
                    ndax_file_list,
                    preprocessed_data=ndax_data_cache,  # Pass the cache here
                    display_plot=False,
                    gui_callback=gui_callback
                )

                # Generate dQ/dV plots
                logging.debug("MAIN.Generating dQ/dV plots...")
                dqdv_fig = plotter.plot_dqdv_curves(
                    ndax_file_list,
                    dqdv_data=dqdv_data,
                    display_plot=False,
                    gui_callback=None  # We'll update manually
                )

                # If we have a GUI and dQ/dV plot, update the dQ/dV tab
                if gui_callback and dqdv_fig and hasattr(gui_callback.__self__, 'update_dqdv_plot'):
                    # Extract plateau statistics instead of peak statistics
                    plateau_stats = extract_plateau_stats(ndax_data_cache, db)
                    gui_callback.__self__.update_dqdv_plot(dqdv_fig, plateau_stats)

                logging.debug("MAIN.Plotting complete.")

            except Exception as e:
                logging.debug(f"MAIN.Error during plotting: {e}")

        logging.debug("MAIN.Features extracted, process_files finished")
        return final_features_df
    else:
        logging.debug("MAIN.No features extracted, process_files func finished.")
        return pd.DataFrame()


def extract_plateau_stats(ndax_data_cache, db):
    """
    Extract plateau capacity statistics from the processed data for display in the UI.

    Args:
        ndax_data_cache: Dictionary containing processed NDAX data
        db: CellDatabase instance for mass lookup

    Returns:
        List of dictionaries with plateau capacity statistics
    """
    stats = []

    # Create a Features object for plateau extraction
    features_obj = Features("plateau_extractor")

    for file_name, df in ndax_data_cache.items():
        # Get cell ID and mass for specific capacity calculations
        cell_ID = extract_cell_id(file_name)
        mass = db.get_mass(cell_ID) or 1.0

        # Extract plateaus for each cycle
        for cycle in range(1, 4):  # Cycles 1, 2, 3
            try:
                # Extract plateau capacities
                plateau_data = features_obj.extract_plateaus(df, cycle, mass)

                if plateau_data:
                    # Add file and cycle information
                    plateau_data["File"] = file_name
                    plateau_data["Cycle"] = cycle

                    # Add to statistics
                    stats.append(plateau_data)
            except Exception as e:
                logging.debug(f"Error extracting plateau data for {file_name}, cycle {cycle}: {e}")

    return stats


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
    use_gui = config.get("use_gui", True)  # Add a new config option for GUI
    output_file = config.get("output_file", "extracted_features.xlsx")
    enable_plotting = config.get("enable_plotting", True)  # New config option for plotting
    plots_dir = config.get("plots_directory", "plots")  # New config option for plot save directory

    # Create plots directory if needed
    if enable_plotting and not os.path.exists(plots_dir):
        os.makedirs(plots_dir, exist_ok=True)

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

        Processes a batch of files selected by the user, extracts features,
        generates plots if enabled, and saves results to Excel. Also combines
        all processed batches into a single output file.

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

        # Process current batch of files
        batch_number = len(all_processed_features) + 1
        batch_output = None

        # Process files with plotting enabled
        features_df = process_files(
            ndax_file_list,
            db,
            batch_output,
            enable_plotting=enable_plotting,
            save_plots_dir=plots_dir,
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