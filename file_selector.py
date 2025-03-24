import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import os


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

    def show_interface(self, process_callback=None):
        """
        Display the file selector interface and handle file selection/processing.

        Args:
            process_callback (callable): Function to call with the list of selected files
                                       when the "Process Files" button is clicked.

        Returns:
            list: List of selected files if no callback provided
        """
        # Create and configure the main window
        self.root = tk.Tk()
        self.root.title("Neware NDAX File Selector")
        self.root.geometry("800x500")

        # Initialize variables
        self.selected_files = []
        self.current_dir = tk.StringVar(value=self.initial_dir)
        self.status_var = tk.StringVar(value="No files selected")

        # Create the UI components
        self._create_directory_selector()
        self._create_file_lists()
        self._create_control_buttons(process_callback)

        # Initialize file list and start status updates
        self._update_file_list()
        self._start_status_updates()

        # Start the GUI event loop
        self.root.mainloop()

        # Return selected files if not using callback
        if not process_callback:
            return self.selected_files
        return None

    def _create_directory_selector(self):
        """Create the directory selection components."""
        frame_top = ttk.Frame(self.root)
        frame_top.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(frame_top, text="Directory:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(frame_top, textvariable=self.current_dir, width=60).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(frame_top, text="Browse...", command=self._browse_directory).pack(side=tk.LEFT)

    def _create_file_lists(self):
        """Create the available and selected file list components."""
        frame_files = ttk.Frame(self.root)
        frame_files.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Available files list
        file_frame = ttk.LabelFrame(frame_files, text="Available NDAX Files")
        file_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=(0, 5))

        scrollbar = ttk.Scrollbar(file_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(file_frame, selectmode=tk.EXTENDED, yscrollcommand=scrollbar.set)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)

        # Selected files list
        selected_frame = ttk.LabelFrame(frame_files, text="Selected Files")
        selected_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)

        selected_scrollbar = ttk.Scrollbar(selected_frame)
        selected_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.selected_listbox = tk.Listbox(selected_frame, yscrollcommand=selected_scrollbar.set)
        self.selected_listbox.pack(fill=tk.BOTH, expand=True)
        selected_scrollbar.config(command=self.selected_listbox.yview)

        # Add/Remove buttons
        add_remove_frame = ttk.Frame(frame_files)
        add_remove_frame.pack(fill=tk.Y, padx=5)

        ttk.Button(add_remove_frame, text=">>", command=self._add_selected_files).pack(pady=5)
        ttk.Button(add_remove_frame, text="<<", command=self._remove_selected_files).pack(pady=5)

    def _create_control_buttons(self, process_callback):
        """Create the control buttons at the bottom of the interface."""
        frame_buttons = ttk.Frame(self.root)
        frame_buttons.pack(fill=tk.X, padx=10, pady=10)

        # Status label
        ttk.Label(frame_buttons, textvariable=self.status_var).pack(side=tk.LEFT, padx=5)

        # Control buttons
        ttk.Button(frame_buttons, text="Exit",
                   command=self._exit_application).pack(side=tk.RIGHT, padx=5)
        ttk.Button(frame_buttons, text="Clear Selection",
                   command=self._clear_selection).pack(side=tk.RIGHT, padx=5)
        ttk.Button(frame_buttons, text="Process Files",
                   command=lambda: self._process_files(process_callback)).pack(side=tk.RIGHT, padx=5)
        ttk.Button(frame_buttons, text="Confirm Selection",
                   command=self._confirm_selection).pack(side=tk.RIGHT, padx=5)

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
    #files = select_ndax_files()  # Return mode
    select_ndax_files(callback=test_callback)  # Callback mode