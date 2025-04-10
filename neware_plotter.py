from common.imports import plt, gridspec, os, logging, NewareNDA
from common.project_imports import CellDatabase, extract_cell_id

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

    def cleanup_plot_resources(self):
        """Clean up matplotlib resources to prevent memory leaks."""
        logging.debug("NEWARE_PLOTTER. Cleaning up matplotlib resources.")
        try:
            plt.close('all')
            logging.debug("NEWARE_PLOTTER. All matplotlib figures closed.")
        except Exception as e:
            logging.debug(f"NEWARE_PLOTTER. Error cleaning up matplotlib: {e}")

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

    def preprocess_ndax_file(self, file_path):
        """
        Reads an NDAX file and prepares it for plotting, reusing the existing
        data processing code from the Features class.

        Args:
            file_path (str): Path to the NDAX file
        Returns:
            tuple: (file_name, DataFrame) containing the processed data
        """

        logging.debug("NEWARE_PLOTTER.preprocess_ndax_files func started.")
        cycles = SELECTED_CYCLES

        try:
            logging.debug(f"NEWARE_PLOTTER.Processing file for plotting: {file_path}...")
            # Extract cell ID from the filename
            filename_stem = os.path.basename(file_path).split(".")[0]
            cell_id = extract_cell_id(filename_stem)

            # Get active mass from database
            mass = self.db.get_mass(cell_id)
            if mass is None:
                logging.debug(f"NEWARE_PLOTTER.Warning: No mass found for cell ID {cell_id}, using 1.0g")
                mass = 1.0

            # Read data
            data = NewareNDA.read(file_path)

            # Filter relevant columns for plotting
            plot_data = data[['Cycle', 'Status', 'Voltage', 'Charge_Capacity(mAh)', 'Discharge_Capacity(mAh)']]
            plot_data = plot_data[plot_data['Cycle'].isin(cycles)]

            # Compute specific capacities
            plot_data['Specific_Charge_Capacity(mAh/g)'] = plot_data['Charge_Capacity(mAh)'] / mass
            plot_data['Specific_Discharge_Capacity(mAh/g)'] = plot_data['Discharge_Capacity(mAh)'] / mass

            logging.debug(f"NEWARE_PLOTTER.File processed successfully for plotting: {file_path}")

            return filename_stem, plot_data

        except Exception as e:
            logging.debug(f"NEWARE_PLOTTER.Error processing file for plotting {file_path}: {e}")
            return None, None

    def create_plot(self, files_data, display_plot=False):
        """
        Creates plots for the specified files and cycles with optimized legend placement.

        Generates a figure with three subplots (one for each cycle), showing
        voltage vs. specific capacity curves for both charge and discharge.
        Different files are represented with different colors.

        Args:
            files_data (dict): Dictionary mapping file names to processed DataFrames
                              containing voltage and capacity data
            display_plot (bool): Whether to display the plot

        Returns:
            fig: The matplotlib figure object created
        """
        #if cycles is None:
        cycles = SELECTED_CYCLES

        # Create a figure with a 2x2 grid - the top row will have 3 plots side by side,
        # and the bottom row will be used for the legend
        fig = plt.figure(figsize=(15, 5))  # Increased height slightly

        # Create a grid layout with more control
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

        if display_plot:
            plt.show()

        return fig

    def plot_ndax_files(self, file_paths, preprocessed_data=None, display_plot=False, gui_callback=None):
        """
        Process multiple NDAX files and create a combined plot.

        Args:
            file_paths (list): List of paths to NDAX files
            preprocessed_data (dict, optional): Pre-processed data to use instead of reading files
            display_plot (bool): Whether to display the plot
            gui_callback (callable, optional): Function to call with the figure for GUI display

        Returns:
            fig: The matplotlib figure object
        """
        logging.debug("NEWARE_PLOTTER.plot_ndax_files func started.")
        cycles = SELECTED_CYCLES

        # Process all files
        files_data = {}

        # If we have preprocessed data, use it
        if preprocessed_data:
            logging.debug("NEWARE_PLOTTER.plot_ndax_files using preprocessed data")
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

                logging.debug(f"NEWARE_PLOTTER.Processed cached data for {file_name}")
                files_data[file_name] = plot_data
        else:
            # Process files normally if no preprocessed data
            logging.debug("NEWARE_PLOTTER.plot_ndax_files no preprocessed data, reading files")
            for file_path in file_paths:
                file_name, processed_data = self.preprocess_ndax_file(file_path)
                if processed_data is not None:
                    logging.debug(f"NEWARE_PLOTTER.Processed file: {file_name}")
                    files_data[file_name] = processed_data

        if not files_data:
            logging.debug("NEWARE_PLOTTER.No valid data to plot.")
            return None

        # Create plot
        fig = self.create_plot(files_data, display_plot)

        # If a GUI callback was provided, send the figure to it
        if gui_callback and fig is not None:
            gui_callback(fig)

        logging.debug("NEWARE_PLOTTER.plot_ndax_files func finished")
        return fig

    def create_dqdv_plot(self, files_data, dqdv_data, display_plot=False):
        """
        Creates plots for the specified files showing dQ/dV curves.

        Generates a figure with three subplots (one for each cycle), showing
        dQ/dV vs. voltage curves for both charge and discharge.
        Different files are represented with different colors.

        Args:
            files_data (dict): Dictionary mapping file names to processed DataFrames
            dqdv_data (dict): Dictionary containing dQ/dV data for each file and cycle
            display_plot (bool): Whether to display the plot

        Returns:
            fig: The matplotlib figure object created
        """
        cycles = SELECTED_CYCLES

        # Create a figure with a 2x2 grid - the top row will have 3 plots side by side,
        # and the bottom row will be used for the legend
        fig = plt.figure(figsize=(15, 5))

        # Create a grid layout with more control
        gs = gridspec.GridSpec(2, 3, height_ratios=[4, 0.2])  # 2 rows, 3 columns, with top row 4x taller

        # Dictionary to store handles for the legend
        legend_handles = {}

        # Plot individual cycles
        for idx, cycle in enumerate(cycles[:3]):  # Up to 3 individual cycles
            ax = fig.add_subplot(gs[0, idx])  # Place in top row

            for file_idx, (file_name, _) in enumerate(files_data.items()):
                color = self.colors[file_idx % len(self.colors)]
                legend_name = self.extract_legend_name(file_name)

                # Get dQ/dV data for this file and cycle if available
                if file_name in dqdv_data and cycle in dqdv_data[file_name]:
                    cycle_dqdv = dqdv_data[file_name][cycle]

                    # Plot charge data if available
                    if 'charge' in cycle_dqdv and cycle_dqdv['charge'] is not None:
                        charge_data = cycle_dqdv['charge']
                        ax.plot(charge_data['voltage'], charge_data['smoothed_dqdv'],
                                linestyle=self.line_styles[0], color=color,
                                label=f"{legend_name} (Charge)")

                    # Plot discharge data if available
                    if 'discharge' in cycle_dqdv and cycle_dqdv['discharge'] is not None:
                        discharge_data = cycle_dqdv['discharge']
                        discharge_dqdv = -abs(discharge_data['smoothed_dqdv'])
                        ax.plot(discharge_data['voltage'], discharge_dqdv,
                                linestyle=self.line_styles[1], color=color,
                                label=f"{legend_name} (Discharge)")

                    # Add to legend handles
                    if legend_name not in legend_handles:
                        legend_handles[legend_name] = ax.plot([], [], color=color, label=legend_name)[0]

                ax.set_xlabel("Voltage (V)")
                ax.set_ylabel("dQ/dV (mAh/g·V)")
                ax.set_title(f"Cycle {cycle}")
                ax.grid(True)
                ax.set_xlim(2.75, 3.75)
                ax.set_ylim(bottom=-max(abs(discharge_dqdv)) * 1.1, top=max(charge_data['smoothed_dqdv']) * 1.1)

        # Create a legend axis spanning the bottom row
        legend_ax = fig.add_subplot(gs[1, :])
        legend_ax.axis('off')  # Hide the axis

        # Add legend with sample names to the dedicated legend axis
        sample_handles = list(legend_handles.values())
        sample_labels = list(legend_handles.keys())

        legend_ax.legend(handles=sample_handles, labels=sample_labels,
                         loc='center', ncol=len(sample_handles))

        plt.tight_layout()

        if display_plot:
            plt.show()

        return fig

    def plot_dqdv_curves(self, file_paths, dqdv_data=None, display_plot=False, gui_callback=None):
        """
        Process multiple NDAX files and create a combined dQ/dV plot.

        Args:
            file_paths (list): List of paths to NDAX files
            dqdv_data (dict, optional): Pre-processed dQ/dV data
            display_plot (bool): Whether to display the plot
            gui_callback (callable, optional): Function to call with the figure for GUI display

        Returns:
            fig: The matplotlib figure object
        """
        logging.debug("NEWARE_PLOTTER.plot_dqdv_curves func started.")

        # Get all files data first for consistency
        files_data = {}
        for file_path in file_paths:
            file_name, _ = self.preprocess_ndax_file(file_path)
            if file_name is not None:
                files_data[file_name] = None  # We just need the file names for plotting

        # If no valid data, exit early
        if not files_data:
            logging.debug("NEWARE_PLOTTER.No valid data to plot dQ/dV curves.")
            return None

        # Create the dQ/dV plot
        fig = self.create_dqdv_plot(files_data, dqdv_data, display_plot)

        # If a GUI callback was provided, send the figure to it
        if gui_callback and fig is not None:
            gui_callback(fig)

        logging.debug("NEWARE_PLOTTER.plot_dqdv_curves func finished")
        return fig