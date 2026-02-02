# Altris QC Neware Reader

A Python-based tool for analyzing electrochemical data from Neware battery testing equipment NDAX files.

## Overview

The Altris QC Neware Reader is designed to extract, analyze, and visualize electrochemical test data from Neware battery testing equipment. It processes NDAX files to calculate key metrics such as specific charge/discharge capacities, internal resistance at different state-of-charge (SOC) levels, coulombic efficiency, and differential capacity (dQ/dV) profiles. The application supports analysis of all cycles in a dataset and includes advanced features for identifying electrochemical processes and battery degradation through plateau analysis and differential capacity curves.

### Key Features

- Bulk processing of multiple NDAX files
- Extraction of critical electrochemical parameters:
  - Charge and discharge capacity (mAh, mAh/g)
  - Specific charge and discharge capacity normalized by active material mass
  - Internal resistance at SOC 100% and SOC 0% (Ohms)
  - Coulombic efficiency (%)
- Differential Capacity Analysis (dQ/dV):
  - Calculate and visualize differential capacity curves for charge and discharge
  - Identify electrochemical reactions and phase transitions
  - Multiple smoothing methods (Savitzky-Golay, Simple Moving Average, Weighted Moving Average, Exponential Moving Average)
  - Automatic detection of high C-rate discharge for optimal processing
- Plateau Analysis:
  - Extract plateau capacities from charge and discharge curves
  - Automatic inflection point detection using dV/dQ gradient analysis
  - Customizable voltage ranges for different battery chemistries
- Multi-cycle analysis supporting all available cycles in dataset
- Interactive graphical user interface for file selection and visualization
- Capacity curve visualization with matplotlib navigation toolbar (zoom, pan, save)
- dQ/dV curve visualization with both raw and smoothed data
- Automated performance data export to Excel with detailed feature extraction

## Installation

### Prerequisites

- Python 3.9
- Required Python packages (install via pip):
  ```
  pip install -r requirements.txt
  ```

### Setup

1. Clone this repository.

2. Create a `config.yaml` file in the root directory with the following structure:
   ```yaml
   data_path: "path/to/your/ndax/files"
   cell_database_path: "path/to/your/cell_database.xlsx"
   output_file: "extracted_features.xlsx"
   enable_plotting: true
   plots_directory: "plots"
   use_gui: true
   ```

3. Ensure you have a cell database Excel file that contains the cell ID as`Name/ID` 
and the active material mass as`Active mass (mg)` columns. If the cell database is 
not loaded correctly or does not contain the active mass for the Cell ID, the 
program will take the mass as 1 for calculating specific charge and discharge capacity.

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

#### Basic Parameters
- Charge and discharge capacities for all available cycles
- Internal resistance measurements at SOC 100% and 0%
- Coulombic efficiency for each cycle
- Specific capacities normalized by active material mass

#### Differential Capacity Analysis (dQ/dV)
The application includes advanced dQ/dV analysis capabilities:
- Automatically detects and processes electrochemical reactions
- Applies appropriate smoothing based on C-rate (skips smoothing for high C-rate discharge to preserve features)
- Supports multiple smoothing algorithms:
  - Savitzky-Golay filter for polynomial smoothing
  - Simple Moving Average (SMA) for basic smoothing
  - Weighted Moving Average (WMA) for emphasis on recent data
  - Exponential Moving Average (EMA) for trend-following
- Generates visualizations showing peaks that correspond to phase transitions

#### Plateau Analysis
- Extracts capacity contributions from distinct voltage plateaus
- Automatically detects inflection points using dV/dQ gradient analysis
- Supports customizable voltage ranges for different battery chemistries
- Calculates plateau capacities for both charge and discharge segments

Results are automatically saved to Excel files for further analysis.

## Code Structure

### Core Processing

- `main.py`: Application entry point and processing orchestration. Handles file loading, feature extraction, and result aggregation.
- `features.py`: Feature extraction classes for electrochemical parameters:
  - `Features`: Extracts charge/discharge capacities, internal resistance, and coulombic efficiency
  - `DQDVAnalysis`: Differential capacity analysis with multiple smoothing algorithms, plateau extraction, and inflection point detection
- `data_loader.py`: Efficient data loading and caching system for NDAX files
- `data_import.py`: Utilities for parsing and importing NDAX data files, cell ID extraction

### User Interface and Visualization

- `file_selector.py`: Tkinter GUI for interactive file selection, preview, and visualization
- `neware_plotter.py`: Matplotlib visualization components for capacity curves and dQ/dV plots

### Database and Configuration

- `cell_database.py`: Cell mass data management with Excel database integration and caching
- `constants.py`: Centralized definitions for Neware status strings and column names

### Utilities

- `logger_configurator.py`: Logging setup and configuration for debugging and monitoring
- `performance_stats.py`: Statistical analysis and performance metrics calculation

## Logging

The application maintains detailed logs in the `logs` directory. Each log file is timestamped and includes debug information about the processing steps.

## Troubleshooting

### Common Issues

- **Missing cell mass data**: Ensure your cell database has the correct format and cell IDs match between NDAX files and the database.
- **Plot display issues**: If plots don't display correctly, check that matplotlib is properly installed and configured.
- **File access errors**: Verify that the application has read/write permissions for all specified directories.

### Debugging

For more detailed debugging information, check the application logs in the `logs` directory.
