import sys
from common.imports import os, logging, Path, time, yaml, pd, plt, NewareNDA, traceback
from common.project_imports import (
    extract_cell_id, extract_sample_name, Features, DQDVAnalysis,
    CellDatabase, NewarePlotter, FileSelector,
    configure_logging
)

sys.path.append(str(Path(__file__).parent))


# Define the path where all the python files are located. This is the directory where the logging
# will be saved
base_directory = os.getcwd()

# Load logger configuration
configure_logging(base_directory)

# Log the start of the program
logging.debug("MAIN. QC Neware Reader Started")


def data_loader(ndax_file_list,
                db,
                selected_cycles=None):

    # Use default cycles if none provided
    if selected_cycles is None or len(selected_cycles) == 0:
        selected_cycles = [1, 2, 3]

        # Ensure we have exactly 3 cycles (pad or trim as needed)
    while len(selected_cycles) < 3:
        selected_cycles.append(selected_cycles[-1] + 1 if selected_cycles else 1)
    selected_cycles = selected_cycles[:3]  # Limit to first 3 cycles if more provided

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

        # Store the processed data and metadata in the cache
        ndax_data_cache[filename_stem] = {
            "df": df,
            "cell_id": cell_ID,
            "mass": mass,
            "sample_name": sample_name
        }
    return ndax_data_cache, selected_cycles

# def extract_plateau_stats(ndax_data_cache, selected_cycles=None):
#     """
#     Extract plateau capacity statistics from the processed data for display in the UI.
#
#     Args:
#         ndax_data_cache: Dictionary from data_loader containing processed NDAX data
#         selected_cycles: List of cycles to extract plateaus for (default: [1, 2, 3])
#
#     Returns:
#         List of dictionaries with plateau capacity statistics
#     """
#     logging.debug("MAIN.extract_plateau_stats started")
#
#     # Use default cycles if none provided
#     if selected_cycles is None:
#         selected_cycles = [1, 2, 3]
#
#     stats = []
#     # Create a DQDVAnalysis object for plateau extraction
#     dqdvanalysis_obj = DQDVAnalysis("plateau_extractor")
#
#     for file_name, df in ndax_data_cache.items():
#         #for key, df in ndax_data_cache.items():
#          #   print(f"Headers for {key}: {df.columns.tolist()}")
#
#         ############### I'M trying to FIGURE OUT THE PART WITH df and data, there is a problem here ########
#         ### IT SEEMS THAT THE DATALOADER IS NOT BEING CALLED AT ALL! ####################################
#         # THE DATA LOADER FUNCTION IS NOT BEING CALLED ANYWHERE #########################################
#
#         # Get DataFrame and mass from cache
#         #print(df.columns)
#         #df = data["df"]
#         #mass = data["mass"]
#         #cell_id = data["cell_id"]
#
#         # Extract plateaus for each selected cycle
#         for cycle in selected_cycles:
#             # Skip if cycle doesn't exist in this file
#             if cycle not in df['Cycle'].unique():
#                 logging.debug(f"Cycle {cycle} not found in file {file_name}, skipping plateau extraction")
#                 continue
#
#             try:
#                 # Extract plateau capacities
#                 logging.debug("MAIN.extracting plateau data")
#                 plateau_data = dqdvanalysis_obj.extract_plateaus(df, cycle, mass)
#
#                 if plateau_data:
#                     # Add file and cycle information
#                     plateau_data["File"] = file_name
#                     plateau_data["Cycle"] = cycle
#
#                     # Add to statistics
#                     stats.append(plateau_data)
#             except Exception as e:
#                 logging.debug(f"Error extracting plateau data for {file_name}, cycle {cycle}: {e}")
#
#     logging.debug("MAIN.extract_plateau_stats finished")
#
#     return stats


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

                # Pass selected cycles to plotter
                fig = plotter.plot_ndax_files(
                    ndax_file_list,
                    preprocessed_data=ndax_data_cache,
                    display_plot=False,
                    gui_callback=gui_callback,
                    selected_cycles=selected_cycles  # Pass the cycles
                )

                # Generate dQ/dV plots
                logging.debug("MAIN.Generating dQ/dV plots...")
                dqdv_fig = plotter.plot_dqdv_curves(
                    ndax_file_list,
                    dqdv_data=dqdv_data,
                    display_plot=False,
                    gui_callback=None,
                    selected_cycles=selected_cycles
                )

                # If we have a GUI and dQ/dV plot, update the dQ/dV tab
                if gui_callback:
                    logging.debug(f"MAIN.GUI callback exists: {gui_callback}")
                    if dqdv_fig:
                        logging.debug(f"MAIN.dQ/dV figure exists: {dqdv_fig}")
                        if hasattr(gui_callback.__self__, 'update_dqdv_plot'):
                            logging.debug("MAIN.GUI callback has update_dqdv_plot method")
                            # Extract plateau statistics
                            plateau_stats = extract_plateau_stats(ndax_data_cache, db, selected_cycles)
                            #plateau_stats = extract_plateau_stats(ndax_data_cache, selected_cycles)
                            logging.debug(f"MAIN.Extracted {len(plateau_stats)} plateau stats entries")
                            # Call the update method
                            try:
                                logging.debug("MAIN.Calling update_dqdv_plot method")
                                gui_callback.__self__.update_dqdv_plot(dqdv_fig, plateau_stats)
                                logging.debug("MAIN.update_dqdv_plot method call completed")
                            except Exception as e:
                                logging.debug(f"MAIN.Error in update_dqdv_plot: {e}")
                                logging.debug(traceback.format_exc())
                        else:
                            logging.debug("MAIN.GUI callback does not have update_dqdv_plot method")
                    else:
                        logging.debug("MAIN.No dQ/dV figure generated")
                else:
                    logging.debug("MAIN.No GUI callback provided")

                logging.debug("MAIN.Plotting complete.")

            except Exception as e:
                logging.debug(f"MAIN.Error during plotting: {e}")

        logging.debug("MAIN.Features extracted, process_files finished")
        return final_features_df
    else:
        logging.debug("MAIN.No features extracted, process_files func finished.")
        return pd.DataFrame()





def extract_plateau_stats(ndax_data_cache, db, selected_cycles=None):
    """
    Extract plateau capacity statistics from the processed data for display in the UI.

    Args:
        ndax_data_cache: Dictionary containing processed NDAX data
        db: CellDatabase instance for mass lookup
        selected_cycles: List of cycles to extract plateaus for (default: [1, 2, 3])

    Returns:
        List of dictionaries with plateau capacity statistics
    """
    logging.debug("MAIN.extract_plateau_stats started")

    # Use default cycles if none provided
    if selected_cycles is None:
        selected_cycles = [1, 2, 3]

    stats = []

    # Create a DQDVAnalysis object for plateau extraction
    dqdvanalysis_obj = DQDVAnalysis("plateau_extractor")

    for file_name, df in ndax_data_cache.items():
        for key, df in ndax_data_cache.items():
            print(f"Headers for {key}: {df.columns.tolist()}")
        # Get cell ID and mass for specific capacity calculations
        cell_ID = extract_cell_id(file_name)
        mass = db.get_mass(cell_ID) or 1.0

        # Extract plateaus for each selected cycle
        for cycle in selected_cycles:
            # Skip if cycle doesn't exist in this file
            if cycle not in df['Cycle'].unique():
                logging.debug(f"Cycle {cycle} not found in file {file_name}, skipping plateau extraction")
                continue

            try:
                # Extract plateau capacities
                #plateau_data = features_obj.extract_plateaus(df, cycle, mass)
                plateau_data = dqdvanalysis_obj.extract_plateaus(df, cycle, mass)


                if plateau_data:
                    # Add file and cycle information
                    plateau_data["File"] = file_name
                    plateau_data["Cycle"] = cycle

                    # Add to statistics
                    stats.append(plateau_data)
            except Exception as e:
                logging.debug(f"Error extracting plateau data for {file_name}, cycle {cycle}: {e}")

    logging.debug("MAIN.extract_plateau_stats finished")

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