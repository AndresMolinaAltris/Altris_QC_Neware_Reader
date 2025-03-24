import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import os
from pathlib import Path


class FileSelector:
    """A GUI for selecting one or multiple .ndax files."""

    def __init__(self, initial_dir=None):
        """
        Initialize the file selector.

        Args:
            initial_dir (str, optional): Initial directory to open the file dialog.
        """
        self.initial_dir = initial_dir or os.getcwd()
        self.selected_files = []


    def select_files_with_preview(self, process_callback=None):
        """
        Open a more advanced GUI with file selection and preview capabilities.

        Args:
            process_callback (function, optional): Function to call with selected files when
                                                 "Process Files" button is clicked.

        Returns:
            list: List of selected file paths if no callback is provided.
        """
        # Create the main window
        root = tk.Tk()
        root.title("Neware NDAX File Selector")
        root.geometry("800x500")

        # Variables
        self.selected_files = []
        file_list_var = tk.StringVar()
        current_dir = tk.StringVar(value=self.initial_dir)

        # Frame layout
        frame_top = ttk.Frame(root)
        frame_top.pack(fill=tk.X, padx=10, pady=10)

        frame_files = ttk.Frame(root)
        frame_files.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        frame_buttons = ttk.Frame(root)
        frame_buttons.pack(fill=tk.X, padx=10, pady=10)

        # Directory selection
        ttk.Label(frame_top, text="Directory:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(frame_top, textvariable=current_dir, width=60).pack(side=tk.LEFT, padx=(0, 5))

        def browse_directory():
            dir_path = filedialog.askdirectory(initialdir=current_dir.get())
            if dir_path:
                current_dir.set(dir_path)
                update_file_list()

        ttk.Button(frame_top, text="Browse...", command=browse_directory).pack(side=tk.LEFT)

        # File listbox with scrollbar
        file_frame = ttk.LabelFrame(frame_files, text="Available NDAX Files")
        file_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=(0, 5))

        scrollbar = ttk.Scrollbar(file_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(file_frame, selectmode=tk.EXTENDED, yscrollcommand=scrollbar.set)
        listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)

        # Selected files frame
        selected_frame = ttk.LabelFrame(frame_files, text="Selected Files")
        selected_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)

        selected_scrollbar = ttk.Scrollbar(selected_frame)
        selected_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        selected_listbox = tk.Listbox(selected_frame, yscrollcommand=selected_scrollbar.set)
        selected_listbox.pack(fill=tk.BOTH, expand=True)
        selected_scrollbar.config(command=selected_listbox.yview)

        # Update file list based on directory
        def update_file_list():
            listbox.delete(0, tk.END)
            try:
                for file in os.listdir(current_dir.get()):
                    if file.endswith(".ndax"):
                        listbox.insert(tk.END, file)
            except Exception as e:
                tk.messagebox.showerror("Error", f"Could not list directory: {str(e)}")

        # Add/Remove file selection
        def add_selection():
            selected_indices = listbox.curselection()
            for i in selected_indices:
                file = listbox.get(i)
                full_path = os.path.join(current_dir.get(), file)
                if full_path not in self.selected_files:
                    self.selected_files.append(full_path)
                    selected_listbox.insert(tk.END, file)

        def remove_selection():
            selected_indices = selected_listbox.curselection()
            # Reverse to avoid index shifting during deletion
            for i in sorted(selected_indices, reverse=True):
                file = selected_listbox.get(i)
                full_path = next((f for f in self.selected_files if os.path.basename(f) == file), None)
                if full_path in self.selected_files:
                    self.selected_files.remove(full_path)
                selected_listbox.delete(i)

        # Button frames
        add_remove_frame = ttk.Frame(frame_files)
        add_remove_frame.pack(fill=tk.Y, padx=5)

        ttk.Button(add_remove_frame, text=">>", command=add_selection).pack(pady=5)
        ttk.Button(add_remove_frame, text="<<", command=remove_selection).pack(pady=5)

        # Bottom buttons
        def confirm_selection():
            # Instead of destroying the window, return the selection and show a confirmation
            if self.selected_files:
                messagebox.showinfo("Selection Confirmed",
                                    f"{len(self.selected_files)} files selected. You can continue selecting more files.")
            else:
                messagebox.showwarning("No Selection",
                                       "No files are currently selected. Please select files before confirming.")

        def process_files():
            # Process the currently selected files
            if not self.selected_files:
                messagebox.showwarning("No Selection",
                                       "No files are currently selected. Please select files before processing.")
                return

            # If we have a callback function, call it with the selected files
            if process_callback:
                # Create a copy of the selected files
                files_to_process = self.selected_files.copy()

                # Show a processing message
                status_var.set(f"Processing {len(files_to_process)} files...")
                root.update()

                # Call the callback function with the list of files
                process_callback(files_to_process)

                # Update status to show completion
                status_var.set(f"Processed {len(files_to_process)} files. Ready for next batch.")
            else:
                # If no callback, just confirm and return
                messagebox.showinfo("Files Ready for Processing",
                                    f"{len(self.selected_files)} files ready to be processed.")
                root.destroy()

        def cancel_selection():
            self.selected_files = []
            messagebox.showinfo("Selection Cleared", "File selection has been cleared.")

        def finish_and_close():
            # New method to close the window when done with all selections
            if messagebox.askyesno("Confirm Exit", "Are you sure you want to exit the file selector?"):
                root.destroy()

        ttk.Button(frame_buttons, text="Confirm Selection", command=confirm_selection).pack(side=tk.RIGHT, padx=5)
        ttk.Button(frame_buttons, text="Process Files", command=process_files).pack(side=tk.RIGHT, padx=5)
        ttk.Button(frame_buttons, text="Clear Selection", command=cancel_selection).pack(side=tk.RIGHT, padx=5)
        ttk.Button(frame_buttons, text="Exit", command=finish_and_close).pack(side=tk.RIGHT, padx=5)

        # Initialize file list
        update_file_list()

        # Add status label to show currently selected files count
        status_var = tk.StringVar(value="No files selected")
        status_label = ttk.Label(frame_buttons, textvariable=status_var)
        status_label.pack(side=tk.LEFT, padx=5)

        # Update status periodically
        def update_status():
            file_count = len(self.selected_files)
            if file_count == 0:
                status_var.set("No files selected")
            elif file_count == 1:
                status_var.set("1 file selected")
            else:
                status_var.set(f"{file_count} files selected")
            root.after(500, update_status)

        # Start status updates
        update_status()

        # Start the GUI event loop
        root.mainloop()

        # If we're not using a callback, return the selected files
        if not process_callback:
            return self.selected_files
        # Otherwise return None (the callback will handle processing)
        return None


def select_ndax_files(initial_dir=None, callback=None):
    """
    Convenience function to select .ndax files using a GUI.

    Args:
        initial_dir (str, optional): Initial directory to open the file dialog.
        callback (function, optional): Function to call when files are selected and confirmed.

    Returns:
        list: List of selected file paths if no callback is provided.
    """
    selector = FileSelector(initial_dir)
    return selector.select_files_with_preview(callback)


if __name__ == "__main__":
    # Test the file selector
    files = select_ndax_files()
    print("Selected files:")
    for file in files:
        print(f"  - {file}")