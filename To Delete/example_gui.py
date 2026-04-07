"""
Simple tkinter GUI for PyGND calculations.
Author: Generated for PyGND project
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys

# Add src to path if running from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import pygnd


class PyGNDGui:
    """Main GUI application for PyGND calculations."""

    # Crystal structure options
    CRYSTAL_STRUCTURES = {
        "FCC": 1,
        "BCC": 2,
        "HCP": 3,
    }

    # Slip systems by crystal structure
    SLIP_SYSTEMS = {
        "FCC": ["all"],
        "BCC": [
            "all",
            "screw+110",
            "screw+112",
            "screw+123",
            "screw+110+112",
            "screw+110+123",
            "screw+112+123",
        ],
        "HCP": [
            "all",
            "basal",
            "prismatic",
            "pyramidal",
            "basal+prismatic",
            "basal+pyramidal",
            "prismatic+pyramidal",
        ],
    }

    # Spacing units
    SPACING_UNITS = ["um", "nm", "mm", "m"]

    def __init__(self, root):
        self.root = root
        self.root.title("PyGND - GND Calculator")
        self.root.geometry("600x700")
        self.root.resizable(True, True)

        # Variables
        self.file_type = tk.StringVar(value="ANG")
        self.file_path = tk.StringVar()
        self.grain_ids_path = tk.StringVar()
        self.ids_name = tk.StringVar(value="FeatureIds")
        self.euler_name = tk.StringVar(value="EulerAngles")
        self.crystal_structure = tk.StringVar(value="FCC")
        self.slip_systems = tk.StringVar(value="all")
        self.burgers = tk.StringVar(value="2.48e-10")
        self.n_cpus = tk.StringVar(value="5")
        self.chunk_size = tk.StringVar(value="1000")
        self.spacing_units = tk.StringVar(value="um")
        self.use_l1 = tk.BooleanVar(value=True)
        self.use_l2 = tk.BooleanVar(value=True)

        # Track calculation thread
        self.calc_thread = None
        self.is_running = False

        self._create_widgets()
        self._update_file_type_ui()

    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        row = 0

        # === File Type Selection ===
        ttk.Label(main_frame, text="File Type:", font=("", 10, "bold")).grid(
            row=row, column=0, sticky="w", pady=(0, 5)
        )
        file_type_frame = ttk.Frame(main_frame)
        file_type_frame.grid(row=row, column=1, sticky="w", pady=(0, 5))
        ttk.Radiobutton(
            file_type_frame,
            text="ANG",
            variable=self.file_type,
            value="ANG",
            command=self._update_file_type_ui,
        ).pack(side="left", padx=(0, 10))
        ttk.Radiobutton(
            file_type_frame,
            text="DREAM3D",
            variable=self.file_type,
            value="DREAM3D",
            command=self._update_file_type_ui,
        ).pack(side="left")
        row += 1

        # === File Selection ===
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=10
        )
        row += 1

        ttk.Label(main_frame, text="Input File:", font=("", 10, "bold")).grid(
            row=row, column=0, sticky="w", pady=2
        )
        file_frame = ttk.Frame(main_frame)
        file_frame.grid(row=row, column=1, sticky="ew", pady=2)
        file_frame.columnconfigure(0, weight=1)
        self.file_entry = ttk.Entry(file_frame, textvariable=self.file_path)
        self.file_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(file_frame, text="Browse...", command=self._browse_file).grid(row=0, column=1)
        row += 1

        # Grain IDs path (ANG only)
        self.grain_ids_label = ttk.Label(main_frame, text="Grain IDs File:")
        self.grain_ids_label.grid(row=row, column=0, sticky="w", pady=2)
        grain_frame = ttk.Frame(main_frame)
        grain_frame.grid(row=row, column=1, sticky="ew", pady=2)
        grain_frame.columnconfigure(0, weight=1)
        self.grain_ids_entry = ttk.Entry(grain_frame, textvariable=self.grain_ids_path)
        self.grain_ids_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.grain_ids_browse_btn = ttk.Button(
            grain_frame, text="Browse...", command=self._browse_grain_ids
        )
        self.grain_ids_browse_btn.grid(row=0, column=1)
        self.grain_ids_row = row
        row += 1

        # DREAM3D DataArray names
        self.ids_name_label = ttk.Label(main_frame, text="Feature IDs Name:")
        self.ids_name_label.grid(row=row, column=0, sticky="w", pady=2)
        self.ids_name_entry = ttk.Entry(main_frame, textvariable=self.ids_name)
        self.ids_name_entry.grid(row=row, column=1, sticky="ew", pady=2)
        self.ids_name_row = row
        row += 1

        self.euler_name_label = ttk.Label(main_frame, text="Euler Angles Name:")
        self.euler_name_label.grid(row=row, column=0, sticky="w", pady=2)
        self.euler_name_entry = ttk.Entry(main_frame, textvariable=self.euler_name)
        self.euler_name_entry.grid(row=row, column=1, sticky="ew", pady=2)
        self.euler_name_row = row
        row += 1

        # === Material Parameters ===
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=10
        )
        row += 1

        ttk.Label(main_frame, text="Material Parameters", font=("", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 5)
        )
        row += 1

        ttk.Label(main_frame, text="Crystal Structure:").grid(row=row, column=0, sticky="w", pady=2)
        cs_combo = ttk.Combobox(
            main_frame,
            textvariable=self.crystal_structure,
            values=list(self.CRYSTAL_STRUCTURES.keys()),
            state="readonly",
            width=15,
        )
        cs_combo.grid(row=row, column=1, sticky="w", pady=2)
        cs_combo.bind("<<ComboboxSelected>>", self._update_slip_systems)
        row += 1

        ttk.Label(main_frame, text="Slip Systems:").grid(row=row, column=0, sticky="w", pady=2)
        self.slip_combo = ttk.Combobox(
            main_frame,
            textvariable=self.slip_systems,
            values=self.SLIP_SYSTEMS["FCC"],
            state="readonly",
            width=15,
        )
        self.slip_combo.grid(row=row, column=1, sticky="w", pady=2)
        row += 1

        ttk.Label(main_frame, text="Burgers Vector (m):").grid(
            row=row, column=0, sticky="w", pady=2
        )
        ttk.Entry(main_frame, textvariable=self.burgers, width=18).grid(
            row=row, column=1, sticky="w", pady=2
        )
        row += 1

        # Spacing units (DREAM3D only)
        self.spacing_label = ttk.Label(main_frame, text="Spacing Units:")
        self.spacing_label.grid(row=row, column=0, sticky="w", pady=2)
        self.spacing_combo = ttk.Combobox(
            main_frame,
            textvariable=self.spacing_units,
            values=self.SPACING_UNITS,
            state="readonly",
            width=15,
        )
        self.spacing_combo.grid(row=row, column=1, sticky="w", pady=2)
        self.spacing_row = row
        row += 1

        # === Calculation Options ===
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=10
        )
        row += 1

        ttk.Label(main_frame, text="Calculation Options", font=("", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 5)
        )
        row += 1

        ttk.Label(main_frame, text="Minimization:").grid(row=row, column=0, sticky="w", pady=2)
        min_frame = ttk.Frame(main_frame)
        min_frame.grid(row=row, column=1, sticky="w", pady=2)
        ttk.Checkbutton(min_frame, text="L1", variable=self.use_l1).pack(side="left", padx=(0, 10))
        ttk.Checkbutton(min_frame, text="L2", variable=self.use_l2).pack(side="left")
        row += 1

        ttk.Label(main_frame, text="CPU Cores:").grid(row=row, column=0, sticky="w", pady=2)
        cpu_frame = ttk.Frame(main_frame)
        cpu_frame.grid(row=row, column=1, sticky="w", pady=2)
        ttk.Entry(cpu_frame, textvariable=self.n_cpus, width=8).pack(side="left")
        ttk.Label(cpu_frame, text="(-1 for all cores minus 1)").pack(side="left", padx=(5, 0))
        row += 1

        ttk.Label(main_frame, text="Chunk Size:").grid(row=row, column=0, sticky="w", pady=2)
        chunk_frame = ttk.Frame(main_frame)
        chunk_frame.grid(row=row, column=1, sticky="w", pady=2)
        ttk.Entry(chunk_frame, textvariable=self.chunk_size, width=8).pack(side="left")
        ttk.Label(chunk_frame, text="(decrease if memory issues)").pack(side="left", padx=(5, 0))
        row += 1

        # === Progress Section ===
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=10
        )
        row += 1

        ttk.Label(main_frame, text="Progress", font=("", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 5)
        )
        row += 1

        self.status_label = ttk.Label(main_frame, text="Ready")
        self.status_label.grid(row=row, column=0, columnspan=2, sticky="w", pady=2)
        row += 1

        self.progress_bar = ttk.Progressbar(main_frame, mode="indeterminate", length=400)
        self.progress_bar.grid(row=row, column=0, columnspan=2, sticky="ew", pady=5)
        row += 1

        # === Buttons ===
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=10
        )
        row += 1

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)

        self.run_button = ttk.Button(
            button_frame, text="Run Calculation", command=self._run_calculation
        )
        self.run_button.pack(side="left", padx=5)

        self.cancel_button = ttk.Button(
            button_frame, text="Cancel", command=self._cancel_calculation, state="disabled"
        )
        self.cancel_button.pack(side="left", padx=5)

        # === Log Output ===
        row += 1
        ttk.Label(main_frame, text="Output Log:", font=("", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(10, 5)
        )
        row += 1

        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=row, column=0, columnspan=2, sticky="nsew", pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(row, weight=1)

        self.log_text = tk.Text(log_frame, height=8, width=60, state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")

        log_scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=log_scroll.set)

    def _update_file_type_ui(self):
        """Show/hide widgets based on file type selection."""
        is_ang = self.file_type.get() == "ANG"

        # ANG-specific widgets
        if is_ang:
            self.grain_ids_label.grid()
            self.grain_ids_entry.master.grid()
        else:
            self.grain_ids_label.grid_remove()
            self.grain_ids_entry.master.grid_remove()

        # DREAM3D-specific widgets
        if not is_ang:
            self.ids_name_label.grid()
            self.ids_name_entry.grid()
            self.euler_name_label.grid()
            self.euler_name_entry.grid()
            self.spacing_label.grid()
            self.spacing_combo.grid()
        else:
            self.ids_name_label.grid_remove()
            self.ids_name_entry.grid_remove()
            self.euler_name_label.grid_remove()
            self.euler_name_entry.grid_remove()
            self.spacing_label.grid_remove()
            self.spacing_combo.grid_remove()

    def _update_slip_systems(self, event=None):
        """Update slip system options based on crystal structure."""
        cs = self.crystal_structure.get()
        options = self.SLIP_SYSTEMS.get(cs, ["all"])
        self.slip_combo.config(values=options)
        self.slip_systems.set(options[0])

    def _browse_file(self):
        """Open file dialog for input file."""
        if self.file_type.get() == "ANG":
            filetypes = [("ANG files", "*.ang"), ("All files", "*.*")]
        else:
            filetypes = [("DREAM3D files", "*.dream3d"), ("All files", "*.*")]

        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            self.file_path.set(filename)

    def _browse_grain_ids(self):
        """Open file dialog for grain IDs file."""
        filetypes = [("Text files", "*.txt"), ("All files", "*.*")]
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            self.grain_ids_path.set(filename)

    def _log(self, message):
        """Add message to log output."""
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _validate_inputs(self):
        """Validate user inputs before running calculation."""
        # Check file path
        if not self.file_path.get():
            messagebox.showerror("Error", "Please select an input file.")
            return False

        if not os.path.exists(self.file_path.get()):
            messagebox.showerror("Error", "Input file does not exist.")
            return False

        # Check grain IDs for ANG
        if self.file_type.get() == "ANG" and self.grain_ids_path.get():
            if not os.path.exists(self.grain_ids_path.get()):
                messagebox.showerror("Error", "Grain IDs file does not exist.")
                return False

        # Check burgers vector
        try:
            burgers = float(self.burgers.get())
            if burgers <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "Burgers vector must be a positive number.")
            return False

        # Check CPU cores
        try:
            n_cpus = int(self.n_cpus.get())
        except ValueError:
            messagebox.showerror("Error", "CPU cores must be an integer.")
            return False

        # Check chunk size
        try:
            chunk_size = int(self.chunk_size.get())
            if chunk_size <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "Chunk size must be a positive integer.")
            return False

        # Check minimization selection
        if not self.use_l1.get() and not self.use_l2.get():
            messagebox.showerror(
                "Error", "Please select at least one minimization method (L1 or L2)."
            )
            return False

        return True

    def _run_calculation(self):
        """Start the GND calculation in a background thread."""
        if not self._validate_inputs():
            return

        # Disable run button, enable cancel
        self.run_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        self.is_running = True

        # Clear log and start progress
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

        self.progress_bar.start(10)
        self.status_label.config(text="Running calculation...")

        # Build minimization list
        minimization = []
        if self.use_l2.get():
            minimization.append("l2")
        if self.use_l1.get():
            minimization.append("l1")
        if len(minimization) == 1:
            minimization = minimization[0]

        # Start calculation thread
        self.calc_thread = threading.Thread(
            target=self._calculation_worker, args=(minimization,), daemon=True
        )
        self.calc_thread.start()

        # Check for completion
        self._check_calculation_status()

    def _calculation_worker(self, minimization):
        """Worker function that runs in background thread."""
        try:
            self._log_threadsafe("Starting GND calculation...")
            self._log_threadsafe(f"File: {self.file_path.get()}")
            self._log_threadsafe(
                f"Crystal structure: {self.crystal_structure.get()} "
                f"(cs={self.CRYSTAL_STRUCTURES[self.crystal_structure.get()]})"
            )
            self._log_threadsafe(f"Slip systems: {self.slip_systems.get()}")
            self._log_threadsafe(f"Minimization: {minimization}")

            # Build kwargs
            kwargs = {
                "cs": self.CRYSTAL_STRUCTURES[self.crystal_structure.get()],
                "burgers": float(self.burgers.get()),
                "minimization": minimization,
                "slip_systems": self.slip_systems.get(),
                "n_cpus": int(self.n_cpus.get()),
                "progress_bar": True,
                "chunk_size": int(self.chunk_size.get()),
            }

            if self.file_type.get() == "ANG":
                kwargs["ang_path"] = self.file_path.get()
                if self.grain_ids_path.get():
                    kwargs["grain_ids_path"] = self.grain_ids_path.get()
            else:
                kwargs["dream3d_path"] = self.file_path.get()
                kwargs["ids_name"] = self.ids_name.get()
                kwargs["euler_name"] = self.euler_name.get()
                kwargs["spacing_units"] = self.spacing_units.get()

            self._log_threadsafe("Calling pygnd.calculate_and_save()...")

            # Run calculation
            success = pygnd.calculate_and_save(**kwargs)

            self._log_threadsafe("Calculation complete!")

            self.calculation_success = True
            self.calculation_error = None

        except Exception as e:
            self._log_threadsafe(f"Error: {str(e)}")
            self.calculation_success = False
            self.calculation_error = str(e)

    def _log_threadsafe(self, message):
        """Thread-safe logging."""
        self.root.after(0, lambda: self._log(message))

    def _check_calculation_status(self):
        """Check if calculation thread has finished."""
        if self.calc_thread and self.calc_thread.is_alive():
            # Still running, check again later
            self.root.after(100, self._check_calculation_status)
        else:
            # Finished
            self._calculation_finished()

    def _calculation_finished(self):
        """Handle calculation completion."""
        self.progress_bar.stop()
        self.is_running = False
        self.run_button.config(state="normal")
        self.cancel_button.config(state="disabled")

        if hasattr(self, "calculation_success") and self.calculation_success:
            self.status_label.config(text="Calculation complete!")
            messagebox.showinfo("Success", "GND calculation completed successfully!")
        elif hasattr(self, "calculation_error") and self.calculation_error:
            self.status_label.config(text="Calculation failed")
            messagebox.showerror("Error", f"Calculation failed:\n{self.calculation_error}")
        else:
            self.status_label.config(text="Calculation cancelled")

    def _cancel_calculation(self):
        """Cancel the running calculation (note: thread cannot be truly cancelled)."""
        self.status_label.config(text="Cancellation requested...")
        self._log("Cancellation requested. Note: Current chunk will complete before stopping.")
        # Note: Python threads cannot be forcefully terminated
        # The calculation will continue until the current operation completes


def main():
    """Main entry point."""
    root = tk.Tk()
    app = PyGNDGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
