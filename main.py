from data_import import *
import features
import NewareNDA
from pathlib import Path
from cell_database import CellDatabase
from statistical_analysis import *
import openpyxl
import yaml
from file_selector import select_ndax_files  # Import the new file selector

# Import configuration file
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

data_path = config["data_path"]
cell_database = config["cell_database_path"]
use_gui = config.get("use_gui", True)  # Add a new config option for GUI

# Get Neware files - either from GUI or file search
if use_gui:
    # Use GUI file selector
    ndax_file_list = select_ndax_files(initial_dir=data_path)
    if not ndax_file_list:
        print("No files selected. Exiting...")
        exit()
else:
    # Find all Neware files (original behavior)
    ndax_file_list = find_ndax_files(data_path)
    if not ndax_file_list:
        print(f"No .ndax files found in {data_path}. Exiting...")
        exit()

print(f"Processing {len(ndax_file_list)} files...")

# load cell database with active mass
db = CellDatabase.get_instance()
db.load_database(cell_database)

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
        feature_df["sample  name"] = sample_name
        feature_df["Cycle"] = cycle
        feature_df["mass (g)"] = mass

        # Append results to list
        all_features.append(feature_df)

# Combine all results into a single DataFrame
final_features_df = pd.concat(all_features, ignore_index=True)

# Save results to Excel file
output_file = config.get("output_file", "extracted_features.xlsx")
print(f"Saving results to {output_file}...")
final_features_df.to_excel(output_file, index=False)

print("Processing complete!")