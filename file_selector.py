import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure


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

    def show_interface(self, process_callback=None):
        """
        Display the file selector interface and handle file selection/processing.
        """
        # Create and configure the main window
        self.root = tk.Tk()
        self.root.title("Neware NDAX File Selector")
        self.root.geometry("800x800")  # Increased height

        # Initialize variables
        self.selected_files = []
        self.current_dir = tk.StringVar(value=self.initial_dir)
        self.status_var = tk.StringVar(value="No files selected")

        # Configure grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0)  # Directory selector row
        self.root.rowconfigure(1, weight=1)  # File lists row
        self.root.rowconfigure(2, weight=2)  # Plot area row
        self.root.rowconfigure(3, weight=0)  # Buttons row

        # Create the directory selector in row 0
        dir_frame = ttk.Frame(self.root)
        dir_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        ttk.Label(dir_frame, text="Directory:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(dir_frame, textvariable=self.current_dir, width=60).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(dir_frame, text="Browse...", command=self._browse_directory).pack(side=tk.LEFT)

        # Create file lists frame in row 1
        file_frame = ttk.Frame(self.root)
        file_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self._create_file_lists(file_frame)

        # Create plot area in row 2
        plot_frame = ttk.LabelFrame(self.root, text="Plot Preview")
        plot_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        self._create_plot_area(plot_frame)

        # Create buttons in row 3
        button_frame = ttk.Frame(self.root)
        button_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)

        ttk.Label(button_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Exit",
                   command=self._exit_application).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Clear Selection",
                   command=self._clear_selection).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Process Files",
                   command=lambda: self._process_files(process_callback)).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Confirm Selection",
                   command=self._confirm_selection).pack(side=tk.RIGHT, padx=5)

        # Initialize file list and start status updates
        self._update_file_list()
        self._start_status_updates()

        # Start the GUI event loop
        self.root.mainloop()

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
        # Create a Figure and add it to a canvas
        self.fig = Figure(figsize=(8, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, side=tk.TOP)

        # Add a toolbar for basic navigation
        toolbar_frame = ttk.Frame(parent)
        toolbar_frame.pack(fill=tk.X, side=tk.BOTTOM)

        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()

        # Add Save Plot button
        save_plot_button = ttk.Button(toolbar_frame, text="Save Plot", command=self._save_current_plot)
        save_plot_button.pack(side=tk.RIGHT, padx=5)

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

    def _confirm_selection(self):
        """Show a confirmation message about the current selection."""
        if self.selected_files:
            messagebox.showinfo(
                "Selection Confirmed",
                f"{len(self.selected_files)} files selected. You can continue selecting more files."
            )
        else:
            messagebox.showwarning(
                "No Selection",
                "No files are currently selected. Please select files before confirming."
            )

    def _process_files(self, callback):
        """Process the selected files using the provided callback function."""
        if not self.selected_files:
            messagebox.showwarning(
                "No Selection",
                "No files are currently selected. Please select files before processing."
            )
            return

        # If we have a callback function, call it with the selected files
        if callback:
            # Create a copy of the selected files
            files_to_process = self.selected_files.copy()

            # Show a processing message
            self.status_var.set(f"Processing {len(files_to_process)} files...")
            self.root.update()

            # Call the callback function with the list of files
            callback(files_to_process)

            # Update status to show completion
            self.status_var.set(f"Processed {len(files_to_process)} files. Ready for next batch.")
        else:
            # If no callback, just confirm and return
            messagebox.showinfo(
                "Files Ready for Processing",
                f"{len(self.selected_files)} files ready to be processed."
            )
            self.root.destroy()

    def _clear_selection(self):
        """Clear the current file selection."""
        self.selected_files = []
        self.selected_listbox.delete(0, tk.END)
        messagebox.showinfo("Selection Cleared", "File selection has been cleared.")

    def _exit_application(self):
        """Exit the application after confirmation."""
        if messagebox.askyesno("Confirm Exit", "Are you sure you want to exit the file selector?"):
            self.root.destroy()

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

        def update():
            self._update_status_display()
            self.root.after(500, update)

        update()

    def update_plot(self, fig):
        """Update the plot in the GUI with a new figure."""
        # Clear the current figure and plot the new one
        if hasattr(self, 'fig') and self.fig is not None:
            for ax in self.fig.get_axes():
                ax.clear()

            # Copy the content from the provided figure
            for ax_new in fig.get_axes():
                ax = self.fig.add_subplot(111)
                for line in ax_new.lines:
                    ax.plot(line.get_xdata(), line.get_ydata(),
                            color=line.get_color(), linestyle=line.get_linestyle())

                ax.set_xlabel(ax_new.get_xlabel())
                ax.set_ylabel(ax_new.get_ylabel())
                ax.set_title(ax_new.get_title())
                if ax_new.get_legend() is not None:
                    ax.legend()
                ax.grid(True)

            self.canvas.draw()
        else:
            # If there's no figure yet, create one
            self.fig = fig

            if not hasattr(self, 'plot_frame'):
                for child in self.root.winfo_children():
                    if isinstance(child, ttk.LabelFrame) and child.winfo_children():
                        if child.cget('text') == "Plot Preview":
                            self.plot_frame = child
                            break

                # Create the canvas in the plot frame
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            #self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
            #self.canvas.draw()
            #self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # Add this to FileSelector class
    def display_matplotlib_figure(self, fig):
        """Display a matplotlib figure in the plot preview area."""
        # Clear any existing plot
        for widget in self.plot_frame.winfo_children():
            widget.destroy()

        # Create a new canvas with the figure
        canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Add navigation toolbar
        toolbar_frame = ttk.Frame(self.plot_frame)
        toolbar_frame.pack(fill=tk.X, side=tk.BOTTOM)
        NavigationToolbar2Tk(canvas, toolbar_frame)

# Convenience function for easier access
def select_ndax_files(initial_dir=None, callback=None):
    """
    Display a file selection dialog for .ndax files.

    Args:
        initial_dir (str, optional): Initial directory to open.
        callback (callable, optional): Function to call with selected files.

    Returns:
        list: List of selected file paths if no callback provided.
    """
    selector = FileSelector(initial_dir)
    return selector.show_interface(callback)


if __name__ == "__main__":
    # Test the file selector
    def test_callback(files):
        print(f"Received {len(files)} files in callback.")
        for f in files[:3]:  # Show first 3 files
            print(f"  - {f}")
        if len(files) > 3:
            print(f"  - ... and {len(files) - 3} more")


    # Uncomment one of these to test different modes:
    # files = select_ndax_files()  # Return mode
    select_ndax_files(callback=test_callback)  # Callback mode