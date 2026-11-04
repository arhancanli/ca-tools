#!/usr/bin/env python3
"""provenance.py - the "how was it built" requirements for submissions (since 2026-11-04).

The table exists so that anyone can see how every array was built and rebuild it. A submission
that adds arrays (claims.csv, certificates.csv, constructions.csv or external.csv) therefore
needs:

1. HOW.md in the submission folder, with three labelled parts, each non-empty:
       Construction: the construction or search method, by name
       Built from:   every base array or ingredient, by table file name or by an openly
                     licensed source ("nothing" when the array was built from scratch)
       Program:      the program or recipe that rebuilds it: a link to the code, or the
                     commands, with seeds and settings for a search
   Submissions opened before the rule are listed in submissions/HOW_EXEMPT.txt.
2. A named construction in every claim: "unknown" (or empty) is refused.
3. No Torres-Jimenez array as a base. The arrays withdrawn on 2026-10-27 and the Torres-Jimenez
   arrays of the CAs package (TJ2level_CAs, CAEX_CAs, TJcat) may not be ingredients or starts:
   a claim is refused when its builds_on names his array repository (web-tj), when its text names
   one of those data sets or arrays, or when the array is the same as one of them up to row,
   column and symbol permutations (fingerprint). His published METHODS (for example the CA
   Extender, caex-tjaa2021) stay allowed, credited as methods.

Standard library only. Used by check_submission.py, check_certificates.py and
check_constructions.py.
"""
import csv
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOW_FILE = "HOW.md"
HOW_PARTS = ("Construction", "Built from", "Program")
ADDING = ("claims.csv", "certificates.csv", "constructions.csv", "external.csv")
UNKNOWN = re.compile(r"^\s*(unknown|n/?a|none|\?+|-+|tbd|not known)\s*\.?\s*$", re.I)
TJ_DATA = re.compile(r"TJ2level|CAEX_CAs|TJcat|\bTJRT\b|sa-tr2012", re.I)
TJ_REPO_ID = "web-tj"


def how_exempt():
    path = os.path.join(REPO, "submissions", "HOW_EXEMPT.txt")
    if not os.path.isfile(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return {ln.strip() for ln in f if ln.strip() and not ln.startswith("#")}


def how_problems(subdir, slug):
    """Problems with HOW.md for a submission folder (an empty list when it is fine or not needed)."""
    names = set(os.listdir(subdir)) if os.path.isdir(subdir) else set()
    if not names.intersection(ADDING) or slug in how_exempt():
        return []                       # an upgrade request adds no array; old submissions exempt
    path = os.path.join(subdir, HOW_FILE)
    if not os.path.isfile(path) or os.path.islink(path):
        return ["%s is missing. Every submission that adds arrays says how they were built, so "
                "that anyone can rebuild them: a %s with the parts %s (see \"How it was built\" in "
                "submissions/README.md)" % (HOW_FILE, HOW_FILE, ", ".join('"%s:"' % p for p in HOW_PARTS))]
    text = open(path, encoding="utf-8", errors="replace").read()
    out = []
    for i, part in enumerate(HOW_PARTS):
        m = re.search(r"^[ \t#*-]*%s[ \t]*:?[ \t]*\**[ \t]*:?(.*)$" % re.escape(part), text, re.I | re.M)
        if not m:
            out.append('%s has no "%s:" part' % (HOW_FILE, part))
            continue
        # the part's text: the rest of its line plus the lines up to the next part's label
        rest = text[m.start(1):]
        nxt = [re.search(r"^[ \t#*-]*%s[ \t]*:" % re.escape(p), rest, re.I | re.M) for p in HOW_PARTS if p != part]
        cut = min([x.start() for x in nxt if x and x.start() > 0] + [len(rest)])
        body = rest[:cut].strip(" \t\r\n*:#-")
        if len(re.sub(r"\W", "", body)) < 2 or UNKNOWN.match(body):
            out.append('%s: the "%s:" part is empty' % (HOW_FILE, part))
    return out


def construction_problem(construction):
    if not (construction or "").strip() or UNKNOWN.match(construction):
        return ("construction must name the construction or search that produced the array; "
                "\"unknown\" is not accepted (since 2026-11-04)")
    return None


def tj_codes():
    """The names of the Torres-Jimenez arrays (ca<N>.<t>.<v>.<k>) from the two fingerprint lists."""
    codes = set()
    for name in ("withdrawn_fingerprints.csv", "tj_fingerprints.csv"):
        path = os.path.join(REPO, "table", name)
        if os.path.isfile(path):
            with open(path, newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    codes.update(re.findall(r"ca\d+\.\d+\.\d+\.\d+", r.get("source_detail", "")))
    return codes


_CODES = None


def tj_text_problem(raw):
    """A refusal text when a claim's fields name a Torres-Jimenez array or his repository as a base."""
    global _CODES
    if _CODES is None:
        _CODES = tj_codes()
    ids = [x.strip() for x in (raw.get("builds_on") or "").split(";")]
    if TJ_REPO_ID in ids:
        return ("builds_on names web-tj, the Torres-Jimenez array repository: arrays of Torres-Jimenez "
                "may not be ingredients or starts (withdrawn 2026-10-27; submissions/README.md, rule 6)")
    # source_detail and construction say what the array was built from; notes may compare with
    # his sizes ("replaces the TJcat entry ..."), which is allowed
    text = " ".join(raw.get(k) or "" for k in ("source_detail", "construction"))
    m = TJ_DATA.search(text)
    if m:
        return ("the claim names %r, a Torres-Jimenez data set: his arrays may not be ingredients or "
                "starts (submissions/README.md, rule 6)" % m.group(0))
    found = sorted(c for c in set(re.findall(r"ca\d+\.\d+\.\d+\.\d+", text)) if c in _CODES)
    if found:
        return ("the claim names %s, a Torres-Jimenez array: his arrays may not be ingredients or "
                "starts (submissions/README.md, rule 6)" % ", ".join(found))
    return None


def load_tj_fingerprints(table_dir):
    """Fingerprints of the withdrawn files and of the Torres-Jimenez arrays of the CAs package."""
    out = []
    for name in ("withdrawn_fingerprints.csv", "tj_fingerprints.csv"):
        path = os.path.join(table_dir, name)
        if os.path.isfile(path):
            with open(path, newline="", encoding="utf-8") as f:
                out += [r for r in csv.DictReader(f) if r.get("fingerprint")]
    return out
