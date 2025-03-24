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
        sample_name = None
        parts = file_name.split('_')
        if len(parts) > 1:
            sample_name = parts[0]
        return sample_name or file_name

    def preprocess_ndax_file(self, file_path, cycles=None):
        """
        Reads an NDAX file, filters for specified cycles, and computes specific capacities.

        Args:
            file_path (str): Path to the NDAX file
            cycles (list, optional): List of cycle numbers to include

        Returns:
            tuple: (file_name, DataFrame) containing the processed data
        """
        if cycles is None:
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

            # Filter relevant columns and rows
            data = data[['Cycle', 'Status', 'Voltage', 'Charge_Capacity(mAh)', 'Discharge_Capacity(mAh)']]
            data = data[data['Cycle'].isin(cycles)]

            # Compute specific capacities
            data['Specific_Charge_Capacity(mAh/g)'] = data['Charge_Capacity(mAh)'] / mass
            data['Specific_Discharge_Capacity(mAh/g)'] = data['Discharge_Capacity(mAh)'] / mass

            print(f"File processed successfully for plotting: {file_path}")
            return filename_stem, data

        except Exception as e:
            print(f"Error processing file for plotting {file_path}: {e}")
            return None, None

    def create_plot(self, files_data, cycles=None, save_dir=None):
        """
        Creates plots for the specified files and cycles.

        Args:
            files_data (dict): Dictionary mapping file names to processed DataFrames
            cycles (list, optional): List of cycle numbers to plot
            save_dir (str, optional): Directory to save plot images to

        Returns:
            list: Paths to the saved plot files
        """
        if cycles is None:
            cycles = SELECTED_CYCLES

        saved_files = []

        # Create a 2x2 grid of plots (3 individual cycles + combined)
        fig, axs = plt.subplots(2, 2, figsize=(12, 8))
        axs = axs.flatten()

        # Dictionary to store handles for the legend
        legend_handles = {}

        # Plot individual cycles
        for idx, cycle in enumerate(cycles[:3]):  # Up to 3 individual cycles
            ax = axs[idx]

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

        # Combined plot (all cycles)
        ax_combined = axs[3]

        for file_idx, (file_name, data) in enumerate(files_data.items()):
            color = self.colors[file_idx % len(self.colors)]
            legend_name = self.extract_legend_name(file_name)

            for cycle_idx, cycle in enumerate(cycles):
                line_style = self.line_styles[cycle_idx % len(self.line_styles)]

                cycle_data = data[data['Cycle'] == cycle]
                charge_data = cycle_data[cycle_data['Status'] == 'CC_Chg']
                discharge_data = cycle_data[cycle_data['Status'] == 'CC_DChg']

                if not charge_data.empty:
                    ax_combined.plot(charge_data['Specific_Charge_Capacity(mAh/g)'], charge_data['Voltage'],
                                     linestyle=line_style, color=color)

                if not discharge_data.empty:
                    ax_combined.plot(discharge_data['Specific_Discharge_Capacity(mAh/g)'], discharge_data['Voltage'],
                                     linestyle=line_style, color=color)

        ax_combined.set_xlabel("Specific Capacity (mAh/g)")
        ax_combined.set_ylabel("Voltage (V)")
        ax_combined.set_title("All Cycles Combined")
        ax_combined.grid(True)
        ax_combined.set_xlim(left=0)

        # Add legend with both sample names and cycle numbers
        sample_handles = list(legend_handles.values())
        sample_labels = list(legend_handles.keys())

        # Add cycle line style legend entries
        cycle_handles = []
        cycle_labels = []
        for idx, cycle in enumerate(cycles):
            if idx < len(self.line_styles):
                handle = plt.Line2D([0], [0], color='black',
                                    linestyle=self.line_styles[idx], label=f'Cycle {cycle}')
                cycle_handles.append(handle)
                cycle_labels.append(f'Cycle {cycle}')

        # Place legend below the plots
        all_handles = sample_handles + cycle_handles
        all_labels = sample_labels + cycle_labels
        fig.legend(handles=all_handles, labels=all_labels,
                   loc='lower center', ncol=len(all_handles), bbox_to_anchor=(0.5, 0.02))

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.15)  # Make room for the legend

        # Save figure if a directory is provided
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
            save_path = os.path.join(save_dir, f'capacity_plot_{timestamp}.png')
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            saved_files.append(save_path)
            print(f"Plot saved to: {save_path}")

        plt.show()
        return saved_files

    def plot_ndax_files(self, file_paths, cycles=None, save_dir=None):
        """
        Process and plot multiple NDAX files.

        Args:
            file_paths (list): List of paths to NDAX files
            cycles (list, optional): List of cycle numbers to plot
            save_dir (str, optional): Directory to save plot images to

        Returns:
            list: Paths to the saved plot files
        """
        if cycles is None:
            cycles = SELECTED_CYCLES

        # Process all files
        files_data = {}
        for file_path in file_paths:
            file_name, processed_data = self.preprocess_ndax_file(file_path, cycles)
            if processed_data is not None:
                files_data[file_name] = processed_data

        if not files_data:
            print("No valid data to plot.")
            return []

        # Create and save plots
        return self.create_plot(files_data, cycles, save_dir)


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