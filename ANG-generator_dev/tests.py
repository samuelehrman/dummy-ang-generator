"""
tests.py  --  Compare two .ang files for identity.

Usage:
    python tests.py <file_a.ang> <file_b.ang>

Exit codes:
    0  files are identical
    1  files differ (or an error occurred)
"""

import sys


def compare_ang_files(path_a: str, path_b: str) -> bool:
    """Return True if both .ang files have identical content, False otherwise."""
    with open(path_a, 'r') as fa, open(path_b, 'r') as fb:
        lines_a = fa.readlines()
        lines_b = fb.readlines()

    if len(lines_a) != len(lines_b):
        print(f"FAIL  line count differs: {len(lines_a)} vs {len(lines_b)}")
        return False

    for i, (la, lb) in enumerate(zip(lines_a, lines_b), start=1):
        if la != lb:
            print(f"FAIL  first difference at line {i}:")
            print(f"  A: {la.rstrip()}")
            print(f"  B: {lb.rstrip()}")
            return False

    print("PASS  files are identical")
    return True


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python tests.py <file_a.ang> <file_b.ang>")
        sys.exit(1)

    _, file_a, file_b = sys.argv
    identical = compare_ang_files(file_a, file_b)
    sys.exit(0 if identical else 1)
