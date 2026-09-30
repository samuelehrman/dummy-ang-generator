"""
Replace columns of one ANG file with the same columns from another ANG file.

Example: take the IQ values from SOURCE_PATH and write them into TARGET_PATH,
leaving every other column (and the whole header) of TARGET_PATH unchanged.

Columns are chosen by name as listed in the '# COLUMN_HEADERS:' header line
(case-insensitive), or by 1-based column number as a fallback.

Before writing, the two files are compared and warnings are printed if:
  - they have a different number of data rows
  - their NCOLS_ODD / NCOLS_EVEN / NROWS header values differ
  - their x/y coordinates do not match row by row
If any warning is raised you are asked whether to continue or cancel.

The result is written next to the target with "_replaced" appended.
"""

import os
import re
import sys
import traceback
from itertools import zip_longest


# ---------------------------------------------------------------------------
# Inputs -- edit these
# ---------------------------------------------------------------------------
TARGET_PATH = r"F:\SamEhrman\120umCoNi90\20260812_183141_951270_0_movie_countedframes_Rescan_Rescan_207BW.ang"   # file whose columns get replaced
SOURCE_PATH = r"F:\SamEhrman\120umCoNi90\20260812_183141_951270_0_movie_countedframes_houghIQ.ang"   # file the new column values come from
COLUMNS = ["IQ"]    # names from COLUMN_HEADERS (e.g. "IQ", "CI", "Fit") or 1-based numbers

# Maximum allowed difference (microns) between x/y values before they count as mismatched.
XY_TOLERANCE = 1e-4

# Number of output lines to accumulate before flushing to disk. Writing in
# moderate batches avoids the Windows "[Errno 22] Invalid argument" error that
# occurs when a single very large write is sent to a network/mapped drive.
WRITE_BATCH_LINES = 50_000

# Column indices (0-based) of x and y in every ANG version.
X_INDEX = 3
Y_INDEX = 4

GRID_KEYS = ("NCOLS_ODD", "NCOLS_EVEN", "NROWS")

_TOKEN_RE = re.compile(r"\S+")


def _check_path(path, label):
    if not isinstance(path, str) or not path.strip():
        raise ValueError(f"{label} is empty -- set it to a real .ang file path.")
    if not os.path.exists(path):
        raise FileNotFoundError(f"{label} not found: {path}")
    if not os.path.isfile(path):
        raise IsADirectoryError(f"{label} is not a file: {path}")


def _open_read(path):
    try:
        return open(path, "r")
    except PermissionError as exc:
        raise PermissionError(
            f"Permission denied reading {path}. "
            f"Check that the file/drive is accessible and not open elsewhere."
        ) from exc
    except OSError as exc:
        raise OSError(
            f"Failed to read {path} (errno {exc.errno}: {exc.strerror})."
        ) from exc


def _is_data_line(line):
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith("#")


def _iter_data_lines(path):
    """Yield (line_no, line) for every data row in the file."""
    with _open_read(path) as f:
        for line_no, line in enumerate(f, start=1):
            if _is_data_line(line):
                yield line_no, line


def _read_header(path):
    """Return the list of '#' header lines at the top of the file."""
    header = []
    with _open_read(path) as f:
        for line in f:
            if line.lstrip().startswith("#"):
                header.append(line)
            elif line.strip():
                break
    return header


def _parse_grid(header_lines):
    """Return {key: value string} for the grid-size header keys that are present."""
    grid = {}
    for line in header_lines:
        for key in GRID_KEYS:
            if line.startswith("# " + key + ":"):
                grid[key] = line.split(":", 1)[1].strip()
    return grid


def _parse_column_headers(header_lines):
    """Return the list of column names from '# COLUMN_HEADERS:', or None."""
    for line in header_lines:
        if line.startswith("# COLUMN_HEADERS:"):
            return [name.strip() for name in line.split(":", 1)[1].split(",")]
    return None


def _resolve_column(spec, column_names, path):
    """Turn a column name or 1-based number into a 0-based index for this file."""
    if isinstance(spec, int) or (isinstance(spec, str) and spec.strip().isdigit()):
        number = int(spec)
        if number < 1:
            raise ValueError(f"Column numbers are 1-based (got {number}).")
        return number - 1

    if column_names is None:
        raise RuntimeError(
            f"{path} has no '# COLUMN_HEADERS:' line, so column {spec!r} can't be "
            f"looked up by name. Use a 1-based column number instead."
        )
    lowered = [name.lower() for name in column_names]
    try:
        return lowered.index(str(spec).strip().lower())
    except ValueError:
        raise RuntimeError(
            f"Column {spec!r} not found in {path}. "
            f"Available columns: {', '.join(column_names)}"
        ) from None


def _replace_tokens(line, replacements):
    """
    Return line with the tokens at the given indices replaced, keeping the
    original spacing so the columns stay aligned.

    replacements: {token_index: new_token}
    """
    parts = []
    last_end = 0
    for i, match in enumerate(_TOKEN_RE.finditer(line)):
        start, end = match.span()
        gap = line[last_end:start]
        if i in replacements:
            new = replacements[i]
            old_width = end - start
            if len(new) < old_width:
                new = new.rjust(old_width)
            elif len(new) > old_width and len(gap) > 1:
                # Borrow leading spaces so the right edge of the column stays put.
                gap = gap[: max(1, len(gap) - (len(new) - old_width))]
            parts.append(gap)
            parts.append(new)
        else:
            parts.append(gap)
            parts.append(match.group())
        last_end = end
    parts.append(line[last_end:])
    return "".join(parts)


def _compare_files(target_path, source_path, max_index):
    """
    Stream both files once and return (target_rows, source_rows, xy_mismatches,
    first_xy_mismatch). Also validates that every overlapping row has enough columns.
    """
    target_rows = 0
    source_rows = 0
    xy_mismatches = 0
    first_mismatch = None

    pairs = zip_longest(_iter_data_lines(target_path), _iter_data_lines(source_path))
    for target_entry, source_entry in pairs:
        if target_entry is not None:
            target_rows += 1
        if source_entry is not None:
            source_rows += 1
        if target_entry is None or source_entry is None:
            continue
        (t_no, t_line), (s_no, s_line) = target_entry, source_entry
        t_tokens = t_line.split()
        s_tokens = s_line.split()
        for path, line_no, tokens in ((target_path, t_no, t_tokens), (source_path, s_no, s_tokens)):
            if len(tokens) <= max(max_index, Y_INDEX):
                raise RuntimeError(
                    f"Malformed data row at line {line_no} of {path}: expected at least "
                    f"{max(max_index, Y_INDEX) + 1} columns, got {len(tokens)}: {tokens!r}"
                )
        try:
            tx, ty = float(t_tokens[X_INDEX]), float(t_tokens[Y_INDEX])
            sx, sy = float(s_tokens[X_INDEX]), float(s_tokens[Y_INDEX])
        except ValueError as exc:
            raise RuntimeError(
                f"Non-numeric x/y at target line {t_no} / source line {s_no}."
            ) from exc
        if abs(tx - sx) > XY_TOLERANCE or abs(ty - sy) > XY_TOLERANCE:
            xy_mismatches += 1
            if first_mismatch is None:
                first_mismatch = (target_rows, (tx, ty), (sx, sy))

    return target_rows, source_rows, xy_mismatches, first_mismatch


def _confirm(prompt):
    while True:
        answer = input(prompt).strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no", ""):
            return False
        print("Please answer 'y' or 'n'.")


def replace_columns(target_path, source_path, columns):
    """Write a copy of target_path with `columns` taken from source_path."""
    _check_path(target_path, "TARGET_PATH")
    _check_path(source_path, "SOURCE_PATH")
    if os.path.abspath(target_path) == os.path.abspath(source_path):
        raise ValueError("TARGET_PATH and SOURCE_PATH are the same file.")
    if not columns:
        raise ValueError("COLUMNS is empty -- list at least one column to replace.")

    # --- Headers and column lookup ---------------------------------------
    target_header = _read_header(target_path)
    source_header = _read_header(source_path)
    target_names = _parse_column_headers(target_header)
    source_names = _parse_column_headers(source_header)

    # (label, target index, source index)
    column_map = []
    for spec in columns:
        t_idx = _resolve_column(spec, target_names, target_path)
        s_idx = _resolve_column(spec, source_names, source_path)
        label = target_names[t_idx] if target_names and t_idx < len(target_names) else f"column {t_idx + 1}"
        column_map.append((label, t_idx, s_idx))

    replaced_indices = {t_idx for _, t_idx, _ in column_map}
    if X_INDEX in replaced_indices or Y_INDEX in replaced_indices:
        print("Note: x and/or y are being replaced, so the x/y comparison below "
              "compares the coordinates before replacement.")

    # --- Compare the two files -------------------------------------------
    warnings = []

    target_grid = _parse_grid(target_header)
    source_grid = _parse_grid(source_header)
    for key in GRID_KEYS:
        t_val, s_val = target_grid.get(key), source_grid.get(key)
        if t_val != s_val:
            warnings.append(f"Header {key} differs: target={t_val}, source={s_val}")

    max_index = max(max(t, s) for _, t, s in column_map)
    print("Comparing files...")
    target_rows, source_rows, xy_mismatches, first_mismatch = _compare_files(
        target_path, source_path, max_index
    )
    if target_rows == 0:
        raise RuntimeError(f"No data rows found in {target_path}")
    if source_rows == 0:
        raise RuntimeError(f"No data rows found in {source_path}")

    if target_rows != source_rows:
        overlap = min(target_rows, source_rows)
        msg = (f"Files have a different number of data rows: target={target_rows}, "
               f"source={source_rows}. Only the first {overlap} rows would be replaced")
        if target_rows > source_rows:
            msg += f"; the last {target_rows - source_rows} target rows would be left unchanged."
        else:
            msg += f"; the last {source_rows - target_rows} source rows would be ignored."
        warnings.append(msg)

    if xy_mismatches:
        row, (tx, ty), (sx, sy) = first_mismatch
        warnings.append(
            f"x/y coordinates differ on {xy_mismatches} rows. First mismatch at data "
            f"row {row}: target=({tx:g}, {ty:g}), source=({sx:g}, {sy:g})."
        )

    if warnings:
        print()
        for w in warnings:
            print(f"WARNING: {w}")
        print()
        if not _confirm("Continue and write the output anyway? [y/N]: "):
            print("Cancelled. No file was written.")
            return None

    # --- Write output ----------------------------------------------------
    base, ext = os.path.splitext(target_path)
    out_path = base + "_replaced" + ext
    if os.path.abspath(out_path) in (os.path.abspath(target_path), os.path.abspath(source_path)):
        raise RuntimeError(f"Refusing to overwrite an input file: {out_path}")

    try:
        out_file = open(out_path, "w")
    except OSError as exc:
        raise OSError(
            f"Failed to open output file {out_path} "
            f"(errno {exc.errno}: {exc.strerror})."
        ) from exc

    replaced_rows = 0
    try:
        buffer = []

        def flush():
            nonlocal buffer
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

        source_iter = _iter_data_lines(source_path)
        with _open_read(target_path) as target_file:
            for line in target_file:
                if _is_data_line(line):
                    source_entry = next(source_iter, None)
                    if source_entry is not None:
                        s_tokens = source_entry[1].split()
                        line = _replace_tokens(
                            line, {t_idx: s_tokens[s_idx] for _, t_idx, s_idx in column_map}
                        )
                        replaced_rows += 1
                buffer.append(line)
                if len(buffer) >= WRITE_BATCH_LINES:
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

    print(f"Target:   {target_path}")
    print(f"Source:   {source_path}")
    for label, t_idx, s_idx in column_map:
        print(f"Replaced: {label} (target column {t_idx + 1} <- source column {s_idx + 1})")
    print(f"Rows:     {replaced_rows} of {target_rows} target rows replaced")
    print(f"Wrote:    {out_path}")
    return out_path


if __name__ == "__main__":
    try:
        replace_columns(TARGET_PATH, SOURCE_PATH, COLUMNS)
    except Exception as exc:
        print(f"\nERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
