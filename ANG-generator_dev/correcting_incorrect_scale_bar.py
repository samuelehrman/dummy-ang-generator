"""
Correct the scale bar of an existing ANG file.

Reads an ANG file, then recomputes the per-point x/y coordinates (and the
XSTEP/YSTEP header values) from a user-supplied horizontal/vertical field
width. The step size is HFW / NCOLS and VFW / NROWS, matching the logic in
ANG-generator_GUI.py.

The corrected file is written next to the input with "_scale_bar" appended.
"""

import os
import sys
import traceback


# ---------------------------------------------------------------------------
# Inputs -- edit these
# ---------------------------------------------------------------------------
ANG_PATH = r"\\128.111.247.210\PollockShare\CurrentResearchers\SamEhrman\20260629_163820_702657_0_movie_movie_Rescan.ang"
HFW = 100.0   # horizontal field width, microns
VFW = 100.0   # vertical field width, microns

# Number of output lines to accumulate before flushing to disk. Writing in
# moderate batches avoids the Windows "[Errno 22] Invalid argument" error that
# occurs when a single very large write is sent to a network/mapped drive.
WRITE_BATCH_LINES = 50_000


def _parse_header_int(header_lines, key):
    """Return the integer value following '# <key>:' in the header, or None."""
    prefix = "# " + key
    for line in header_lines:
        if line.startswith(prefix):
            value_str = line.split(":", 1)[1].strip()
            try:
                return int(float(value_str))
            except ValueError as exc:
                raise RuntimeError(
                    f"Could not parse '{key}' value '{value_str}' "
                    f"from header line: {line.strip()!r}"
                ) from exc
    return None


def _read_lines(ang_path):
    """Read the ANG file into a list of lines, with clear error messages."""
    if not isinstance(ang_path, str) or not ang_path.strip():
        raise ValueError("ANG_PATH is empty -- set it to a real .ang file path.")
    if not os.path.exists(ang_path):
        raise FileNotFoundError(f"ANG file not found: {ang_path}")
    if not os.path.isfile(ang_path):
        raise IsADirectoryError(f"ANG_PATH is not a file: {ang_path}")
    try:
        with open(ang_path, "r") as f:
            return f.readlines()
    except PermissionError as exc:
        raise PermissionError(
            f"Permission denied reading {ang_path}. "
            f"Check that the file/drive is accessible and not open elsewhere."
        ) from exc
    except OSError as exc:
        raise OSError(
            f"Failed to read {ang_path} (errno {exc.errno}: {exc.strerror})."
        ) from exc


def correct_scale_bar(ang_path, hfw, vfw):
    """Rewrite ang_path with x/y coordinates derived from hfw/vfw."""
    # --- Validate the numeric inputs -------------------------------------
    try:
        hfw = float(hfw)
        vfw = float(vfw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"HFW and VFW must be numbers (got HFW={hfw!r}, VFW={vfw!r}).") from exc
    if hfw <= 0 or vfw <= 0:
        raise ValueError(f"HFW and VFW must be greater than zero (got HFW={hfw}, VFW={vfw}).")

    # --- Read input -------------------------------------------------------
    lines = _read_lines(ang_path)
    if not lines:
        raise RuntimeError(f"ANG file is empty: {ang_path}")

    # --- Parse grid dimensions from the header ---------------------------
    header_lines = [ln for ln in lines if ln.lstrip().startswith("#")]
    ncols = _parse_header_int(header_lines, "NCOLS_ODD")
    if ncols is None:
        ncols = _parse_header_int(header_lines, "NCOLS_EVEN")
    nrows = _parse_header_int(header_lines, "NROWS")
    if ncols is None or nrows is None:
        raise RuntimeError(
            "Could not read NCOLS/NROWS from the ANG header. "
            "Expected '# NCOLS_ODD:'/'# NCOLS_EVEN:' and '# NROWS:' lines."
        )
    if ncols <= 0 or nrows <= 0:
        raise RuntimeError(f"Invalid grid dimensions in header: {ncols} cols x {nrows} rows.")

    # Step size from the field of view (overrides whatever is in the file).
    dx = hfw / ncols
    dy = vfw / nrows

    # --- Build corrected lines and stream them to disk in batches --------
    base, ext = os.path.splitext(ang_path)
    out_path = base + "_scale_bar" + ext
    if os.path.abspath(out_path) == os.path.abspath(ang_path):
        raise RuntimeError(f"Refusing to overwrite the input file: {out_path}")

    point_index = 0
    try:
        out_file = open(out_path, "w")
    except OSError as exc:
        raise OSError(
            f"Failed to open output file {out_path} "
            f"(errno {exc.errno}: {exc.strerror})."
        ) from exc

    try:
        buffer = []
        buffered = 0

        def flush():
            nonlocal buffer, buffered
            if not buffer:
                return
            try:
                out_file.write("".join(buffer))
            except OSError as exc:
                raise OSError(
                    f"Failed while writing to {out_path} "
                    f"(errno {exc.errno}: {exc.strerror}). "
                    f"This can happen on network/mapped drives with large writes."
                ) from exc
            buffer = []
            buffered = 0

        for line_no, ln in enumerate(lines, start=1):
            if ln.lstrip().startswith("#"):
                # Update the step size header lines; pass everything else through.
                if ln.startswith("# XSTEP:"):
                    buffer.append("# XSTEP: %f\n" % dx)
                elif ln.startswith("# YSTEP:"):
                    buffer.append("# YSTEP: %f\n" % dy)
                else:
                    buffer.append(ln)
                buffered += 1
            elif not ln.strip():
                buffer.append(ln)
                buffered += 1
            else:
                # Recompute x/y from the point's position in the square grid.
                col = point_index % ncols
                row = point_index // ncols
                x = col * dx
                y = row * dy

                tokens = ln.split()
                if len(tokens) < 5:
                    raise RuntimeError(
                        f"Malformed data row at line {line_no}: expected at least "
                        f"5 columns (phi1 PHI phi2 x y ...), got {len(tokens)}: "
                        f"{ln.strip()!r}"
                    )
                tokens[3] = "%.5f" % x
                tokens[4] = "%.5f" % y
                buffer.append("  ".join(tokens) + "\n")
                buffered += 1
                point_index += 1

            if buffered >= WRITE_BATCH_LINES:
                flush()

        flush()
    except Exception:
        # Clean up the partial/corrupt output so a failed run leaves no half file.
        try:
            out_file.close()
        finally:
            try:
                if os.path.exists(out_path):
                    os.remove(out_path)
            except OSError:
                pass
        raise
    else:
        out_file.close()

    expected = ncols * nrows
    if point_index != expected:
        print(
            f"Warning: file has {point_index} data points but header implies "
            f"{ncols} x {nrows} = {expected}. Coordinates were still rewritten "
            f"row-major using the header dimensions."
        )

    print(f"Read:  {ang_path}")
    print(f"Grid:  {ncols} cols x {nrows} rows")
    print(f"FOV:   HFW={hfw:g} um, VFW={vfw:g} um -> dx={dx:g} um, dy={dy:g} um")
    print(f"Wrote: {out_path}")
    return out_path


if __name__ == "__main__":
    try:
        correct_scale_bar(ANG_PATH, HFW, VFW)
    except Exception as exc:
        print(f"\nERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
