import sys
from pathlib import Path
from common.imports import os, logging, Path, time, yaml, pd, plt, NewareNDA
from common.project_imports import (
    extract_cell_id, extract_sample_name, Features,
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


def process_files(ndax_file_list, db, output_file=None, enable_plotting=True,
                  save_plots_dir=None, gui_callback=None):
    """
    Process a list of NDAX files and return the extracted features dataframe.

    Extracts electrochemical features from cycles 1-3 of each NDAX file,
    using cell mass data from the database. Optionally saves results to an
    Excel file and generates capacity plots.

    Args:
        ndax_file_list (list): List of paths to NDAX files to process
        db (CellDatabase): Instance of the cell database for mass lookup
        output_file (str, optional): Path to save the results Excel file
        enable_plotting (bool): Whether to generate capacity plots
        save_plots_dir (str, optional): Directory to save generated plots
        gui_callback (callable, optional): Function to call with the figure for GUI display

    Returns:
        pandas.DataFrame: DataFrame containing all extracted features with columns for
                         cell ID, sample name, cycle number, and various electrochemical
                         parameters (capacities, internal resistances, etc.)
    """

    logging.debug("MAIN. process_files started")

    # Initialize an empty DataFrame to store extracted features
    all_features = []

    # Process each file
    for file in ndax_file_list:
        filename_stem = Path(file).stem
        cell_ID = extract_cell_id(filename_stem)
        logging.debug(f"MAIN.Processing cell ID: {cell_ID}")

        sample_name = extract_sample_name(filename_stem)
        logging.debug(f"Main.Processing sample: {sample_name}")

        # Read data from Neware NDA file
        df = NewareNDA.read(file)

        # Extract active mass
        mass = db.get_mass(cell_ID)
        logging.debug(f'MAIN.Mass for cell {cell_ID} is {mass}')

        # Create a Features object once per file
        features_obj = Features(file)

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

    # Combine all results into a single DataFrame
    if all_features:
        final_features_df = pd.concat(all_features, ignore_index=True)

        # Save results if output file is specified
        if output_file:
            logging.debug(f"MAIN.Saving results to {output_file}...")
            final_features_df.to_excel(output_file, index=False)

        # Generate plots if enabled
        # In main.py process_files function
        if enable_plotting and ndax_file_list:
            try:
                logging.debug("MAIN.Generating capacity plots...")
                plotter = NewarePlotter(db)
                fig = plotter.plot_ndax_files(
                    ndax_file_list,
                    display_plot=False,  # Don't show in separate window
                    gui_callback=gui_callback
                )
                logging.debug("MAIN.Plotting complete.")

            except Exception as e:
                logging.debug(f"MAIN.Error during plotting: {e}")

        logging.debug("MAIN.Features extracted, process_files finished")
        return final_features_df
    else:
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
    file_selector_instance = FileSelector(initial_dir=data_path)

    # Define a callback function to process files
    def process_file_callback(ndax_file_list):
        """
        Callback function for processing batches of NDAX files.

        Processes a batch of files selected by the user, extracts features,
        generates plots if enabled, and saves results to Excel. Also combines
        all processed batches into a single output file.

        Args:
            ndax_file_list (list): List of paths to NDAX files to process
        """

        logging.debug("MAIN.process_file_callback func started")
        nonlocal all_processed_features

        if not ndax_file_list:
            print("No files to process.")
            return

        # Display summary of selected files
        logging.debug(f"MAIN.Processing {len(ndax_file_list)} files:")
        for i, file in enumerate(ndax_file_list[:5], 1):  # Show first 5 files
            logging.debug(f"MAIN. {i}. {os.path.basename(file)}")
        if len(ndax_file_list) > 5:
            logging.debug(f"MAIN.  ... and {len(ndax_file_list) - 5} more files")

        # Process current batch of files
        batch_number = len(all_processed_features) + 1
        batch_output = f"batch_{batch_number}_{output_file}"

        # Process files with plotting enabled. This is the part that send the plot
        # to the GUI though the callback (gui_callback)
        logging.debug("MAIN.Sending plot to GUI.")
        features_df = process_files(
            ndax_file_list,
            db,
            batch_output,
            enable_plotting=enable_plotting,
            save_plots_dir=plots_dir,
            gui_callback = file_selector_instance.update_plot
        )

        if not features_df.empty:
            all_processed_features.append(features_df)
            logging.debug(f"MAIN.Batch {batch_number} processed successfully. Results saved to {batch_output}")

            # Combine all batches processed so far
            if len(all_processed_features) > 1:
                combined_df = pd.concat(all_processed_features, ignore_index=True)
                combined_df.to_excel(output_file, index=False)
                logging.debug(f"MAIN.All results combined and saved to {output_file}")

    # Main processing path based on configuration
    logging.debug("MAIN. Opening file selector")
    file_selector_instance.show_interface(process_callback=process_file_callback)

    # When the GUI is closed, we're done
    logging.debug("MAIN. File selection window closed. Processing complete.")

    # Combine all batches if there were multiple
    if len(all_processed_features) > 1:
        logging.debug("MAIN.Combining all processed batches...")
        final_df = pd.concat(all_processed_features, ignore_index=True)
        final_df.to_excel(output_file, index=False)
        logging.debug(f"MAIN. All results combined and saved to {output_file}")
    elif len(all_processed_features) == 1:
        logging.debug(f"MAIN.Processing complete. Results saved to batch_{len(all_processed_features)}_{output_file}")
    else:
        logging.debug("MAIN.No files were processed.")

    logging.debug("MAIN. Program ending. Attempting to close matplotlib resources.")
    plt.close('all')  # Close all matplotlib figures
    logging.debug("MAIN. Matplotlib figures closed. Program should terminate now.")

    logging.debug("MAIN.Program complete.")


if __name__ == "__main__":
    main()