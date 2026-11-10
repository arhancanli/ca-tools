"""Tests of tools/credit_text.py, the one reader of a row's credit.

Run: python3 tools/tests_credit/test_credit_text.py   (offline, a few seconds)

The credit runs to the first semicolon outside parentheses. Two tools cut it at the first
semicolon until 2026-11-10 (tools/credit_check.py, tools/add_tjim7.py), which loses the end of
every credit that names a size such as CA(1180; 3, 8, 10). This test checks the reader on
fixed cases and on every row of the table whose credit has a semicolon inside parentheses,
checks that every tool reads a credit through it, and that no tool keeps a reader of its own.
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
TOOLS = os.path.join(REPO, "tools")
sys.path.insert(0, TOOLS)
import credit_text as ct      # noqa: E402
import render_table as rt     # noqa: E402
import check_upgrades as cu   # noqa: E402
import auto_upgrade as au     # noqa: E402
import credit_check as cc     # noqa: E402

failures = []


def check(cond, what):
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        failures.append(what)


# 1. fixed cases
check(ct.credit("credit: A. Author (the ingredient CA(15; 3, 12, 2)); exceeds table: x")
      == "A. Author (the ingredient CA(15; 3, 12, 2))", "a semicolon inside parentheses stays in the credit")
check(ct.credit("credit: A. Author; exceeds table") == "A. Author", "the credit ends at the first semicolon outside")
check(ct.credit("equals best known; credit: B. Author; submission s") == "B. Author", "a credit after '; ' is found")
check(ct.credit("equals best known") == "", "no credit gives the empty string")
check(ct.credit("") == "" and ct.credit(None) == "", "empty and missing notes")
check(ct.credit("credit: A (x; y") == "A (x", "unbalanced parentheses fall back to the first semicolon")
check(ct.credit("credit: A (x) (y; z) w") == "A (x) (y; z) w", "no semicolon outside: the whole rest")

# 2. every row of the table
with open(os.path.join(REPO, "table", "ca_table.csv"), newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
inside = 0
bad_balance = bad_tools = 0
for r in rows:
    c = ct.credit(r["notes"])
    if ";" in c:
        inside += 1
        if c.count("(") != c.count(")"):
            bad_balance += 1
        cut = r["notes"][r["notes"].find("credit:"):].split(":", 1)[1].split(";", 1)[0].strip()
        if not (len(cut) < len(c) and c.startswith(cut)):
            bad_balance += 1
    if (rt.credit_of(r) != c or (cu.original_credit(r["notes"]) or "") != c
            or (au.original_credit(r["notes"]) or "") != c or (c and cc.row_credit(r) != c)):
        bad_tools += 1
check(inside >= 49, "%d rows have a credit with a semicolon inside parentheses (76 rows, 41 distinct "
      "credits, on 2026-11-10)" % inside)
check(bad_balance == 0, "each of them is read whole, with balanced parentheses, longer than the cut at "
      "the first semicolon (%d wrong)" % bad_balance)
check(bad_tools == 0, "render_table, check_upgrades, auto_upgrade and credit_check read the same credit "
      "on all %d rows (%d differ)" % (len(rows), bad_tools))

# 3. no tool keeps a reader of its own
own = []
for name in sorted(os.listdir(TOOLS)):
    if not name.endswith(".py") or name == "credit_text.py":
        continue
    src = open(os.path.join(TOOLS, name), encoding="utf-8").read()
    if re.search(r"""split\(\s*["']credit: ["']""", src) or re.search(r"credit:\\s\*\(\[\^;\]\+\)", src) \
            or re.search(r"""find\(\s*["']credit: ["']\)""", src):
        own.append(name)
check(not own, "no tool cuts a credit itself (%s)" % (", ".join(own) or "none"))

print("%d failures" % len(failures))
sys.exit(1 if failures else 0)
