import pandas as pd
import matplotlib.pyplot as plt
import os
import NewareNDA
from cell_database import CellDatabase
from data_import import extract_cell_id

# Constants for plotting
SELECTED_CYCLES = [1, 2, 3]  # Default cycles to plot, can be changed by user


class NewarePlotter:
    """Class for creating plots from Neware NDAX files."""

    def __init__(self, db=None):
        """
        Initialize the plotter with an optional database instance.

        Args:
            db (CellDatabase, optional): Instance of CellDatabase for mass lookup.
                If None, will get the singleton instance.
        """
        if db is None:
            self.db = CellDatabase.get_instance()
        else:
            self.db = db

        # Define color and line style schemes
        self.colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'cyan', 'magenta']
        self.line_styles = ['-', '--', '-.']

    def extract_legend_name(self, file_name):
        """
        Extracts a legend name from the file name.

        Args:
            file_name (str): The file name to extract from

        Returns:
            str: Legend name for the plot
        """
        # Using the sample name as the legend
        # sample_name = None
        parts = file_name.split('_')
        sample_name = parts[0]

        return sample_name

    def preprocess_ndax_file(self, file_path, cycles=None):
        """
        Reads an NDAX file and prepares it for plotting, reusing the existing
        data processing code from the Features class.

        Args:
            file_path (str): Path to the NDAX file
            cycles (list, optional): List of cycle numbers to include

        Returns:
            tuple: (file_name, DataFrame) containing the processed data
        """

        cycles = SELECTED_CYCLES

        try:
            print(f"Processing file for plotting: {file_path}...")
            # Extract cell ID from the filename
            filename_stem = os.path.basename(file_path).split(".")[0]
            cell_id = extract_cell_id(filename_stem)

            # Get active mass from database
            mass = self.db.get_mass(cell_id)
            if mass is None:
                print(f"Warning: No mass found for cell ID {cell_id}, using 1.0g")
                mass = 1.0

            # Read data
            data = NewareNDA.read(file_path)

            # Filter relevant columns for plotting
            plot_data = data[['Cycle', 'Status', 'Voltage', 'Charge_Capacity(mAh)', 'Discharge_Capacity(mAh)']]
            plot_data = plot_data[plot_data['Cycle'].isin(cycles)]

            # Compute specific capacities
            plot_data['Specific_Charge_Capacity(mAh/g)'] = plot_data['Charge_Capacity(mAh)'] / mass
            plot_data['Specific_Discharge_Capacity(mAh/g)'] = plot_data['Discharge_Capacity(mAh)'] / mass

            print(f"File processed successfully for plotting: {file_path}")
            return filename_stem, plot_data

        except Exception as e:
            print(f"Error processing file for plotting {file_path}: {e}")
            return None, None

    def create_plot(self, files_data, cycles=None, save_dir=None, display_plot=False):
        """
        Creates plots for the specified files and cycles with optimized legend placement.

        Generates a figure with three subplots (one for each cycle), showing
        voltage vs. specific capacity curves for both charge and discharge.
        Different files are represented with different colors.

        Args:
            files_data (dict): Dictionary mapping file names to processed DataFrames
                              containing voltage and capacity data
            cycles (list, optional): List of cycle numbers to plot, defaults to [1, 2, 3]
            save_dir (str, optional): Directory to save the generated plot.
                                     If None, plot is only displayed.

        Returns:
            list: Paths to the saved plot files, or empty list if no plots were saved
        """
        if cycles is None:
            cycles = SELECTED_CYCLES

        saved_files = []

        # Create a figure with a 2x2 grid - the top row will have 3 plots side by side,
        # and the bottom row will be used for the legend
        fig = plt.figure(figsize=(15, 5))  # Increased height slightly

        # Create a grid layout with more control
        import matplotlib.gridspec as gridspec
        gs = gridspec.GridSpec(2, 3, height_ratios=[4, 0.2])  # 2 rows, 3 columns, with top row 4x taller

        # Dictionary to store handles for the legend
        legend_handles = {}

        # Plot individual cycles
        for idx, cycle in enumerate(cycles[:3]):  # Up to 3 individual cycles
            ax = fig.add_subplot(gs[0, idx])  # Place in top row

            for file_idx, (file_name, data) in enumerate(files_data.items()):
                color = self.colors[file_idx % len(self.colors)]
                legend_name = self.extract_legend_name(file_name)

                # Filter data for the current cycle
                cycle_data = data[data['Cycle'] == cycle]
                charge_data = cycle_data[cycle_data['Status'] == 'CC_Chg']
                discharge_data = cycle_data[cycle_data['Status'] == 'CC_DChg']

                if not charge_data.empty:
                    ax.plot(charge_data['Specific_Charge_Capacity(mAh/g)'], charge_data['Voltage'],
                            linestyle=self.line_styles[0], color=color)

                if not discharge_data.empty:
                    ax.plot(discharge_data['Specific_Discharge_Capacity(mAh/g)'], discharge_data['Voltage'],
                            linestyle=self.line_styles[0], color=color)

                # Add to legend handles
                if legend_name not in legend_handles:
                    legend_handles[legend_name] = ax.plot([], [], color=color, label=legend_name)[0]

            ax.set_xlabel("Specific Capacity (mAh/g)")
            ax.set_ylabel("Voltage (V)")
            ax.set_title(f"Cycle {cycle}")
            ax.grid(True)
            ax.set_xlim(left=0)

        # Create a legend axis spanning the bottom row
        legend_ax = fig.add_subplot(gs[1, :])
        legend_ax.axis('off')  # Hide the axis

        # Add legend with sample names to the dedicated legend axis
        sample_handles = list(legend_handles.values())
        sample_labels = list(legend_handles.keys())

        legend_ax.legend(handles=sample_handles, labels=sample_labels,
                         loc='center', ncol=len(sample_handles))

        plt.tight_layout()

        # Save figure if a directory is provided. Filename with timestamp.
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
            save_path = os.path.join(save_dir, f'capacity_plot_{timestamp}.png')
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            saved_files.append(save_path)
            print(f"Plot saved to: {save_path}")

        if display_plot:
            plt.show()
        else:
            plt.close(fig)

        return fig, saved_files


    def plot_ndax_files(self, file_paths, cycles=None, save_dir=None, preprocessed_data=None,
                        display_plot=False, gui_callback=None):

        if cycles is None:
            cycles = SELECTED_CYCLES

        # Process all files
        files_data = {}

        # If we have preprocessed data, use it
        if preprocessed_data:
            for file_name, data in preprocessed_data.items():
                # Filter data for plotting
                plot_data = data[['Cycle', 'Status', 'Voltage', 'Charge_Capacity(mAh)', 'Discharge_Capacity(mAh)']]
                plot_data = plot_data[plot_data['Cycle'].isin(cycles)]

                # Get cell ID and mass
                cell_id = extract_cell_id(file_name)
                mass = self.db.get_mass(cell_id) or 1.0

                # Compute specific capacities if they don't already exist
                if 'Specific_Charge_Capacity(mAh/g)' not in plot_data.columns:
                    plot_data['Specific_Charge_Capacity(mAh/g)'] = plot_data['Charge_Capacity(mAh)'] / mass

                if 'Specific_Discharge_Capacity(mAh/g)' not in plot_data.columns:
                    plot_data['Specific_Discharge_Capacity(mAh/g)'] = plot_data['Discharge_Capacity(mAh)'] / mass

                files_data[file_name] = plot_data
        else:
            # Process files normally if no preprocessed data
            for file_path in file_paths:
                file_name, processed_data = self.preprocess_ndax_file(file_path, cycles)
                if processed_data is not None:
                    files_data[file_name] = processed_data

        if not files_data:
            print("No valid data to plot.")
            return []

        # Create and save plots
        fig, saved_files = self.create_plot(files_data, cycles, save_dir, display_plot)

        # If a GUI callback was provided, send the figure to it
        if gui_callback and fig is not None:
            gui_callback(fig)

        #return self.create_plot(files_data, cycles, save_dir)
        return fig, saved_files


# Example usage
if __name__ == "__main__":
    plotter = NewarePlotter()

    # Example: Select files and plot them
    from tkinter import Tk, filedialog

    Tk().withdraw()
    file_paths = filedialog.askopenfilenames(title="Select NDAX Files", filetypes=[("NDAX Files", "*.ndax")])

    if file_paths:
        # Initialize and load database if needed
        db = CellDatabase.get_instance()
        if not db._is_loaded:
            db_path = filedialog.askopenfilename(title="Select Cell Database", filetypes=[("Excel Files", "*.xlsx")])
            if db_path:
                db.load_database(db_path)
            else:
                print("No database selected, using mass=1.0g for all cells")

        # Plot the files
        plotter.plot_ndax_files(file_paths, save_dir="./plots")
    else:
        print("No files selected.")