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

    def select_files(self):
        """
        Open a GUI file dialog for selecting .ndax files.

        Returns:
            list: List of selected file paths.
        """
        root = tk.Tk()
        root.withdraw()  # Hide the main window

        files = filedialog.askopenfilenames(
            title="Select Neware NDAX Files",
            initialdir=self.initial_dir,
            filetypes=[("NDAX Files", "*.ndax"), ("All Files", "*.*")]
        )

        self.selected_files = [str(Path(file)) for file in files]
        return self.selected_files

    def select_files_with_preview(self):
        """
        Open a more advanced GUI with file selection and preview capabilities.

        Returns:
            list: List of selected file paths.
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
            root.destroy()

        def cancel_selection():
            self.selected_files = []
            root.destroy()

        ttk.Button(frame_buttons, text="Confirm Selection", command=confirm_selection).pack(side=tk.RIGHT, padx=5)
        ttk.Button(frame_buttons, text="Cancel", command=cancel_selection).pack(side=tk.RIGHT, padx=5)

        # Initialize file list
        update_file_list()

        # Start the GUI event loop
        root.mainloop()

        return self.selected_files


def select_ndax_files(initial_dir=None, advanced=True):
    """
    Convenience function to select .ndax files using a GUI.

    Args:
        initial_dir (str, optional): Initial directory to open the file dialog.
        advanced (bool, optional): Whether to use the advanced GUI with preview.

    Returns:
        list: List of selected file paths.
    """
    selector = FileSelector(initial_dir)
    if advanced:
        return selector.select_files_with_preview()
    else:
        return selector.select_files()


if __name__ == "__main__":
    # Test the file selector
    files = select_ndax_files()
    print("Selected files:")
    for file in files:
        print(f"  - {file}")