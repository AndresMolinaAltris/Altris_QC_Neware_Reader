from common.imports import (
    tk, filedialog, ttk, messagebox, os, pd,
    logging, FigureCanvasTkAgg, Figure, plt
)
#from common.project_imports import DataLoader
from data_loader import DataLoader # For some reason I cannot import this from common imports

class CycleSelectionDialog(tk.Toplevel):
    """Dialog for selecting which cycles to display in plots and analysis."""

    def __init__(self, parent, current_cycles):
        super().__init__(parent)
        self.title("Set Display Cycles")
        self.transient(parent)  # Make dialog modal
        self.grab_set()

        self.result = None
        self.current_cycles = current_cycles

        # Set up the dialog window
        self.geometry("300x200")
        self.resizable(False, False)

        self._create_widgets()

        # Center the dialog
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")

        # Handle window close event
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        # Wait for window to be destroyed
        self.wait_window(self)

    def _create_widgets(self):
        """Create the widgets for the dialog."""
        # Main frame
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Label
        ttk.Label(main_frame, text="Select 3 cycles to display:").pack(pady=(0, 10))

        # Create frame for cycle selection
        cycle_frame = ttk.Frame(main_frame)
        cycle_frame.pack(fill=tk.X, pady=5)

        # Add cycle selection dropdowns
        self.cycle_vars = []
        labels = ["First plot:", "Second plot:", "Third plot:"]

        for i, label in enumerate(labels):
            row_frame = ttk.Frame(cycle_frame)
            row_frame.pack(fill=tk.X, pady=2)

            ttk.Label(row_frame, text=label, width=10).pack(side=tk.LEFT, padx=(0, 5))

            var = tk.IntVar(value=self.current_cycles[i])
            self.cycle_vars.append(var)

            # Dropdown with values 1-10
            dropdown = ttk.Combobox(row_frame, textvariable=var, width=5)
            dropdown['values'] = list(range(1, 11))  # Cycles 1-10
            dropdown.pack(side=tk.LEFT)

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # Reset button
        ttk.Button(button_frame, text="Reset to Default",
                   command=self._reset_defaults).pack(side=tk.LEFT, padx=(0, 5))

        # OK and Cancel buttons
        ttk.Button(button_frame, text="OK", command=self._ok).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Cancel", command=self._cancel).pack(side=tk.RIGHT, padx=5)

    def _reset_defaults(self):
        """Reset to default cycles (1, 2, 3)."""
        for i, var in enumerate(self.cycle_vars):
            var.set(i + 1)

    def _ok(self):
        """Process the selection and close the dialog."""
        self.result = [var.get() for var in self.cycle_vars]
        self.destroy()

    def _cancel(self):
        """Cancel the selection and close the dialog."""
        self.result = None
        self.destroy()


class FileSelector:
    """A GUI for selecting and processing .ndax files with preview functionality."""

    def __init__(self, initial_dir=None, default_output_file=None):
        """Initialize the file selector with an optional starting directory."""
        self.initial_dir = initial_dir or os.getcwd()
        self.default_output_file = default_output_file or "specific_capacity_results.xlsx"
        self.selected_files = []
        self.root = None
        self.listbox = None
        self.selected_listbox = None
        self.status_var = None
        self.current_dir = None
        self.fig = None
        self.canvas = None
        self.selected_cycles = [1, 2, 3]  # Default cycles to display

    def _open_cycle_selection(self):
        """Open dialog to select which cycles to display."""
        dialog = CycleSelectionDialog(self.root, self.selected_cycles)

        if dialog.result:  # If user clicked OK
            # Store the previous cycles to check if they changed
            previous_cycles = self.selected_cycles.copy()

            # Update to new cycles
            self.selected_cycles = dialog.result

            # Update status to show selected cycles
            cycle_text = ", ".join(str(c) for c in self.selected_cycles)
            self.status_var.set(f"Selected cycles: {cycle_text}")

            # Update table columns if they changed
            if previous_cycles != self.selected_cycles:
                self._update_table_columns()

            # If files are already selected, reprocess to update the plots
            if self.selected_files:
                self._process_files(self._last_callback)

    def show_interface(self, process_callback=None):
        """
        Display the file selector interface and handle file selection/processing.
        """
        # Create and configure the main window
        self.root = tk.Tk()
        self.root.title("Neware NDAX File Selector")
        self.root.geometry("1000x800")  # Increased height
        self.root.minsize(900, 750)  # Minimum width and height

        # Register cleanup for window close via the X button
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)

        # Initialize variables
        self.selected_files = []
        self.current_dir = tk.StringVar(value=self.initial_dir)
        self.status_var = tk.StringVar(value="No files selected")
        self._last_callback = None  # Store the callback for later reprocessing

        # Configure grid layout
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0)  # Directory selector row
        self.root.rowconfigure(1, weight=0)  # Tabs row (new)
        self.root.rowconfigure(2, weight=1)  # Content area (contains the notebook)

        # Create the directory selector in row 0
        dir_frame = ttk.Frame(self.root)
        dir_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        ttk.Label(dir_frame, text="Directory:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(dir_frame, textvariable=self.current_dir, width=60).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(dir_frame, text="Browse...", command=self._browse_directory).pack(side=tk.LEFT)

        # Create notebook (tabbed interface) in row 1
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=10, pady=5)

        # Create first tab - "Charge vs Voltage Plot"
        self.plot_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.plot_tab, text="Charge vs Voltage Plot")

        # Configure the plot tab grid
        self.plot_tab.columnconfigure(0, weight=1)
        self.plot_tab.rowconfigure(0, weight=1)  # File lists row
        self.plot_tab.rowconfigure(1, weight=2)  # Plot area row
        self.plot_tab.rowconfigure(2, weight=0)  # Buttons row

        # Create second tab - "Specific capacity results"
        self.analysis_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.analysis_tab, text="Specific capacity results")

        # For now, just add a label to the second tab
        ttk.Label(self.analysis_tab, text="Analysis will appear here after processing files.").pack(padx=20, pady=20)

        # Create the differential capacity tab
        self.dqdv_tab = self._create_dqdv_tab()
        self.notebook.add(self.dqdv_tab, text="Differential Capacity")

        # Move existing components into the first tab
        # Create file lists frame in the plot tab
        file_frame = ttk.Frame(self.plot_tab)
        file_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=5)
        file_frame.grid_propagate(False)  # Prevent frame from resizing based on content
        file_frame.config(height=200)  # Fixed height for file lists section
        self._create_file_lists(file_frame)

        # Create plot area in the plot tab
        plot_frame = ttk.LabelFrame(self.plot_tab, text="Plot Preview")
        plot_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=5)
        plot_frame.grid_propagate(False)
        plot_frame.config(height=400)
        self._create_plot_area(plot_frame)
        self.plot_frame = plot_frame  # Store reference to plot frame

        # Create buttons in the plot tab
        button_frame = ttk.Frame(self.plot_tab)
        button_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=10)

        ttk.Label(button_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Export Raw Data",
                   command=self._export_raw_data).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Exit",
                   command=self._exit_application).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Clear Selection",
                   command=self._clear_selection).pack(side=tk.RIGHT, padx=5)

        logging.debug("FILE_SELECTOR. Calling process_files func in main")
        ttk.Button(button_frame, text="Process Files",
                   command=lambda: self._process_files(process_callback)).pack(side=tk.RIGHT, padx=5)

        ttk.Button(button_frame, text="Set Cycles...",
                   command=self._open_cycle_selection).pack(side=tk.RIGHT, padx=5)

        # Initialize file list and start status updates
        self._update_file_list()
        self._start_status_updates()

        # Create a simple 3x3 table in the analysis tab
        self._create_analysis_table()

        logging.debug("FILE_SELECTOR. Starting Tkinter mainloop.")
        # Starting the main loop
        self.root.mainloop()
        logging.debug("FILE_SELECTOR. Tkinter mainloop exited.")

        # Return selected files if not using callback
        if not process_callback:
            return self.selected_files
        return None

    def _comprehensive_cleanup(self):
        """Comprehensive cleanup of all resources before window destruction."""
        logging.debug("FILE_SELECTOR. Comprehensive cleanup started.")

        # Cancel any pending after events
        if hasattr(self, '_status_update_id') and self._status_update_id:
            logging.debug("FILE_SELECTOR. Canceling pending after events.")
            self.root.after_cancel(self._status_update_id)
            self._status_update_id = None

        # Clean up matplotlib resources
        logging.debug("FILE_SELECTOR. Closing all matplotlib figures.")
        plt.close('all')

        # Set matplotlib to non-interactive mode
        logging.debug("FILE_SELECTOR. Setting matplotlib to non-interactive mode.")
        plt.ioff()

        logging.debug("FILE_SELECTOR. Comprehensive cleanup completed.")

    def _cleanup(self):
        """Basic cleanup resources before window destruction - kept for backward compatibility."""
        logging.debug("FILE_SELECTOR. Cleanup method called.")
        # Call the comprehensive cleanup instead
        self._comprehensive_cleanup()
        logging.debug("FILE_SELECTOR. Cleanup completed.")

    def _on_window_close(self):
        """Handle window close event when the X button is clicked."""
        logging.debug("FILE_SELECTOR. Window close (X button) detected.")
        # Use the comprehensive cleanup
        self._comprehensive_cleanup()

        logging.debug("FILE_SELECTOR. Destroying window from X button.")
        self.root.destroy()
        logging.debug("FILE_SELECTOR. Window destroyed from X button close.")

    def _create_file_lists(self, parent):
        """Create the available and selected file list components."""
        # Configure frame
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=0)
        parent.columnconfigure(2, weight=1)

        # Available files list
        file_frame = ttk.LabelFrame(parent, text="Available NDAX Files")
        file_frame.grid(row=0, column=0, sticky="nsew")

        # Add scrollbar
        scrollbar = ttk.Scrollbar(file_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add listbox
        self.listbox = tk.Listbox(file_frame, selectmode=tk.EXTENDED, yscrollcommand=scrollbar.set)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)

        # Add/Remove buttons
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=0, column=1, sticky="ns")

        ttk.Button(button_frame, text=">>", command=self._add_selected_files).pack(pady=5)
        ttk.Button(button_frame, text="<<", command=self._remove_selected_files).pack(pady=5)

        # Selected files list
        selected_frame = ttk.LabelFrame(parent, text="Selected Files")
        selected_frame.grid(row=0, column=2, sticky="nsew")

        # Add scrollbar
        selected_scrollbar = ttk.Scrollbar(selected_frame)
        selected_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add listbox
        self.selected_listbox = tk.Listbox(selected_frame, yscrollcommand=selected_scrollbar.set)
        self.selected_listbox.pack(fill=tk.BOTH, expand=True)
        selected_scrollbar.config(command=self.selected_listbox.yview)

    def _create_plot_area(self, parent):
        """Create the plotting area within the GUI."""
        # Create a container frame with fixed height for the button
        button_container = ttk.Frame(parent, height=40)
        button_container.pack(side=tk.BOTTOM, fill=tk.X)
        button_container.pack_propagate(False)  # Prevent shrinking

        # Add Save Plot button
        save_plot_button = ttk.Button(button_container, text="Save Plot", command=self._save_current_plot)
        save_plot_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # Create a Figure and add it to a canvas
        plot_container = ttk.Frame(parent)
        plot_container.pack(fill=tk.BOTH, expand=True, side=tk.TOP)

        self.fig = Figure(figsize=(8, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_container)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _save_current_plot(self, plot_type="capacity"):
        """
        Save the current plot to a file.

        Args:
            plot_type: String indicating the type of plot to save ('capacity' or 'dqdv')
        """
        fig = None
        if plot_type == "capacity" and hasattr(self, 'fig'):
            fig = self.fig
        elif plot_type == "dqdv" and hasattr(self, 'dqdv_fig'):
            fig = self.dqdv_fig

        if fig is None:
            messagebox.showinfo("No Plot", "There is no plot to save.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )

        if file_path:
            fig.savefig(file_path, dpi=300, bbox_inches='tight')
            messagebox.showinfo("Success", f"Plot saved to {file_path}")

    def _create_analysis_table(self):
        """Create a table in the analysis tab to display specific capacity results."""
        # Create a frame to hold the table
        table_frame = ttk.Frame(self.analysis_tab)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Configure the table frame grid
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=0)  # Header row
        table_frame.rowconfigure(1, weight=1)  # Table row

        # Create a header frame for cycle labels
        self.header_frame = ttk.Frame(table_frame)
        self.header_frame.grid(row=0, column=0, sticky="ew")

        # First define the metrics that will repeat for each cycle
        self.metrics = ["Specific Charge Capacity (mAh/g)",
                        "Specific Discharge Capacity (mAh/g)",
                        "Coulombic Efficiency (%)"]

        # Store the table frame for future reference
        self.table_frame = table_frame

        # Create the actual table - we'll populate it with _update_table_columns()
        self._update_table_columns()

        # Add a label explaining the purpose of this tab
        explanation = ttk.Label(
            self.analysis_tab,
            text="This tab displays capacity data and statistics for the selected cycles.\n"
                 "Process files in the 'Charge vs Voltage Plot' tab to see results.",
            justify=tk.CENTER
        )
        explanation.pack(pady=10, before=table_frame)

        # Add export button
        export_frame = ttk.Frame(self.analysis_tab)
        export_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(
            export_frame,
            text="Export Table",
            command=self._export_analysis_table
        ).pack(side=tk.RIGHT)

    def _update_table_columns(self):
        """Update the table columns based on the current selected cycles"""
        # Clear existing widgets in the header frame
        for widget in self.header_frame.winfo_children():
            widget.destroy()

        # Recreate the header based on currently selected cycles
        cell_id_label = ttk.Label(self.header_frame, text="", width=15, anchor="center")
        cell_id_label.grid(row=0, column=0, padx=1, pady=1)

        # Define the columns based on selected cycles
        columns = ["Cell ID"]

        col_index = 1
        for cycle in self.selected_cycles:
            # Create a label spanning 3 columns (for the 3 metrics per cycle)
            cycle_label = ttk.Label(self.header_frame, text=f"Cycle {cycle}",
                                    width=len(self.metrics) * 20, anchor="center",
                                    background="#e6e6e6", relief="solid", borderwidth=1)
            cycle_label.grid(row=0, column=col_index, columnspan=len(self.metrics), padx=1, pady=1, sticky="ew")
            col_index += len(self.metrics)

            # Add columns for this cycle
            for metric in self.metrics:
                columns.append(f"C{cycle}: {metric}")

        # If we already have a table, destroy it
        if hasattr(self, 'analysis_table'):
            # Remove old table and scrollbars
            if hasattr(self, 'y_scrollbar'):
                self.y_scrollbar.destroy()
            if hasattr(self, 'x_scrollbar'):
                self.x_scrollbar.destroy()
            self.analysis_table.destroy()

        # Create a new table with updated columns
        self.analysis_table = ttk.Treeview(self.table_frame, columns=columns, show="headings")

        # Define column headings and widths
        self.analysis_table.heading("Cell ID", text="Cell ID")
        self.analysis_table.column("Cell ID", width=100, anchor="center")

        # Set up the metric columns for each cycle
        for cycle in self.selected_cycles:
            for metric in self.metrics:
                col_name = f"C{cycle}: {metric}"
                # Use shorter display text for column headers
                display_text = metric.replace("Specific ", "").replace(" (mAh/g)", "").replace("Coulombic ", "")
                self.analysis_table.heading(col_name, text=display_text)
                self.analysis_table.column(col_name, width=120, anchor="center")

        # Add scrollbars
        self.y_scrollbar = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.analysis_table.yview)
        self.x_scrollbar = ttk.Scrollbar(self.table_frame, orient="horizontal", command=self.analysis_table.xview)
        self.analysis_table.configure(yscrollcommand=self.y_scrollbar.set, xscrollcommand=self.x_scrollbar.set)

        # Place the table and scrollbars in the frame
        self.analysis_table.grid(row=1, column=0, sticky="nsew")
        self.y_scrollbar.grid(row=1, column=1, sticky="ns")
        self.x_scrollbar.grid(row=2, column=0, sticky="ew")

    def _create_dqdv_tab(self):
        """Create the Differential Capacity tab with plot area and statistics."""
        dqdv_tab = ttk.Frame(self.notebook)

        # Configure the grid for the dQ/dV tab
        dqdv_tab.columnconfigure(0, weight=1)
        dqdv_tab.rowconfigure(0, weight=4)  # Main plot area (larger)
        dqdv_tab.rowconfigure(1, weight=1)  # Statistics area (smaller)

        # Create plot area
        plot_frame = ttk.LabelFrame(dqdv_tab, text="dQ/dV Plot Preview")
        plot_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)

        # Create a container frame with fixed height for the save button
        button_container = ttk.Frame(plot_frame, height=40)
        button_container.pack(side=tk.BOTTOM, fill=tk.X)
        button_container.pack_propagate(False)  # Prevent shrinking

        # Add Save Plot button
        save_plot_button = ttk.Button(button_container, text="Save Plot",
                                      command=lambda: self._save_current_plot(plot_type="dqdv"))
        save_plot_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # Create the actual plot area
        plot_container = ttk.Frame(plot_frame)
        plot_container.pack(fill=tk.BOTH, expand=True, side=tk.TOP)

        # Create a Figure and add it to a canvas
        self.dqdv_fig = Figure(figsize=(8, 4))
        self.dqdv_canvas = FigureCanvasTkAgg(self.dqdv_fig, master=plot_container)
        self.dqdv_canvas.draw()
        self.dqdv_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Create statistics area
        stats_frame = ttk.LabelFrame(dqdv_tab, text="dQ/dV Statistics")
        stats_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        # Use grid layout for better control in the stats frame
        stats_frame.columnconfigure(0, weight=1)  # For table area
        stats_frame.rowconfigure(0, weight=0)  # For explanation
        stats_frame.rowconfigure(1, weight=1)  # For table
        stats_frame.rowconfigure(2, weight=0)  # For export button

        # Add explanatory text
        ttk.Label(stats_frame,
                  text="This section displays capacity contributions from each voltage plateau. 1st plateau indicates "
                       "low spin plateau",
                  justify=tk.CENTER).grid(row=0, column=0, sticky="ew", pady=5)

        # Create a frame for the statistics table
        table_frame = ttk.Frame(stats_frame)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # Create columns for the table
        columns = [
            "File", "Cycle",
            "Charge 1st Cap (mAh/g)", "Charge 1st %",
            "Charge 2nd Cap (mAh/g)", "Charge 2nd %",
            "Charge Total (mAh/g)",
            "Discharge 1st Cap (mAh/g)", "Discharge 1st %",
            "Discharge 2nd Cap (mAh/g)", "Discharge 2nd %",
            "Discharge Total (mAh/g)"
        ]

        # Create the table
        self.dqdv_stats_table = ttk.Treeview(table_frame, columns=columns, show="headings", height=5)

        # Configure column headings with shorter text for better display
        heading_map = {
            "File": "Cell ID",
            "Cycle": "Cycle",
            "Charge 1st Cap (mAh/g)": "Chg 1st Cap",
            "Charge 1st %": "Chg 1st %",
            "Charge 2nd Cap (mAh/g)": "Chg 2nd Cap",
            "Charge 2nd %": "Chg 2nd %",
            "Charge Total (mAh/g)": "Chg Total",
            "Discharge 1st Cap (mAh/g)": "Dchg 1st Cap",
            "Discharge 1st %": "Dchg 1st %",
            "Discharge 2nd Cap (mAh/g)": "Dchg 2nd Cap",
            "Discharge 2nd %": "Dchg 2nd %",
            "Discharge Total (mAh/g)": "Dchg Total"
        }

        # Configure column headings and widths
        for col in columns:
            self.dqdv_stats_table.heading(col, text=heading_map[col])
            # Make plateau columns wider to accommodate percentages
            if "Plateau" in col:
                self.dqdv_stats_table.column(col, width=130, anchor="center")
            else:
                self.dqdv_stats_table.column(col, width=100, anchor="center")

        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.dqdv_stats_table.yview)
        self.dqdv_stats_table.configure(yscrollcommand=y_scrollbar.set)

        # Place the table and scrollbar
        self.dqdv_stats_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add export button in its own frame at the bottom
        export_frame = ttk.Frame(stats_frame)
        export_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)

        # Right-align the export button
        export_frame.columnconfigure(0, weight=1)  # This pushes the button to the right

        ttk.Button(
            export_frame,
            text="Export Table",
            command=lambda: self._export_analysis_table(self.dqdv_stats_table, "dqdv_statistics")
        ).grid(row=0, column=0, sticky="e", padx=5, pady=5)

        return dqdv_tab

    ############## ACTION METHODS ###########################
    def _browse_directory(self):
        """Open dialog to select a directory and update the file list."""
        dir_path = filedialog.askdirectory(initialdir=self.current_dir.get())
        if dir_path:
            self.current_dir.set(dir_path)
            self._update_file_list()

    def _update_file_list(self):
        """Update the available files list based on the current directory."""
        self.listbox.delete(0, tk.END)
        try:
            # Get all .ndax files
            ndax_files = [file for file in os.listdir(self.current_dir.get()) if file.endswith(".ndax")]

            # Sort files by extracting the numeric part from filenames
            # This regex finds sequences of digits in the filename
            import re
            def extract_number(filename):
                # Extract all numbers from the filename
                numbers = re.findall(r'\d+', filename)
                # Return the first number found (as an integer) or 0 if none found
                return int(numbers[0]) if numbers else 0

            # Sort files numerically in descending order (high to low)
            ndax_files.sort(key=extract_number, reverse=True)

            # Add sorted files to the listbox
            for file in ndax_files:
                self.listbox.insert(tk.END, file)
        except Exception as e:
            messagebox.showerror("Error", f"Could not list directory: {str(e)}")

    def _add_selected_files(self):
        """Add selected files from available list to selected list."""
        selected_indices = self.listbox.curselection()
        for i in selected_indices:
            file = self.listbox.get(i)
            full_path = os.path.join(self.current_dir.get(), file)
            if full_path not in self.selected_files:
                self.selected_files.append(full_path)
                self.selected_listbox.insert(tk.END, file)

    def _remove_selected_files(self):
        """Remove selected files from the selected list."""
        selected_indices = self.selected_listbox.curselection()
        # Reverse to avoid index shifting during deletion
        for i in sorted(selected_indices, reverse=True):
            file = self.selected_listbox.get(i)
            full_path = next((f for f in self.selected_files if os.path.basename(f) == file), None)
            if full_path in self.selected_files:
                self.selected_files.remove(full_path)
            self.selected_listbox.delete(i)

    def _process_files(self, callback):
        """Process the selected files using the provided callback function."""
        logging.debug("FILE_SELECTOR._process_files func started")
        if not self.selected_files:
            messagebox.showwarning(
                "No Selection",
                "No files are currently selected. Please select files before processing."
            )
            return

        # Store callback for later use
        self._last_callback = callback

        # If we have a callback function, call it with the selected files
        if callback:
            logging.debug("FILE_SELECTOR._process_files callback")
            # Create a copy of the selected files
            files_to_process = self.selected_files.copy()

            # Show a processing message
            self.status_var.set(f"Processing {len(files_to_process)} files...")
            self.root.update()

            # Call the callback function with just the list of files
            # The callback function will access self.selected_cycles directly
            features_df = callback(files_to_process)

            # Update the analysis table with the new data
            if features_df is not None and not features_df.empty:
                self._update_analysis_table(features_df)

            # Update status to show completion
            cycle_text = ", ".join(str(c) for c in self.selected_cycles)
            self.status_var.set(f"Processed {len(files_to_process)} files. Cycles: {cycle_text}")
            logging.debug("FILE_SELECTOR._process_files callback finished")

        else:
            logging.debug("FILE_SELECTOR._process_files func no callback")
            # If no callback, just confirm and return
            messagebox.showinfo(
                "Files Ready for Processing",
                f"{len(self.selected_files)} files ready to be processed."
            )

            # Cancel any pending after events before destroying the window
            if hasattr(self, '_status_update_id') and self._status_update_id:
                self.root.after_cancel(self._status_update_id)
            self.root.destroy()
            logging.debug("FILE_SELECTOR._process_files func no callback finished")

    def _clear_selection(self):
        """Clear the current file selection."""
        self.selected_files = []
        self.selected_listbox.delete(0, tk.END)
        messagebox.showinfo("Selection Cleared", "File selection has been cleared.")

    def _update_status_display(self):
        """Update the status label with the current file selection count."""
        file_count = len(self.selected_files)
        if file_count == 0:
            self.status_var.set("No files selected")
        elif file_count == 1:
            self.status_var.set("1 file selected")
        else:
            self.status_var.set(f"{file_count} files selected")

    def _start_status_updates(self):
        """Schedule periodic updates of the status display."""

        # Store the after ID so we can cancel it later
        self._status_update_id = None

        def update():
            self._update_status_display()
            # Store the ID returned by after so we can cancel it if needed
            self._status_update_id = self.root.after(500, update)

        # Start the first update
        update()

    def _exit_application(self):
        """Exit the application after confirmation."""
        if messagebox.askyesno("Confirm Exit", "Are you sure you want to exit the file selector?"):
            logging.debug("FILE_SELECTOR. User confirmed exit. Performing cleanup...")
            # Use the comprehensive cleanup
            self._comprehensive_cleanup()

            logging.debug("FILE_SELECTOR. Destroying root window.")
            self.root.destroy()
            logging.debug("FILE_SELECTOR. Root window destroyed.")

    def update_plot(self, fig):
        """Update the plot in the GUI with a new figure."""
        # Check if root window still exists
        if not hasattr(self, 'root') or not self.root.winfo_exists():
            print("Warning: Attempted to update plot after window was closed")
            return

        # Find the plot frame if needed
        if not hasattr(self, 'plot_frame') or not self.plot_frame.winfo_exists():
            print("Warning: Plot frame no longer exists")
            return

        # Completely clear the plot frame first - safely
        for widget in list(self.plot_frame.winfo_children()):
            try:
                widget.destroy()
            except tk.TclError:
                # Widget might already be destroyed, just continue
                pass

        # Store the new figure with a consistent size
        self.fig = fig

        try:
            # Create a fixed-height button container at the bottom
            button_container = ttk.Frame(self.plot_frame, height=40)
            button_container.pack(side=tk.BOTTOM, fill=tk.X)
            button_container.pack_propagate(False)  # Prevent shrinking

            # Add Save Plot button
            save_plot_button = ttk.Button(button_container, text="Save Plot", command=self._save_current_plot)
            save_plot_button.pack(side=tk.RIGHT, padx=5, pady=5)

            # Create plot container for the canvas
            plot_container = ttk.Frame(self.plot_frame)
            plot_container.pack(fill=tk.BOTH, expand=True)

            # Create a new canvas with the figure
            self.canvas = FigureCanvasTkAgg(self.fig, master=plot_container)

            # Make sure the figure fits properly in the available space
            self.fig.tight_layout()

            # Draw the canvas
            self.canvas.draw()

            # Pack the canvas to fill the available space
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            # Update analysis tab with new data
            self._update_analysis_table()

        except Exception as e:
            print(f"Error updating plot: {e}")

    def display_matplotlib_figure(self, fig):
        """Display a matplotlib figure in the plot preview area."""
        # Clear any existing plot
        for widget in self.plot_frame.winfo_children():
            widget.destroy()

        # Create a new canvas with the figure
        canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Add a frame for the Save Plot button without toolbar
        button_frame = ttk.Frame(self.plot_frame)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # Add Save Plot button
        save_plot_button = ttk.Button(button_frame, text="Save Plot", command=self._save_current_plot)
        save_plot_button.pack(side=tk.RIGHT, padx=5)

    def _update_analysis_table(self, features_df=None):
        """
        Update the analysis table with data from the processed files for selected cycles.

        :param features_df: DataFrame containing the extracted features.
                            If None, attempt to clear the table.
        """
        # Clear existing items in the table
        for item in self.analysis_table.get_children():
            self.analysis_table.delete(item)

        # If no data provided, exit early
        if features_df is None or features_df.empty:
            return

        # Get unique cell IDs
        cell_ids = features_df['cell ID'].unique()

        # Process data for each cell ID
        for cell_id in cell_ids:
            cell_data = features_df[features_df['cell ID'] == cell_id]

            # Create a row for this cell with values for all cycles
            row_values = [cell_id]

            # Add data for each selected cycle
            for cycle in self.selected_cycles:
                cycle_data = cell_data[cell_data['Cycle'] == cycle]

                # If we have data for this cycle, add it to the row
                if not cycle_data.empty:
                    for metric in self.metrics:
                        value = cycle_data.iloc[0].get(metric, 0)
                        row_values.append(f"{float(value):.1f}" if pd.notnull(value) else "-")
                else:
                    # No data for this cycle, add placeholder values
                    row_values.extend(["-", "-", "-"])

            # Insert the row into the table
            self.analysis_table.insert('', 'end', values=row_values)

        # Calculate and display statistics (mean, std dev, etc.)
        if len(self.analysis_table.get_children()) > 0:
            # Add a separator row
            separator_id = self.analysis_table.insert('', 'end', values=['-'] * len(row_values))
            self.analysis_table.item(separator_id, tags=('separator',))

            # Add statistics rows
            self._add_statistics_rows(features_df)

            # Apply styling
            self.analysis_table.tag_configure('separator', background='#f0f0f0')
            self.analysis_table.tag_configure('statistic', background='#e6f2ff', font=('', 9, 'bold'))

    def _add_statistics_rows(self, features_df):
        """Add statistics rows to the analysis table for all selected cycles."""
        # For each statistic type (mean, std dev, rsd)
        stat_types = [
            ('Average', 'mean', '{:.1f}'),
            ('Std Dev', 'std', '{:.1f}'),
            ('RSD (%)', lambda x: (x.std() / x.mean() * 100) if x.mean() != 0 else float('nan'), '{:.1f}')
        ]

        for label, func, format_str in stat_types:
            row_values = [label]

            # Calculate statistics for each selected cycle and metric
            for cycle in self.selected_cycles:
                cycle_data = features_df[features_df['Cycle'] == cycle]

                if not cycle_data.empty:
                    for metric in self.metrics:
                        if metric in cycle_data.columns:
                            values = pd.to_numeric(cycle_data[metric], errors='coerce')

                            if callable(func):
                                stat = func(values)
                            else:
                                stat = getattr(values, func)()

                            # Use format method instead of f-string with format specifier
                            row_values.append(format_str.format(stat) if pd.notnull(stat) else "-")
                        else:
                            row_values.append("-")
                else:
                    # No data for this cycle
                    row_values.extend(["-", "-", "-"])

            # Insert the statistics row
            stat_id = self.analysis_table.insert('', 'end', values=row_values)
            self.analysis_table.item(stat_id, tags=('statistic',))

    def update_dqdv_plot(self, fig, dqdv_stats=None):
        """
        Update the dQ/dV plot in the GUI with a new figure and statistics.

        Args:
            fig: The matplotlib figure containing dQ/dV plots
            dqdv_stats: Optional list of dictionaries with peak statistics
        """
        logging.debug("FILE_SELECTOR.update_dqdv_plot started")

        # Check if root window still exists
        if not hasattr(self, 'root') or not self.root.winfo_exists():
            logging.debug("Warning: Attempted to update dQ/dV plot after window was closed")
            return

        # Check if we have the dqdv_tab attribute
        if not hasattr(self, 'dqdv_tab') or not self.dqdv_tab.winfo_exists():
            logging.debug("Warning: dQ/dV tab no longer exists")
            return

        # Find the plot frame in the dQ/dV tab
        plot_frame = None
        for child in self.dqdv_tab.winfo_children():
            if isinstance(child, ttk.LabelFrame) and child.cget("text") == "dQ/dV Plot Preview":
                plot_frame = child
                break

        if not plot_frame:
            logging.debug("Warning: dQ/dV plot frame not found")
            return

        # Log the figure object details
        logging.debug(f"dQ/dV Figure object: {fig}")
        logging.debug(f"dQ/dV Figure size: {fig.get_size_inches()}")
        if hasattr(fig, 'axes') and fig.axes:
            logging.debug(f"Number of axes in figure: {len(fig.axes)}")
            for i, ax in enumerate(fig.axes):
                logging.debug(f"Axis {i} has {len(ax.lines)} lines")

        # Completely clear the plot frame
        logging.debug("Clearing existing dQ/dV plot frame widgets")
        for widget in list(plot_frame.winfo_children()):
            try:
                widget.destroy()
            except tk.TclError:
                # Widget might already be destroyed, just continue
                logging.debug("Widget already destroyed during cleanup")
                pass

        # Store the new figure
        logging.debug("Storing the new dQ/dV figure")
        self.dqdv_fig = fig

        # Create a fixed-height button container at the bottom
        button_container = ttk.Frame(plot_frame, height=40)
        button_container.pack(side=tk.BOTTOM, fill=tk.X)
        button_container.pack_propagate(False)  # Prevent shrinking

        # Add Save Plot button
        save_plot_button = ttk.Button(button_container, text="Save Plot",
                                      command=lambda: self._save_current_plot(plot_type="dqdv"))
        save_plot_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # Create plot container for the canvas
        plot_container = ttk.Frame(plot_frame)
        plot_container.pack(fill=tk.BOTH, expand=True)

        # Create a new canvas with the figure
        logging.debug("Creating new FigureCanvasTkAgg for dQ/dV figure")
        try:
            self.dqdv_canvas = FigureCanvasTkAgg(self.dqdv_fig, master=plot_container)

            # Make sure the figure fits properly in the available space
            self.dqdv_fig.tight_layout()

            # Draw the canvas
            logging.debug("Drawing the dQ/dV canvas")
            self.dqdv_canvas.draw()

            # Pack the canvas to fill the available space
            logging.debug("Packing the dQ/dV canvas into the container")
            self.dqdv_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            logging.debug("dQ/dV canvas successfully created and packed")
        except Exception as e:
            logging.debug(f"Error creating or drawing dQ/dV canvas: {e}")
            import traceback
            logging.debug(traceback.format_exc())

        # Update statistics table if provided
        if dqdv_stats and hasattr(self, 'dqdv_stats_table'):
            logging.debug(f"Updating dQ/dV stats table with {len(dqdv_stats)} entries")
            # Clear existing items
            for item in self.dqdv_stats_table.get_children():
                self.dqdv_stats_table.delete(item)

            # Sort by cycle first, then by file for better comparison
            dqdv_stats_sorted = sorted(dqdv_stats, key=lambda x: (x.get('Cycle', 0), x.get('File', '')))

            # Add plateau statistics
            for stat in dqdv_stats_sorted:
                # Get capacity values
                charge_1st = stat.get('Charge 1st Plateau (mAh/g)', 0)
                charge_2nd = stat.get('Charge 2nd Plateau (mAh/g)', 0)
                charge_total = stat.get('Charge Total (mAh/g)', 0)
                discharge_1st = stat.get('Discharge 1st Plateau (mAh/g)', 0)
                discharge_2nd = stat.get('Discharge 2nd Plateau (mAh/g)', 0)
                discharge_total = stat.get('Discharge Total (mAh/g)', 0)

                # Calculate percentages (handle division by zero)
                charge_1st_pct = (charge_1st / charge_total * 100) if charge_total != 0 else 0
                charge_2nd_pct = (charge_2nd / charge_total * 100) if charge_total != 0 else 0
                discharge_1st_pct = (discharge_1st / discharge_total * 100) if discharge_total != 0 else 0
                discharge_2nd_pct = (discharge_2nd / discharge_total * 100) if discharge_total != 0 else 0

                # Format values with one decimal place plus percentage in brackets
                formatted_values = [
                    stat.get('File', ''),
                    stat.get('Cycle', ''),
                    f"{charge_1st:.1f}",
                    f"{charge_1st_pct:.1f}",
                    f"{charge_2nd:.1f}",
                    f"{charge_2nd_pct:.1f}",
                    f"{charge_total:.1f}",
                    f"{discharge_1st:.1f}",
                    f"{discharge_1st_pct:.1f}",
                    f"{discharge_2nd:.1f}",
                    f"{discharge_2nd_pct:.1f}",
                    f"{discharge_total:.1f}"
                ]

                # Insert into table
                self.dqdv_stats_table.insert('', 'end', values=formatted_values)

            logging.debug("dQ/dV stats table updated successfully")
        else:
            logging.debug(
                f"Skipping dQ/dV stats table update: have stats: {bool(dqdv_stats)}, have table: {hasattr(self, 'dqdv_stats_table')}")

        logging.debug("FILE_SELECTOR.update_dqdv_plot completed")

    def _export_raw_data(self):
        """
        Export raw data from selected NDAX files directly to Excel using DataLoader.
        Allows user to choose the export directory.
        Uses DataLoader for efficient batch file reading with error handling.
        """
        if not self.selected_files:
            messagebox.showwarning(
                "No Selection",
                "No files are currently selected. Please select files before exporting."
            )
            return

        # Ask user to select an export directory
        export_dir = filedialog.askdirectory(
            title="Select Export Directory",
            initialdir=os.path.dirname(self.selected_files[0])
        )

        # If user cancels directory selection, abort export
        if not export_dir:
            return

        # Create a progress bar for user feedback
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Exporting Raw Data")
        progress_window.geometry("400x120")
        progress_window.transient(self.root)  # Set as transient to main window
        progress_window.grab_set()  # Make modal

        # Configure progress window grid
        progress_window.columnconfigure(0, weight=1)
        progress_window.rowconfigure(0, weight=0)
        progress_window.rowconfigure(1, weight=0)
        progress_window.rowconfigure(2, weight=0)

        # Add status label
        status_label = ttk.Label(progress_window, text="Loading files with DataLoader...")
        status_label.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        # Add progress bar
        progress_bar = ttk.Progressbar(progress_window, mode="determinate", length=380)
        progress_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        # Add details label for cache info
        details_label = ttk.Label(progress_window, text="", font=('', 8))
        details_label.grid(row=2, column=0, sticky="ew", padx=10, pady=2)

        # Create a copy of selected files
        files_to_export = self.selected_files.copy()
        total_files = len(files_to_export)

        # Update progress bar max value
        progress_bar["maximum"] = total_files + 1  # +1 for loading phase
        progress_bar["value"] = 0
        progress_window.update()

        try:
            # Initialize DataLoader and load all files at once
            logging.debug("FILE_SELECTOR._export_raw_data: Initializing DataLoader")
            data_loader = DataLoader()

            # Load all files
            status_label.config(text="Loading all NDAX files...")
            progress_window.update()

            data_loader.load_files(files_to_export)

            # Update progress for loading phase
            progress_bar["value"] = 1

            # Get cache info for user feedback
            cache_info = data_loader.get_cache_info()
            details_label.config(text=f"Loaded {cache_info['cached_files']} files "
                                      f"({cache_info['memory_usage_mb']:.1f} MB)")
            progress_window.update()

            # Log cache information
            logging.debug(f"FILE_SELECTOR._export_raw_data: DataLoader cache: "
                          f"{cache_info['cached_files']} files, "
                          f"{cache_info['total_rows']} total rows, "
                          f"{cache_info['memory_usage_mb']:.1f} MB")

            # Check for failed files
            failed_files = data_loader.get_failed_files()
            if failed_files:
                failed_names = [os.path.basename(f) for f in failed_files]
                logging.warning(f"FILE_SELECTOR._export_raw_data: Failed to load files: {failed_names}")

            # Export each successfully loaded file
            files_exported = 0
            export_errors = []

            for file_path in files_to_export:
                try:
                    file_name = os.path.basename(file_path)

                    # Skip files that failed to load
                    if not data_loader.is_loaded(file_path):
                        logging.debug(f"FILE_SELECTOR._export_raw_data: Skipping unloaded file: {file_name}")
                        export_errors.append(f"{file_name} (failed to load)")
                        continue

                    # Update status message
                    status_label.config(text=f"Exporting {file_name}... ({files_exported + 1}/{total_files})")
                    progress_window.update()

                    # Get the data from DataLoader cache
                    df = data_loader.get_data(file_path)

                    if df is None:
                        export_errors.append(f"{file_name} (no data available)")
                        continue

                    # Generate output file path with same name but .xlsx extension
                    output_path = os.path.join(export_dir, os.path.splitext(file_name)[0] + ".xlsx")

                    # Export to Excel
                    df.to_excel(output_path, index=False)

                    logging.debug(f"FILE_SELECTOR._export_raw_data: Exported {file_name} "
                                  f"with {len(df)} rows to {output_path}")

                    # Update progress
                    files_exported += 1
                    progress_bar["value"] = files_exported + 1  # +1 for loading phase
                    progress_window.update()

                except Exception as e:
                    logging.error(f"FILE_SELECTOR._export_raw_data: Error exporting {file_path}: {e}")
                    export_errors.append(f"{os.path.basename(file_path)} (export error: {str(e)})")

            # Clean up DataLoader
            data_loader.clear_cache()
            logging.debug("FILE_SELECTOR._export_raw_data: DataLoader cache cleared")

        except Exception as e:
            logging.error(f"FILE_SELECTOR._export_raw_data: DataLoader initialization failed: {e}")
            progress_window.destroy()
            messagebox.showerror("Export Failed", f"Failed to initialize data loading: {str(e)}")
            return

        # Close progress window
        progress_window.destroy()

        # Show completion message
        if export_errors:
            error_details = "\n".join(export_errors[:5])  # Show first 5 errors
            if len(export_errors) > 5:
                error_details += f"\n... and {len(export_errors) - 5} more errors"

            messagebox.showwarning(
                "Export Completed With Errors",
                f"Exported {files_exported} of {total_files} files to {export_dir}.\n\n"
                f"Issues encountered:\n{error_details}"
            )
        else:
            messagebox.showinfo(
                "Export Completed",
                f"Successfully exported raw data for {files_exported} files to:\n{export_dir}\n\n"
                f"Performance: Files loaded once and cached for efficient export."
            )

        logging.debug(f"FILE_SELECTOR._export_raw_data: Export completed. "
                      f"Success: {files_exported}, Errors: {len(export_errors)}")

    def _export_analysis_table(self, table=None, file_prefix=None):
        """
        Export the specified table to an Excel file.

        Args:
            table: The ttk.Treeview widget to export. If None, uses self.analysis_table.
            file_prefix: Optional prefix for the default filename.
        """
        # If no table specified, use the analysis table
        if table is None:
            table = self.analysis_table

        # Check if the table has data
        if not table.get_children():
            messagebox.showinfo("Export Table", "No data to export.")
            return

        # Set up default filename based on the provided prefix or use the default
        if file_prefix:
            default_file = f"{file_prefix}.xlsx"
        else:
            default_file = os.path.basename(self.default_output_file)

        default_dir = os.path.dirname(os.path.abspath(self.default_output_file))

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialdir=default_dir,
            initialfile=default_file
        )

        if not file_path:
            return  # User cancelled

        try:
            # Create a DataFrame from the table data
            data = []
            columns = table["columns"]

            for item_id in table.get_children():
                item_values = table.item(item_id)["values"]
                data.append(dict(zip(columns, item_values)))

            # Convert to DataFrame and export
            df = pd.DataFrame(data)
            df.to_excel(file_path, index=False)

            messagebox.showinfo("Export Successful", f"Table data exported to {file_path}")
            logging.debug(f"FILE_SELECTOR. Table data exported to {file_path}")

        except Exception as e:
            messagebox.showerror("Export Failed", f"An error occurred: {str(e)}")
            logging.debug(f"FILE_SELECTOR. Error exporting table data: {e}")