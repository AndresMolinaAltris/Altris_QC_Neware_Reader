# Altris QC Neware Reader

A Python-based tool for analyzing electrochemical data from Neware battery testing equipment NDAX files.

## Overview

The Altris QC Neware Reader is designed to extract, analyze, and visualize electrochemical test data from Neware battery testing equipment. It processes NDAX files to calculate key metrics such as specific charge/discharge capacities and internal resistance at different state-of-charge (SOC) levels. The calculation and visualizations are designed by default for the first three cycles.

### Key Features

- Bulk processing of multiple NDAX files
- Extraction of critical electrochemical parameters:
  - Charge capacity (mAh)
  - Specific charge capacity (mAh/g)
  - Discharge capacity (mAh)
  - Specific discharge capacity (mAh/g)
  - Internal resistance at SOC 100% (Ohms)
  - Internal resistance at SOC 0% (Ohms)
- Interactive graphical user interface for file selection
- Capacity curve visualization
- Automated performance data export to Excel

## Installation

### Prerequisites

- Python 3.6+
- Neware NDA library (`NewareNDA`)
- Required Python packages (install via pip):
  ```
  pip install pandas numpy matplotlib pyyaml tk
  ```

### Setup

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/altris-qc-neware-reader.git
   cd altris-qc-neware-reader
   ```

2. Create a `config.yaml` file in the root directory with the following structure:
   ```yaml
   data_path: "path/to/your/ndax/files"
   cell_database_path: "path/to/your/cell_database.xlsx"
   output_file: "extracted_features.xlsx"
   enable_plotting: true
   plots_directory: "plots"
   use_gui: true
   ```

3. Ensure you have a cell database Excel file that contains the cell ID as`Name/ID` and the active material mass as`Active mass (mg)` columns. If the cell database is not loaded correctly or does not contain the active mass for the Cell ID, the program will take the mass as 1 for calculating specific charge and sicharge capacity.

## Usage

### Running the Application

Start the application by running:

```
python main.py
```

This will:
1. Load the configuration from `config.yaml`
2. Initialize the cell database from the specified Excel file
3. Open the GUI file selector interface

### Using the GUI

The file selector interface allows you to:

1. Navigate to directories containing NDAX files
2. Select files for processing
3. View a real-time preview of capacity curves
4. Process selected files to extract features
5. Save generated plots

### Data Processing

The application processes NDAX files to extract:
- Charge and discharge capacities for cycles 1-3
- Internal resistance measurements at different SOC levels
- Specific capacities normalized by active material mass

Results are automatically saved to Excel files for further analysis.

## Code Structure

- `main.py`: Application entry point and main processing logic
- `features.py`: Feature extraction from electrochemical data
- `cell_database.py`: Cell mass data management with caching
- `data_import.py`: Utilities for importing and parsing NDAX data
- `file_selector.py`: GUI interface for file selection and visualization
- `neware_plotter.py`: Data visualization components
- `logger_configurator.py`: Logging setup and configuration

## Logging

The application maintains detailed logs in the `logs` directory. Each log file is timestamped and includes debug information about the processing steps.

## Troubleshooting

### Common Issues

- **Missing cell mass data**: Ensure your cell database has the correct format and cell IDs match between NDAX files and the database.
- **Plot display issues**: If plots don't display correctly, check that matplotlib is properly installed and configured.
- **File access errors**: Verify that the application has read/write permissions for all specified directories.

### Debugging

For more detailed debugging information, check the application logs in the `logs` directory.
