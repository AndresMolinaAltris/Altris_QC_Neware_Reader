from common.imports import plt, gridspec, os, logging, NewareNDA
from common.project_imports import CellDatabase, extract_cell_id


DEFAULT_CYCLES = [1, 2, 3]  # Default cycles to plot


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

    def preprocess_ndax_file_with_loader(self, data_loader, file_path, selected_cycles=None):
        """
        Updated version of preprocess_ndax_file that uses DataLoader instead of reading files.

        Args:
            data_loader: DataLoader instance with cached data
            file_path: Path to the NDAX file
            selected_cycles: List of cycles to process

        Returns:
            tuple: (filename_stem, processed_data) or (None, None) if failed
        """
        logging.debug("NEWARE_PLOTTER.preprocess_ndax_file_with_loader func started.")

        # Use default cycles if none provided
        cycles = selected_cycles if selected_cycles else DEFAULT_CYCLES

        # Check if file is loaded
        if not data_loader.is_loaded(file_path):
            logging.debug(f"NEWARE_PLOTTER.File not loaded in DataLoader: {os.path.basename(file_path)}")
            return None, None

        # Get cached data
        df = data_loader.get_data(file_path)
        if df is None:
            logging.debug(f"NEWARE_PLOTTER.No data available from DataLoader: {os.path.basename(file_path)}")
            return None, None

        filename_stem = os.path.basename(file_path).split(".")[0]

        # Prepare plot data
        plot_data = self._prepare_plot_data_from_dataframe(df, filename_stem, cycles)

        logging.debug("NEWARE_PLOTTER.preprocess_ndax_file_with_loader func finished.")
        return filename_stem, plot_data

    def create_plot(self, files_data, selected_cycles=None, display_plot=False):
        """
        Creates plots for the specified files and cycles with optimized legend placement.

        Generates a figure with three subplots (one for each cycle), showing
        voltage vs. specific capacity curves for both charge and discharge.
        Different files are represented with different colors.

        Args:
            files_data (dict): Dictionary mapping file names to processed DataFrames
                              containing voltage and capacity data
            selected_cycles (list, optional): List of cycles to plot. Defaults to [1, 2, 3].
            display_plot (bool): Whether to display the plot

        Returns:
            fig: The matplotlib figure object created
        """
        # Use default cycles if none provided
        cycles = selected_cycles if selected_cycles else DEFAULT_CYCLES

        # Ensure we have at most 3 cycles for plotting
        cycles = cycles[:3]

        # Find which cycles actually exist in the data
        existing_cycles = set()
        for file_name, data in files_data.items():
            if data is not None:
                existing_cycles.update(data['Cycle'].unique())

        # Filter cycles to only those that exist in at least one file
        valid_cycles = [cycle for cycle in cycles if cycle in existing_cycles]

        if not valid_cycles:
            logging.debug("NEWARE_PLOTTER.No valid cycles found in any file. Cannot create plot.")
            # Create an empty figure with a message
            fig = plt.figure(figsize=(15, 5))
            plt.figtext(0.5, 0.5, "No data available for selected cycles",
                        ha='center', va='center', fontsize=14)
            plt.tight_layout()
            return fig

        # Create a figure with a 2x2 grid - the top row will have up to 3 plots side by side,
        # and the bottom row will be used for the legend
        fig = plt.figure(figsize=(15, 5))  # Increased height slightly

        # Create a grid layout with more control
        gs = gridspec.GridSpec(2, 3, height_ratios=[4, 0.2])  # 2 rows, 3 columns, with top row 4x taller

        # Dictionary to store handles for the legend
        legend_handles = {}

        # Plot individual cycles
        for idx, cycle in enumerate(valid_cycles):  # Up to 3 valid cycles
            ax = fig.add_subplot(gs[0, idx])  # Place in top row

            for file_idx, (file_name, data) in enumerate(files_data.items()):
                if data is None or cycle not in data['Cycle'].unique():
                    # Skip this file/cycle combination if data doesn't exist
                    continue

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

        if sample_handles:  # Only create legend if we have data
            legend_ax.legend(handles=sample_handles, labels=sample_labels,
                             loc='center', ncol=len(sample_handles))

        plt.tight_layout()

        if display_plot:
            plt.show()

        return fig

    def plot_ndax_files_with_loader(self, data_loader, file_paths, display_plot=False,
                                    gui_callback=None, selected_cycles=None):
        """
        Process multiple NDAX files using DataLoader and create a combined plot.

        Args:
            data_loader: DataLoader instance with cached data
            file_paths (list): List of paths to NDAX files (for reference)
            display_plot (bool): Whether to display the plot
            gui_callback (callable, optional): Function to call with the figure for GUI display
            selected_cycles (list, optional): List of cycles to plot. Defaults to [1, 2, 3].

        Returns:
            fig: The matplotlib figure object
        """
        logging.debug("NEWARE_PLOTTER.plot_ndax_files_with_loader func started.")

        # Use default cycles if none provided
        cycles = selected_cycles if selected_cycles else DEFAULT_CYCLES

        # Process all files using DataLoader
        files_data = {}

        for file_path in file_paths:
            # Skip files that failed to load
            if not data_loader.is_loaded(file_path):
                logging.debug(f"NEWARE_PLOTTER.Skipping unloaded file: {os.path.basename(file_path)}")
                files_data[os.path.basename(file_path)] = None
                continue

            # Get cached data from DataLoader
            df = data_loader.get_data(file_path)
            if df is None:
                logging.debug(f"NEWARE_PLOTTER.No data available for: {os.path.basename(file_path)}")
                files_data[os.path.basename(file_path)] = None
                continue

            filename_stem = os.path.basename(file_path).split(".")[0]

            # Process data for plotting
            plot_data = self._prepare_plot_data_from_dataframe(df, filename_stem, cycles)

            if plot_data is not None:
                logging.debug(f"NEWARE_PLOTTER.Processed cached data for {filename_stem}")
                files_data[filename_stem] = plot_data
            else:
                files_data[filename_stem] = None

        if not any(data is not None for data in files_data.values()):
            logging.debug("NEWARE_PLOTTER.No valid data to plot.")
            # Create an empty figure with a message
            fig = plt.figure(figsize=(15, 5))
            plt.figtext(0.5, 0.5, "No data available for selected cycles",
                        ha='center', va='center', fontsize=14)
            if gui_callback:
                gui_callback(fig)
            return fig

        # Create plot
        fig = self.create_plot(files_data, selected_cycles=cycles, display_plot=display_plot)

        # If a GUI callback was provided, send the figure to it
        if gui_callback and fig is not None:
            gui_callback(fig)

        logging.debug("NEWARE_PLOTTER.plot_ndax_files_with_loader func finished")
        return fig

    def create_dqdv_plot(self, files_data, dqdv_data, selected_cycles=None, display_plot=False):
        """
        Creates plots for the specified files showing dQ/dV curves.

        Generates a figure with three subplots (one for each cycle), showing
        dQ/dV vs. voltage curves for both charge and discharge.
        Different files are represented with different colors.

        Args:
            files_data (dict): Dictionary mapping file names to processed DataFrames
            dqdv_data (dict): Dictionary containing dQ/dV data for each file and cycle
            selected_cycles (list, optional): List of cycles to plot. Defaults to [1, 2, 3].
            display_plot (bool): Whether to display the plot

        Returns:
            fig: The matplotlib figure object created
        """
        # Use default cycles if none provided
        cycles = selected_cycles if selected_cycles else DEFAULT_CYCLES

        # Ensure we have at most 3 cycles for plotting
        cycles = cycles[:3]

        # Create a figure with a 2x2 grid - the top row will have 3 plots side by side,
        # and the bottom row will be used for the legend
        fig = plt.figure(figsize=(15, 5))

        # Create a grid layout with more control
        gs = gridspec.GridSpec(2, 3, height_ratios=[4, 0.2])  # 2 rows, 3 columns, with top row 4x taller

        # Dictionary to store handles for the legend
        legend_handles = {}

        # Check if we have valid dQ/dV data for any file/cycle combination
        valid_dqdv_data = False

        # Plot individual cycles
        for idx, cycle in enumerate(cycles[:3]):  # Up to 3 individual cycles
            ax = fig.add_subplot(gs[0, idx])  # Place in top row

            has_data_for_cycle = False  # Track if this cycle has any data
            max_charge_dqdv = 0
            min_discharge_dqdv = 0

            # First pass to calculate y-axis limits
            for file_idx, (file_name, _) in enumerate(files_data.items()):
                if file_name in dqdv_data and cycle in dqdv_data[file_name]:
                    cycle_dqdv = dqdv_data[file_name][cycle]

                    if 'charge' in cycle_dqdv and cycle_dqdv['charge'] is not None:
                        charge_data = cycle_dqdv['charge']
                        max_charge_dqdv = max(max_charge_dqdv, charge_data['smoothed_dqdv'].max())
                        has_data_for_cycle = True
                        valid_dqdv_data = True

                    if 'discharge' in cycle_dqdv and cycle_dqdv['discharge'] is not None:
                        discharge_data = cycle_dqdv['discharge']
                        min_discharge_dqdv = min(min_discharge_dqdv, -abs(discharge_data['smoothed_dqdv'].min()))
                        has_data_for_cycle = True
                        valid_dqdv_data = True

            # Second pass to actually plot
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
                                linestyle=self.line_styles[0], color=color,
                                label=f"{legend_name} (Discharge)")

                    # Add to legend handles
                    if legend_name not in legend_handles:
                        legend_handles[legend_name] = ax.plot([], [], color=color, label=legend_name)[0]

            # Set labels and title even if no data (for consistency)
            ax.set_xlabel("Voltage (V)")
            ax.set_ylabel("dQ/dV (mAh/g·V)")
            ax.set_title(f"Cycle {cycle}")
            ax.grid(True)

            # Set axis limits if we have data
            if has_data_for_cycle:
                #ax.set_xlim(2.75, 3.75)
                ax.set_xlim(2.8, 3.6)
                # Ensure we don't have zero division issues
                if max_charge_dqdv > 0 or min_discharge_dqdv < 0:
                    max_y = max(0.1, max_charge_dqdv * 1.1)  # Always at least 0.1 for non-zero scale
                    min_y = min(-0.1, min_discharge_dqdv * 1.1)
                    ax.set_ylim(bottom=min_y, top=max_y)
            else:
                # No data for this cycle, add a message
                ax.text(0.5, 0.5, f"No data for Cycle {cycle}",
                        ha='center', va='center', transform=ax.transAxes)

        # Create a legend axis spanning the bottom row
        legend_ax = fig.add_subplot(gs[1, :])
        legend_ax.axis('off')  # Hide the axis

        # Add legend with sample names to the dedicated legend axis
        sample_handles = list(legend_handles.values())
        sample_labels = list(legend_handles.keys())

        if sample_handles:  # Only create legend if we have data
            legend_ax.legend(handles=sample_handles, labels=sample_labels,
                             loc='center', ncol=len(sample_handles))

        plt.tight_layout()

        if display_plot:
            plt.show()

        # If no valid data was found, add a message to the figure
        if not valid_dqdv_data:
            plt.figtext(0.5, 0.5, "No dQ/dV data available for selected cycles",
                        ha='center', va='center', fontsize=14)

        return fig

    def plot_dqdv_curves_with_loader(self, data_loader, file_paths, dqdv_data=None,
                                     display_plot=False, gui_callback=None, selected_cycles=None):
        """
        Process multiple NDAX files using DataLoader and create a combined dQ/dV plot.

        Args:
            data_loader: DataLoader instance with cached data
            file_paths (list): List of paths to NDAX files
            dqdv_data (dict, optional): Pre-processed dQ/dV data
            display_plot (bool): Whether to display the plot
            gui_callback (callable, optional): Function to call with the figure for GUI display
            selected_cycles (list, optional): List of cycles to plot. Defaults to [1, 2, 3].

        Returns:
            fig: The matplotlib figure object
        """
        logging.debug("NEWARE_PLOTTER.plot_dqdv_curves_with_loader func started.")

        # Use default cycles if none provided
        cycles = selected_cycles if selected_cycles else DEFAULT_CYCLES

        # Get all files data for consistency (we just need the file names for plotting)
        files_data = {}
        for file_path in file_paths:
            filename_stem = os.path.basename(file_path).split(".")[0]
            if data_loader.is_loaded(file_path):
                files_data[filename_stem] = None  # We just need the file names for dQ/dV plotting
            else:
                logging.debug(f"NEWARE_PLOTTER.Skipping unloaded file for dQ/dV: {filename_stem}")

        # If no valid data, exit early
        if not files_data:
            logging.debug("NEWARE_PLOTTER.No valid data to plot dQ/dV curves.")
            return None

        # Create the dQ/dV plot
        fig = self.create_dqdv_plot(files_data, dqdv_data, selected_cycles=cycles, display_plot=display_plot)

        # If a GUI callback was provided, send the figure to it
        if gui_callback and fig is not None:
            gui_callback(fig)

        logging.debug("NEWARE_PLOTTER.plot_dqdv_curves_with_loader func finished")
        return fig

    def _prepare_plot_data_from_dataframe(self, df, filename_stem, selected_cycles):
        """
        Prepare plot data from a cached DataFrame instead of reading from file.

        Args:
            df: Cached DataFrame from DataLoader
            filename_stem: Filename stem for cell ID extraction
            selected_cycles: List of cycles to include

        Returns:
            Processed DataFrame ready for plotting, or None if no valid data
        """
        logging.debug(f"NEWARE_PLOTTER._prepare_plot_data_from_dataframe started for {filename_stem}")

        try:
            # Extract cell ID from the filename
            cell_id = extract_cell_id(filename_stem)

            # Get active mass from database
            mass = self.db.get_mass(cell_id)
            if mass is None:
                logging.debug(f"NEWARE_PLOTTER.Warning: No mass found for cell ID {cell_id}, using 1.0g")
                mass = 1.0

            # Filter relevant columns for plotting
            plot_data = df[['Cycle', 'Status', 'Voltage', 'Charge_Capacity(mAh)', 'Discharge_Capacity(mAh)']].copy()

            # Filter data for selected cycles that exist in the data
            available_cycles = plot_data['Cycle'].unique()
            valid_cycles = [cycle for cycle in selected_cycles if cycle in available_cycles]

            if not valid_cycles:
                logging.debug(
                    f"NEWARE_PLOTTER.Warning: None of the selected cycles {selected_cycles} exist in file {filename_stem}.")
                return None

            # Filter to only include valid cycles
            plot_data = plot_data[plot_data['Cycle'].isin(valid_cycles)]

            # Compute specific capacities
            plot_data['Specific_Charge_Capacity(mAh/g)'] = plot_data['Charge_Capacity(mAh)'] / mass
            plot_data['Specific_Discharge_Capacity(mAh/g)'] = plot_data['Discharge_Capacity(mAh)'] / mass

            logging.debug(f"NEWARE_PLOTTER.Data prepared successfully for plotting: {filename_stem}")
            return plot_data

        except Exception as e:
            logging.debug(f"NEWARE_PLOTTER.Error preparing plot data for {filename_stem}: {e}")
            return None

