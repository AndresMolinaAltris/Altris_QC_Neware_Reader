from data_import import *
import features
import NewareNDA
from pathlib import Path
from cell_database import CellDatabase
import openpyxl
import yaml
import time
import os
import pandas as pd
from file_selector import select_ndax_files  # Import the new file selector


def process_files(ndax_file_list, db, output_file=None):
    """
    Process a list of NDAX files and return the extracted features dataframe.

    Args:
        ndax_file_list (list): List of NDAX file paths to process
        db (CellDatabase): Instance of the cell database
        output_file (str, optional): Path to save the results

    Returns:
        pandas.DataFrame: DataFrame containing all extracted features
    """
    # Initialize an empty DataFrame to store extracted features
    all_features = []

    # Process each file
    for file in ndax_file_list:
        filename_stem = Path(file).stem
        cell_ID = extract_cell_id(filename_stem)
        print(f"Processing cell ID: {cell_ID}")

        sample_name = extract_sample_name(filename_stem)
        print(f"Processing sample: {sample_name}")

        # Read data from Neware NDA file
        df = NewareNDA.read(file)

        # Extract active mass
        mass = db.get_mass(cell_ID)
        print(f'Mass for cell {cell_ID} is {mass}')

        # Create a Features object once per file
        features_obj = features.Features(file)

        # Process multiple cycles
        for cycle in range(1, 4):  # Cycles 1, 2, 3
            print(f"Extracting features for CYCLE {cycle}")

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
            print(f"Saving results to {output_file}...")
            final_features_df.to_excel(output_file, index=False)

        return final_features_df
    else:
        print("No features extracted.")
        return pd.DataFrame()


def main():
    # Import configuration file
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)

    # Import paths
    data_path = config["data_path"]
    cell_database = config["cell_database_path"]
    use_gui = config.get("use_gui", True)  # Add a new config option for GUI
    output_file = config.get("output_file", "extracted_features.xlsx")

    # Load cell database with active mass (only once)
    print("Loading cell database...")
    start_time = time.time()
    db = CellDatabase.get_instance()
    db.load_database(cell_database)
    elapsed = time.time() - start_time
    print(f"Database loaded in {elapsed:.2f} seconds")

    # Keep all processed features
    all_processed_features = []

    # Define a callback function to process files
    def process_file_callback(ndax_file_list):
        nonlocal all_processed_features

        if not ndax_file_list:
            print("No files to process.")
            return

        # Display summary of selected files
        print(f"\nProcessing {len(ndax_file_list)} files:")
        for i, file in enumerate(ndax_file_list[:5], 1):  # Show first 5 files
            print(f"  {i}. {os.path.basename(file)}")
        if len(ndax_file_list) > 5:
            print(f"  ... and {len(ndax_file_list) - 5} more files")

        # Process current batch of files
        batch_number = len(all_processed_features) + 1
        batch_output = f"batch_{batch_number}_{output_file}"
        features_df = process_files(ndax_file_list, db, batch_output)

        if not features_df.empty:
            all_processed_features.append(features_df)
            print(f"Batch {batch_number} processed successfully. Results saved to {batch_output}")

            # Combine all batches processed so far
            if len(all_processed_features) > 1:
                combined_df = pd.concat(all_processed_features, ignore_index=True)
                combined_df.to_excel(output_file, index=False)
                print(f"All results combined and saved to {output_file}")

    # Main processing path based on configuration
    # Use GUI file selector with callback to process files
    print("Opening file selector. Please select files and click 'Process Files' button when ready.")
    select_ndax_files(initial_dir=data_path, callback=process_file_callback)
    # When the GUI is closed, we're done
    print("\nFile selection window closed. Processing complete.")


    # Combine all batches if there were multiple
    if len(all_processed_features) > 1:
        print("\nCombining all processed batches...")
        final_df = pd.concat(all_processed_features, ignore_index=True)
        final_df.to_excel(output_file, index=False)
        print(f"All results combined and saved to {output_file}")
    elif len(all_processed_features) == 1:
        print(f"\nProcessing complete. Results saved to {batch_output}")
    else:
        print("\nNo files were processed.")

    print("\nProgram complete.")


if __name__ == "__main__":
    main()