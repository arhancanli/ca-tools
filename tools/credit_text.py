"""credit_text.py - the one reader of the credit in a row's notes.

The notes of a row start with "credit: " (or carry it after "; "), and the credit runs to
the first semicolon outside parentheses: a semicolon inside, as in CA(15; 3, 12, 2) or
"(the ingredient CA(1180; 3, 8, 10))", belongs to the credit. Cutting at the first
semicolon instead loses the end of such a credit; that happened on the page before
2026-11-08 and in two tools until 2026-11-10. Every tool that reads a credit uses this
module (tools/render_table.py, tools/credit_check.py, tools/check_upgrades.py,
tools/auto_upgrade.py, tools/add_tjim7.py); tests_credit/test_credit_text.py checks it on
every row of the table whose credit has a semicolon inside parentheses.

Standard library only.
"""
import re

START = re.compile(r"(?:^|;\s*)credit:\s*")


def credit(notes):
    """The credit of a row's notes, or "" when the notes name none. With unbalanced
    parentheses (no row has them) it falls back to the first semicolon."""
    notes = notes or ""
    m = START.search(notes)
    if not m:
        return ""
    s = notes[m.end():]
    depth = 0
    for j, ch in enumerate(s):
        if ch == ";" and depth == 0:
            return s[:j].strip()
        depth = max(0, depth + (ch == "(") - (ch == ")"))
    return (s.split(";", 1)[0] if depth > 0 else s).strip()
