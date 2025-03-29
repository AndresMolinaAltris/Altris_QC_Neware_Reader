from common.imports import (
    tk, filedialog, ttk, messagebox, os,
    logging, FigureCanvasTkAgg, Figure, plt
)
from performance_stats import calculate_statistics

class FileSelector:
    """A GUI for selecting and processing .ndax files with preview functionality."""

    def __init__(self, initial_dir=None):
        """Initialize the file selector with an optional starting directory."""
        self.initial_dir = initial_dir or os.getcwd()
        self.selected_files = []
        self.root = None
        self.listbox = None
        self.selected_listbox = None
        self.status_var = None
        self.current_dir = None
        self.fig = None
        self.canvas = None

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

        ttk.Button(button_frame, text="Exit",
                   command=self._exit_application).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Clear Selection",
                   command=self._clear_selection).pack(side=tk.RIGHT, padx=5)

        logging.debug("FILE_SELECTOR. Calling process_files func in main")
        ttk.Button(button_frame, text="Process Files",
                   command=lambda: self._process_files(process_callback)).pack(side=tk.RIGHT, padx=5)

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

    def _save_current_plot(self):
        """Save the current plot to a file."""
        if not hasattr(self, 'fig') or self.fig is None:
            messagebox.showinfo("No Plot", "There is no plot to save.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )

        if file_path:
            self.fig.savefig(file_path, dpi=300, bbox_inches='tight')
            messagebox.showinfo("Success", f"Plot saved to {file_path}")

    def _create_analysis_table(self):
        """Create a table in the analysis tab to display specific capacity results."""
        # Create a frame to hold the table
        table_frame = ttk.Frame(self.analysis_tab)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Configure the table frame grid
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        # Create a Treeview widget with our desired columns
        columns = ("Cell ID", "Specific Charge Capacity (mAh/g)",
                   "Specific Discharge Capacity (mAh/g)", "Coulombic Efficiency (%)")
        self.analysis_table = ttk.Treeview(table_frame, columns=columns, show="headings")

        # Define column headings and widths
        column_widths = {
            "Cell ID": 100,
            "Specific Charge Capacity (mAh/g)": 200,
            "Specific Discharge Capacity (mAh/g)": 200,
            "Coulombic Efficiency (%)": 150
        }

        for col in columns:
            self.analysis_table.heading(col, text=col)
            self.analysis_table.column(col, width=column_widths[col], anchor="center")

        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.analysis_table.yview)
        x_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.analysis_table.xview)
        self.analysis_table.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)

        # Place the table and scrollbars in the frame
        self.analysis_table.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")

        # Add a label explaining the purpose of this tab
        explanation = ttk.Label(
            self.analysis_tab,
            text="This tab displays first cycle data and statistics from processed files.\n"
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

    # Action Methods
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
            for file in os.listdir(self.current_dir.get()):
                if file.endswith(".ndax"):
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

        # If we have a callback function, call it with the selected files
        if callback:
            logging.debug("FILE_SELECTOR._process_files callback")
            # Create a copy of the selected files
            files_to_process = self.selected_files.copy()

            # Show a processing message
            self.status_var.set(f"Processing {len(files_to_process)} files...")
            self.root.update()

            # Call the callback function with the list of files
            features_df = callback(files_to_process)

            # Update the analysis table with the new data
            if features_df is not None and not features_df.empty:
                self._update_analysis_table(features_df)

            # Update status to show completion
            self.status_var.set(f"Processed {len(files_to_process)} files. Ready for next batch.")
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
        Update the analysis table with data from the processed files.

        :param features_df: DataFrame containing the extracted features.
                            If None, attempt to clear the table.
        """
        # Clear existing items in the table
        for item in self.analysis_table.get_children():
            self.analysis_table.delete(item)

        # If no data provided, exit early
        if features_df is None or features_df.empty:
            return

        # Filter data to only include first cycle
        cycle1_data = features_df[features_df['Cycle'] == 1]

        # If no cycle 1 data, exit early
        if cycle1_data.empty:
            return

        # Insert data for each cell
        for _, row in cycle1_data.iterrows():
            # Prepare the values to display
            values = (
                row.get('cell ID', 'Unknown'),
                f"{row.get('Specific Charge Capacity (mAh/g)', 0):.1f}",
                f"{row.get('Specific Discharge Capacity (mAh/g)', 0):.1f}",
                f"{row.get('Coulombic Efficiency (%)', 0):.1f}"
            )

            # Insert the row into the table
            self.analysis_table.insert('', 'end', values=values)

        # Calculate statistics
        stats_df = calculate_statistics(features_df)

        if stats_df is not None:
            # Add a separator row
            separator_id = self.analysis_table.insert('', 'end', values=('---', '---', '---', '---'))
            self.analysis_table.item(separator_id, tags=('separator',))

            # Add statistics rows
            for _, row in stats_df.iterrows():
                values = (
                    row['Cell ID'],
                    row['Specific Charge Capacity (mAh/g)'],
                    row['Specific Discharge Capacity (mAh/g)'],
                    row['Coulombic Efficiency (%)']
                )

                stat_id = self.analysis_table.insert('', 'end', values=values)
                # Tag the row for potential styling
                self.analysis_table.item(stat_id, tags=('statistic',))

            # Apply styling for statistics rows
            self.analysis_table.tag_configure('separator', background='#f0f0f0')
            self.analysis_table.tag_configure('statistic', background='#e6f2ff', font=('', 9, 'bold'))

    def _export_analysis_table(self):
        """Export the analysis table to an Excel file."""
        # This is a placeholder for future export functionality
        messagebox.showinfo(
            "Export Table",
            "This feature will be implemented in a future update."
        )