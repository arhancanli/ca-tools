#!/usr/bin/env python3
"""Meta-test: no test may assert a particular value of the live table/.

The table grows every day. A test that asserts a size, an id or a count read from the live table/ breaks the
day a new row moves that value, although nothing is wrong (this happened on 2026-11-10: two frame tests
named "DP2 gives 2448" and "all 23 alphabets" of the live table, and Arhan Canli's strength-2 rows changed
both). Such a test belongs on the fixed fixture table (tools/tests_frame/fixtures, fixture_table.py), and
what must hold on the live table however it grows belongs in test_frame_invariants.py.

The check is at the level of the source text (Python ast), not of what a test does when it runs:

  - a unit is a function of a test file, or the statements of the file outside any function;
  - a unit reads the live table when its text joins the repository root with "table" (a name starting with
    REPO, ROOT, TOP or BASE, with os.path.join or with a pathlib "/", or Path(...).parents[n] / "table"), passes a path "table/<file>.csv" as the first argument of a call, uses a name the file
    binds at the top to such a path (for example LIVE = os.path.join(REPO, "table")), loads from the rows
    that tools/derive_laws.py reads on import (unless it replaces them first), or calls a function of the
    same file that reads it (a sys.path entry, to import table/ca_table.py, is not a read);
  - a unit pins a value when a comparison in it (==, !=, <, <=, >, >=, in, not in, or a unittest call
    self.assertEqual, assertIn, assertLess and the like) has among its operands, at any depth, an integer of 2 or more, a string of digits other than "0" and "1", or a row id such as
    "t3-v12-k10000-1".

A unit that does both fails this test unless ALLOW lists it with a reason. It is a lint, not a proof: it does
not follow helpers imported from other files, and it does not see a tool called with its default table
directory (for example cc.check_frame_veto(rows) without table_dir). The test files scanned are
tools/tests_*/*.py and tools/cphf/tests/*.py; R tests are checked by a plain grep for table/ paths.

Usage: test_no_live_pins.py [--list]   (--list prints every unit that reads the live table)
"""
import ast
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

LIVE_RE = re.compile(r"""\b_?(?:REPO|ROOT|TOP|BASE)\w*\s*[,/]\s*["']table["']|\]\s*/\s*["']table["']"""
                     r"""|\(\s*["'](?:\./)?table/[A-Za-z_]+\.csv""")
DERIVE_LAWS_RE = re.compile(r"\b(?:L|derive_laws)\.(?:load\(|rows\b)")
ID_RE = re.compile(r"^t[2-9]-v\d+-k\d+-\d+$")

# Units that only copy the live table/ (its support files: references, lists, certificates) into a temporary
# table or repository, where the test then builds its own rows. They read no size, so they neither count as a
# read nor make their callers one. (file relative to the repository, unit) -> what it copies.
COPY_ONLY = {
    ("tools/tests_submission/test_above_rule.py", "small_table"):
        "the support files of table/ into a synthetic table of two baseline rows",
    ("tools/tests_upgrade/test_upgrades.py", "make_repo"):
        "table/ without arrays/ into a temporary git repository (also used by test_route.py); MANIFEST.csv emptied",
    ("tools/cphf/tests/test_certificates.py", "fresh"):
        "table/ without arrays/ into a temporary repository",
}

# (file relative to the repository, unit) -> why it may compare numbers while reading the live table.
# A unit is "<module>" for the statements outside functions. Keep the reasons specific.
ALLOW = {
    ("tools/tests_credit/test_credit_text.py", "<module>"):
        "a scan of the credit text of every live row for faults: the number of faults is 0, and at least 49 "
        "rows have a semicolon inside parentheses (a lower bound; rows are never removed)",
    ("tools/tests_credit/test_correct_credit.py", "<module>"):
        "corrects the existing row CA(6228; 3, 196, 12) in a temporary copy (rows are never removed from the "
        "table, so it stays); it compares that row's own fields, not a best size",
    ("tools/tests_construction/test_route.py", "run"):
        "reads the stored Power CZ certificates of table/constructions/powercz (fixed files) to submit them again "
        "as duplicates; the other numbers are of the test's own rows in a copy of table/",
    ("tools/cphf/tests/test_certificates.py", "run_all"):
        "reads stored CPHF certificate files of table/certificates (fixed files, by sha256); the numbers compared "
        "are of its own planted rows, shard counts and timing fields",
}


def files():
    out = sorted(glob.glob(os.path.join(REPO, "tools", "tests_*", "*.py")) +
                 glob.glob(os.path.join(REPO, "tools", "cphf", "tests", "*.py")))
    return [f for f in out if os.path.basename(f) != os.path.basename(__file__)]


def pinned_constants(node):
    """the constants in a comparison that look like a value of the table"""
    out = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant):
            c = sub.value
            if isinstance(c, bool):
                continue
            if isinstance(c, int) and c >= 2:
                out.append(c)
            elif isinstance(c, str) and ((c.isdigit() and c not in ("0", "1")) or ID_RE.match(c)):
                out.append(c)
    return out


def units(tree, src):
    """[(name, text, nodes)] for every function (nested ones inside their outer function) and the module rest"""
    out, rest = [], []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append((node.name, ast.get_source_segment(src, node) or "", [node]))
        elif isinstance(node, ast.ClassDef):
            for f in node.body:
                if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.append(("%s.%s" % (node.name, f.name), ast.get_source_segment(src, f) or "", [f]))
        else:
            rest.append(node)
    out.append(("<module>", "\n".join(ast.get_source_segment(src, n) or "" for n in rest), rest))
    return out


def live_text(text):
    """does the text name the live table/ (a sys.path entry for importing table/ca_table.py does not count)"""
    text = "\n".join(l for l in text.splitlines() if "sys.path" not in l)
    # tools/derive_laws.py reads the live table when imported (its rows); a unit that loads from them reads it,
    # unless it puts other rows in their place first
    laws = DERIVE_LAWS_RE.search(text) and not re.search(r"\bL\.rows\s*=|derive_laws\.rows\s*=", text)
    return bool(LIVE_RE.search(text) or laws)


def scan(path, copy_only=()):
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src, path)
    # names bound at the top of the file to a path in the live table/
    live_names = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and live_text(ast.get_source_segment(src, node) or ""):
            live_names |= {t.id for t in node.targets if isinstance(t, ast.Name)}
    us = units(tree, src)
    reads = {}
    for name, text, nodes in us:
        used = {n.id for nd in nodes for n in ast.walk(nd) if isinstance(n, ast.Name)}
        reads[name] = live_text(text) or bool(used & live_names) and name != "<module>"
        if name == "<module>":
            # the module rest reads the table only by its own text (the binding of a name is not a read)
            reads[name] = any(live_text(ast.get_source_segment(src, n) or "") and not (
                isinstance(n, ast.Assign) and all(isinstance(t, ast.Name) and t.id in live_names for t in n.targets))
                for n in nodes) or bool({x.id for nd in nodes if not (isinstance(nd, ast.Assign) and all(
                    isinstance(t, ast.Name) and t.id in live_names for t in nd.targets))
                    for x in ast.walk(nd) if isinstance(x, ast.Name)} & live_names)
    for name in copy_only:
        reads[name] = False
    calls = {name: {n.func.id for nd in nodes for n in ast.walk(nd)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)} for name, _, nodes in us}
    changed = True
    while changed:
        changed = False
        for name in reads:
            if not reads[name] and name not in copy_only and calls[name] & {n for n, r in reads.items() if r}:
                reads[name] = changed = True
    found = []
    for name, _, nodes in us:
        if not reads[name]:
            continue
        pins = []
        for nd in nodes:
            for sub in ast.walk(nd):
                if isinstance(sub, ast.Compare) or (
                        isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr.startswith("assert")):
                    pins += [(sub.lineno, c) for c in pinned_constants(sub)]
        found.append((name, pins))
    return found


def selftest():
    """the scan finds planted pins (plain, pathlib root, unittest assert) and passes a fixture test"""
    import tempfile
    bad = ('import os\nREPO = "."\nLIVE = os.path.join(REPO, "table")\n\n'
           'def helper():\n    return open(os.path.join(LIVE, "ca_frame.csv")).read()\n\n'
           'def test_pin():\n    x = helper()\n    assert x == "2448"\n\n'
           'def test_fixture():\n    x = open("fixtures/t.csv").read()\n    assert x == "2448"\n\n'
           'def test_pathlib():\n    n = len(open(TOP / "table" / "ca_frame.csv").readlines())\n    assert n > 9000\n\n'
           'class T:\n    def test_unittest(self):\n'
           '        self.assertEqual(len(open(os.path.join(REPO_ROOT, "table", "ca_frame.csv")).readlines()), 9570)\n')
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(bad)
    try:
        got = {n: p for n, p in scan(f.name)}
    finally:
        os.remove(f.name)
    return bool(got.get("test_pin") and "test_fixture" not in got and got.get("helper") == []
                and got.get("test_pathlib") and got.get("T.test_unittest"))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    fails, n_units, n_files, used = [], 0, 0, set()
    for path in files():
        rel = os.path.relpath(path, REPO).replace(os.sep, "/")
        found = scan(path, {u for f, u in COPY_ONLY if f == rel})
        n_files += 1
        for name, pins in found:
            n_units += 1
            if "--list" in argv:
                print("reads table/: %s %s%s" % (rel, name, " (pins %s)" % pins[:5] if pins else ""))
            if pins and (rel, name) in ALLOW:
                used.add((rel, name))
            if pins and (rel, name) not in ALLOW:
                fails.append("%s %s: lines %s compare %s"
                             % (rel, name, sorted({l for l, _ in pins})[:8], [c for _, c in pins][:8]))
    stale = [k for k in list(ALLOW) + list(COPY_ONLY) if not os.path.exists(os.path.join(REPO, k[0]))]
    stale += [k for k in ALLOW if k not in used and k not in stale]     # an entry no longer needed is removed
    rfails = []
    for path in sorted(glob.glob(os.path.join(REPO, "r", "**", "test*.R"), recursive=True)):
        for i, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
            if re.search(r"""["'](?:\.\./)*table/(?:ca_table|ca_frame|derived)\.csv""", line):
                rfails.append("%s line %d: %s" % (os.path.relpath(path, REPO), i, line.strip()[:100]))
    ok_self = selftest()
    print("%s  selftest: planted live pins are found (plain, pathlib, assertEqual), a fixture test passes" % ("PASS" if ok_self else "FAIL"))
    print("%s  no test of %d files asserts a value of the live table/ outside the allowlist (%d units read it)"
          % ("PASS" if not fails else "FAIL", n_files, n_units))
    for f in fails:
        print("      " + f)
    print("%s  every allowlist entry names a unit that still reads the live table and compares numbers"
          % ("PASS" if not stale else "FAIL"))
    for f in stale:
        print("      %s %s" % f)
    print("%s  no R test reads table/ca_table.csv, ca_frame.csv or derived.csv" % ("PASS" if not rfails else "FAIL"))
    for f in rfails:
        print("      " + f)
    bad = (not ok_self) + bool(fails) + bool(stale) + bool(rfails)
    print("%d passed, %d failed" % (4 - bad, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
