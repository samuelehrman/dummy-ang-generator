"""
GUI for ANG Generator from UP2 files.
Wraps the logic from AngGeneratorFromUP2.py with a tkinter interface.
"""

# GUI template modelled from James Lamb GND GUI: https://github.com/PollockGroup/TriBeam_GND


import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import struct


class AngGeneratorGui:
    """Main GUI application for generating ANG files from UP2 files."""

    def __init__(self, root):
        self.root = root
        self.root.title("ANG Generator from UP2")
        self.root.geometry("620x620")
        self.root.resizable(True, True)

        # Variables
        self.up2_path = tk.StringVar()
        self.ang_output_dir = tk.StringVar()
        self.ang_file_name = tk.StringVar()
        self.pc_x = tk.StringVar(value="0.5")
        self.pc_y = tk.StringVar(value="0.7")
        self.pc_z = tk.StringVar(value="0.67")
        self.s_tilt = tk.StringVar(value="70")
        self.c_elev = tk.StringVar(value="10")

        self.gen_thread = None
        self.is_running = False
        self.generation_success = False
        self.generation_error = None

        self._create_widgets()

    def _create_widgets(self):
        """Create all GUI widgets."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        row = 0

        # === Input File ===
        ttk.Label(main_frame, text="Input File", font=("", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 5)
        )
        row += 1

        ttk.Label(main_frame, text="UP2 File:").grid(row=row, column=0, sticky="w", pady=2)
        up2_frame = ttk.Frame(main_frame)
        up2_frame.grid(row=row, column=1, sticky="ew", pady=2)
        up2_frame.columnconfigure(0, weight=1)
        ttk.Entry(up2_frame, textvariable=self.up2_path).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ttk.Button(up2_frame, text="Browse...", command=self._browse_up2).grid(row=0, column=1)
        row += 1

        # === Output ===
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=10
        )
        row += 1

        ttk.Label(main_frame, text="Output", font=("", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 5)
        )
        row += 1

        ttk.Label(main_frame, text="ANG Output Path:").grid(row=row, column=0, sticky="w", pady=2)
        ang_dir_frame = ttk.Frame(main_frame)
        ang_dir_frame.grid(row=row, column=1, sticky="ew", pady=2)
        ang_dir_frame.columnconfigure(0, weight=1)
        ttk.Entry(ang_dir_frame, textvariable=self.ang_output_dir).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ttk.Button(ang_dir_frame, text="Browse...", command=self._browse_ang_dir).grid(
            row=0, column=1
        )
        row += 1

        ttk.Label(main_frame, text="ANG File Name:").grid(row=row, column=0, sticky="w", pady=2)
        name_frame = ttk.Frame(main_frame)
        name_frame.grid(row=row, column=1, sticky="ew", pady=2)
        name_frame.columnconfigure(0, weight=1)
        ttk.Entry(name_frame, textvariable=self.ang_file_name).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ttk.Label(name_frame, text="(leave blank to use UP2 name)", foreground="gray").grid(
            row=0, column=1
        )
        row += 1

        # === Pattern Center ===
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=10
        )
        row += 1

        ttk.Label(main_frame, text="Pattern Center", font=("", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 5)
        )
        row += 1

        pc_frame = ttk.Frame(main_frame)
        pc_frame.grid(row=row, column=0, columnspan=2, sticky="w", pady=2)
        ttk.Label(pc_frame, text="PC X (xstar):").grid(row=0, column=0, sticky="w", padx=(0, 5))
        ttk.Entry(pc_frame, textvariable=self.pc_x, width=8).grid(
            row=0, column=1, padx=(0, 20)
        )
        ttk.Label(pc_frame, text="PC Y (ystar):").grid(row=0, column=2, sticky="w", padx=(0, 5))
        ttk.Entry(pc_frame, textvariable=self.pc_y, width=8).grid(
            row=0, column=3, padx=(0, 20)
        )
        ttk.Label(pc_frame, text="PC Z (zstar):").grid(row=0, column=4, sticky="w", padx=(0, 5))
        ttk.Entry(pc_frame, textvariable=self.pc_z, width=8).grid(row=0, column=5)
        row += 1

        # === Geometry ===
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=10
        )
        row += 1

        ttk.Label(main_frame, text="Geometry", font=("", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 5)
        )
        row += 1

        geom_frame = ttk.Frame(main_frame)
        geom_frame.grid(row=row, column=0, columnspan=2, sticky="w", pady=2)
        ttk.Label(geom_frame, text="Sample Tilt (sTilt):").grid(
            row=0, column=0, sticky="w", padx=(0, 5)
        )
        ttk.Entry(geom_frame, textvariable=self.s_tilt, width=8).grid(
            row=0, column=1, padx=(0, 30)
        )
        ttk.Label(geom_frame, text="Camera Elevation (cElev):").grid(
            row=0, column=2, sticky="w", padx=(0, 5)
        )
        ttk.Entry(geom_frame, textvariable=self.c_elev, width=8).grid(row=0, column=3)
        row += 1

        # === Progress ===
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=10
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
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)
        self.run_button = ttk.Button(
            button_frame, text="Generate ANG", command=self._run_generation
        )
        self.run_button.pack(side="left", padx=5)
        row += 1

        # === Output Log ===
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=10
        )
        row += 1

        ttk.Label(main_frame, text="Output Log:", font=("", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 5)
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

    # ------------------------------------------------------------------
    # Browse helpers
    # ------------------------------------------------------------------

    def _browse_up2(self):
        """Open file dialog for the UP2 input file."""
        filename = filedialog.askopenfilename(
            filetypes=[("UP2 files", "*.up2"), ("UP files", "*.up1 *.up2"), ("All files", "*.*")]
        )
        if filename:
            self.up2_path.set(filename)
            # Auto-populate output directory if currently empty
            if not self.ang_output_dir.get():
                self.ang_output_dir.set(os.path.dirname(filename))

    def _browse_ang_dir(self):
        """Open directory dialog for the ANG output folder."""
        directory = filedialog.askdirectory()
        if directory:
            self.ang_output_dir.set(directory)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, message):
        """Append a line to the output log."""
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _log_threadsafe(self, message):
        """Thread-safe wrapper for _log."""
        self.root.after(0, lambda m=message: self._log(m))

    # ------------------------------------------------------------------
    # Dimension picker dialog (called from main thread)
    # ------------------------------------------------------------------

    def _ask_dimensions(self, options, result_holder, event):
        """Show a Toplevel dialog listing candidate (cols, rows) pairs.
        Stores the chosen (cols, rows) tuple in result_holder[0] and sets event.
        Called on the main thread via root.after().
        """
        dlg = tk.Toplevel(self.root)
        dlg.title("Select Scan Dimensions")
        dlg.resizable(False, False)
        dlg.grab_set()  # modal

        ttk.Label(
            dlg,
            text="The UP2 file does not contain scan dimensions.\n"
                 "Select the correct (cols \u00d7 rows) from the candidates below:",
            justify="left",
            padding=(10, 10, 10, 5),
        ).pack(fill="x")

        frame = ttk.Frame(dlg, padding=(10, 0, 10, 0))
        frame.pack(fill="both", expand=True)

        listbox = tk.Listbox(frame, selectmode="single", height=min(len(options), 10), width=25)
        listbox.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(frame, command=listbox.yview)
        sb.pack(side="right", fill="y")
        listbox.config(yscrollcommand=sb.set)

        for c, r in options:
            listbox.insert("end", f"{c} cols \u00d7 {r} rows")
        listbox.selection_set(0)

        def on_ok():
            sel = listbox.curselection()
            if not sel:
                return
            result_holder[0] = options[sel[0]]
            dlg.destroy()
            event.set()

        def on_cancel():
            result_holder[0] = None
            dlg.destroy()
            event.set()

        dlg.protocol("WM_DELETE_WINDOW", on_cancel)

        btn_frame = ttk.Frame(dlg, padding=(10, 5, 10, 10))
        btn_frame.pack()
        ttk.Button(btn_frame, text="OK", command=on_ok, width=10).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=on_cancel, width=10).pack(side="left", padx=5)

        dlg.update_idletasks()
        # Centre over root window
        x = self.root.winfo_x() + (self.root.winfo_width() - dlg.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dlg.winfo_height()) // 2
        dlg.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_inputs(self):
        """Validate all inputs before running. Returns True if valid."""
        up2 = self.up2_path.get().strip()
        if not up2:
            messagebox.showerror("Error", "Please select a UP2 file.")
            return False
        if not os.path.exists(up2):
            messagebox.showerror("Error", "UP2 file does not exist.")
            return False

        ang_dir = self.ang_output_dir.get().strip()
        if not ang_dir:
            messagebox.showerror("Error", "Please specify an ANG output path.")
            return False
        if not os.path.isdir(ang_dir):
            messagebox.showerror("Error", "ANG output path is not a valid directory.")
            return False

        for label, var in [
            ("PC X", self.pc_x),
            ("PC Y", self.pc_y),
            ("PC Z", self.pc_z),
            ("sTilt", self.s_tilt),
            ("cElev", self.c_elev),
        ]:
            try:
                float(var.get())
            except ValueError:
                messagebox.showerror("Error", f"{label} must be a number.")
                return False

        return True

    def _resolve_ang_path(self):
        """Build the full ANG output path, falling back to the UP2 filename."""
        ang_dir = self.ang_output_dir.get().strip()
        ang_name = self.ang_file_name.get().strip()
        if not ang_name:
            base = os.path.splitext(os.path.basename(self.up2_path.get().strip()))[0]
            ang_name = base + ".ang"
        elif not ang_name.lower().endswith(".ang"):
            ang_name += ".ang"
        return os.path.join(ang_dir, ang_name)

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def _run_generation(self):
        """Validate inputs and start the generation worker thread."""
        if not self._validate_inputs():
            return

        self.run_button.config(state="disabled")
        self.is_running = True

        # Clear previous log
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

        self.progress_bar.start(10)
        self.status_label.config(text="Generating ANG file...")

        self.gen_thread = threading.Thread(target=self._generation_worker, daemon=True)
        self.gen_thread.start()
        self._check_generation_status()

    def _generation_worker(self):
        """Worker that runs the ANG generation logic in a background thread."""
        try:
            up2_path = self.up2_path.get().strip()
            ang_path = self._resolve_ang_path()
            xstar = float(self.pc_x.get())
            ystar = float(self.pc_y.get())
            zstar = float(self.pc_z.get())
            s_tilt = float(self.s_tilt.get())
            c_elev = float(self.c_elev.get())

            self._log_threadsafe(f"UP2 file:   {up2_path}")
            self._log_threadsafe(f"ANG output: {ang_path}")
            self._log_threadsafe(
                f"xstar={xstar}, ystar={ystar}, zstar={zstar}, "
                f"sTilt={s_tilt}, cElev={c_elev}"
            )
            self._log_threadsafe("Reading UP2 header...")

            cols = None
            rows = None
            dx = None
            dy = None

            with open(up2_path, 'rb') as f:
                # version, pat cols, pat rows, data offset, extra pattern flag,
                # scan cols, scan rows, hex/square flag, x step, y step
                hdr_fmt = '<iiiiBiiBdd'
                hdr_len = struct.calcsize(hdr_fmt)
                hdr_bytes = f.read(hdr_len)
                if not hdr_bytes:
                    raise RuntimeError("Failed to read UP2 header (file may be empty).")
                s = struct.Struct(hdr_fmt).unpack_from(hdr_bytes)
                version = s[0]
                if version < 1 or version > 4:
                    raise RuntimeError(f"Unsupported UP2 version: {version}")

                if version > 2:
                    cols = s[5]
                    rows = s[6]
                    dx   = s[8]
                    dy   = s[9]
                else:
                    pat_cols = s[1]
                    pat_rows = s[2]
                    data_offset = s[3]
                    f_bytes = os.path.getsize(up2_path) - data_offset
                    p_bytes = pat_cols * pat_rows
                    if up2_path.lower().endswith('2'):
                        p_bytes = p_bytes * 2
                    else:
                        raise RuntimeError(
                            "Cannot determine bit depth for this file. "
                            "Expected a .up2 file."
                        )
                    num_pats = round(f_bytes / p_bytes)
                    if cols is None or rows is None or cols * rows != num_pats:
                        # Compute candidate dimensions (same logic as AngGeneratorFromUP2.py)
                        tgt_sq = num_pats ** 0.5
                        min_x = round(tgt_sq * 0.5 ** 0.5)
                        max_x = round(tgt_sq)
                        candidates = [
                            (i, round(num_pats / i))
                            for i in range(min_x, max_x + 1)
                            if num_pats % i == 0
                        ]
                        self._log_threadsafe(
                            f"File contains {num_pats} patterns. "
                            f"Scan dimensions not stored — found {len(candidates)} candidate(s)."
                        )
                        if not candidates:
                            raise RuntimeError(
                                f"No valid (cols x rows) factorisation found for {num_pats} patterns."
                            )
                        # Pause and ask the user on the main thread
                        result_holder = [None]
                        dim_event = threading.Event()
                        self.root.after(
                            0,
                            lambda c=candidates, r=result_holder, e=dim_event:
                                self._ask_dimensions(c, r, e),
                        )
                        dim_event.wait()  # block worker until user picks
                        if result_holder[0] is None:
                            raise RuntimeError("Dimension selection cancelled by user.")
                        cols, rows = result_holder[0]
                        self._log_threadsafe(f"User selected: {cols} cols x {rows} rows")

            if dx is None:
                dx = 1.0
            if dy is None:
                dy = 1.0

            self._log_threadsafe(
                f"Scan dimensions: {cols} cols x {rows} rows, "
                f"dx={dx:.6g}, dy={dy:.6g}"
            )
            self._log_threadsafe("Writing ANG file...")

            with open(ang_path, 'w') as f:
                f.write('# x-star %f\n# y-star %f\n# z-star %f\n' % (xstar, ystar, zstar))
                f.write(
                    '# WorkingDistance 10.0\n'
                    '# SampleTiltAngle %f\n'
                    '# CameraElevationAngle %f\n'
                    '# CameraAzimuthalAngle 0.\n' % (s_tilt, c_elev)
                )
                f.write('# GRID: SqrGrid\n# XSTEP: %f\n# YSTEP: %f\n' % (dx, dy))
                f.write(
                    '# NCOLS_ODD: %i\n# NCOLS_EVEN: %i\n# NROWS: %i\n' % (cols, cols, rows)
                )
                f.write(
                    '# Phase 1\n'
                    '# MaterialName <unknown>\n'
                    '# Symmetry 1\n'
                    '# LatticeConstants 3. 4. 5. 70. 80. 100.\n'
                    '# NumberFamilies 0\n'
                )

                x = [dx * i for i in range(cols)]
                y = [dy * i for i in range(rows)]
                for j in range(rows):
                    for i in range(cols):
                        f.write('0. 0. 0. %f %f 0. -1.\n' % (x[i], y[j]))

            self._log_threadsafe("Done! ANG file written successfully.")
            self.generation_success = True
            self.generation_error = None

        except Exception as e:
            self._log_threadsafe(f"Error: {e}")
            self.generation_success = False
            self.generation_error = str(e)

    def _check_generation_status(self):
        """Poll until the generation thread finishes."""
        if self.gen_thread and self.gen_thread.is_alive():
            self.root.after(100, self._check_generation_status)
        else:
            self._generation_finished()

    def _generation_finished(self):
        """Handle completion of the generation thread."""
        self.progress_bar.stop()
        self.is_running = False
        self.run_button.config(state="normal")

        if self.generation_success:
            self.status_label.config(text="ANG file generated successfully!")
            messagebox.showinfo("Success", "ANG file generated successfully!")
        elif self.generation_error:
            self.status_label.config(text="Generation failed.")
            messagebox.showerror("Error", f"Generation failed:\n{self.generation_error}")
        else:
            self.status_label.config(text="Ready")


def main():
    root = tk.Tk()
    AngGeneratorGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
