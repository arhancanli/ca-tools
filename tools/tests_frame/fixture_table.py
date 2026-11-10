"""The fixed fixture table of the tests (tools/tests_frame/fixtures/table_<commit>, made by
tools/tests_frame/fixtures/make_fixture.py): a copy of the table at one commit, t = 2 and 3 and t = 6 at
v = 2, with its derived.csv lines and above_rule_rows.csv. Tests that assert sizes, ids or counts of a
real table read this, never the live table/, so new rows in the live table cannot change what they assert."""
import contextlib
import csv
import gzip
import io
import os
import shutil
import tempfile

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
FIXTURE = "51d2111"


@contextlib.contextmanager
def fixture_table(extra=(), name=FIXTURE):
    """a temporary table directory holding the fixture table, ca_table.csv unpacked, and the rows of extra
    (dicts; missing columns empty) appended. Yields (directory, rows)."""
    with tempfile.TemporaryDirectory() as d:
        shutil.copytree(os.path.join(FIXTURES, "table_" + name), d, dirs_exist_ok=True)
        raw = gzip.decompress(open(os.path.join(d, "ca_table.csv.gz"), "rb").read()).decode("utf-8")
        rows = list(csv.DictReader(io.StringIO(raw)))
        rows += [dict({c: "" for c in rows[0]}, **e) for e in extra]
        with open(os.path.join(d, "ca_table.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, list(rows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        yield d, rows
