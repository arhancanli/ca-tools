"""Tests of tools/credit_check.py against the real table and references.

Run: python3 tools/tests_credit/test_credit_check.py   (offline, a few seconds)

The cases are the credit questions met in review so far: pull request #31 as
first submitted (Bai XunDi's deposit given as a new method of the submitter)
and as corrected (one starting array still without its reference), Bai XunDi
citing his own deposit (correct), and a DOI of someone else's deposit.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))
import builds_on as bo      # noqa: E402
import credit_check as cc   # noqa: E402

refs = bo.load(os.path.join(REPO, "table"))
with open(os.path.join(REPO, "table", "ca_table.csv"), newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))


def flags(raw, slug="test-credit"):
    ck = cc.Checker(refs, rows, repo=REPO, slug=slug, online=False)
    ids, links, errs = bo.parse(raw["builds_on"], refs)
    assert not errs, errs
    return ck.claim_flags(raw, ids, links), ck


def kinds(fl):
    return sorted(k for k, _ in fl)


SITJAR = "T. N. Sitjar (tns-research)"
POSTOP = ("Classic post-optimisation (row deletion with local re-assignment of "
          "non-essential entries) of the table's record array CA(%s)")

# 1. #31 as first submitted: Bai XunDi's deposit given as 'new'
fl, _ = flags(dict(t="3", v="8", k="12", N="954", construction=POSTOP % "955; 3, 12, 8",
                   builds_on="postop-nck2013;new doi:10.5281/zenodo.23787055",
                   credit=SITJAR, notes="", source_detail="deposit"))
assert kinds(fl) == ["deposit-as-new", "starting-array"], fl

# 2. #31 as corrected: fine where deposit-bai2026 is listed ...
fl, _ = flags(dict(t="3", v="8", k="12", N="954", construction=POSTOP % "955; 3, 12, 8",
                   builds_on="deposit-bai2026;postop-nck2013",
                   credit=SITJAR, notes="", source_detail="deposit"))
assert fl == [], fl

# 3. ... and still flagged where it is not (CA(5522; 3, 19, 14) from Bai XunDi's CA(5568))
fl, _ = flags(dict(t="3", v="14", k="19", N="5522", construction=POSTOP % "5568; 3, 19, 14",
                   builds_on="fuse-ckrs2010;proj-c2008;postop-nck2013",
                   credit=SITJAR, notes="", source_detail="deposit"))
assert kinds(fl) == ["starting-array"], fl
assert "deposit-bai2026" in fl[0][1] and "Bai XunDi" in fl[0][1], fl

# 4. Bai XunDi citing his own deposit as 'new' is right: no deposit-as-new flag
fl, _ = flags(dict(t="3", v="3", k="27", N="72", construction="his own construction",
                   builds_on="new doi:10.5281/zenodo.23787055", credit="Bai XunDi",
                   notes="", source_detail="deposit"), slug="bai-xundi-2026-11-part9")
assert "deposit-as-new" not in kinds(fl), fl

# 5. a 'new' DOI that is the source of rows credited to someone else
fl, _ = flags(dict(t="2", v="2", k="3", N="4", construction="x",
                   builds_on="new doi:10.5281/zenodo.23787055", credit="Someone Else",
                   notes="", source_detail="x"))
assert kinds(fl) == ["deposit-as-new"], fl

# 6. 'new' while the text names a known method
fl, _ = flags(dict(t="2", v="2", k="3", N="4", construction="randomized post-optimization",
                   builds_on="new https://example.org/m", credit="Someone Else",
                   notes="", source_detail="x"))
assert kinds(fl) == ["new-vs-known"], fl

# 7. an author of a reference named in the text, not cited
fl, _ = flags(dict(t="2", v="2", k="3", N="4", construction="following Nayeri's idea",
                   builds_on="cphf-smc2006", credit="Someone Else", notes="", source_detail="x"))
assert kinds(fl) == ["named"], fl

# 8. first-time contributor, and a known one
_, ck = flags(dict(t="2", v="2", k="3", N="4", construction="x", builds_on="cphf-smc2006",
                   credit="Someone Else", notes="", source_detail="x"))
assert [k for k, _ in ck.submission_flags(["Someone Else"])] == ["first-time"]
assert ck.submission_flags([SITJAR]) == []

# 9. author list parsing
assert cc.authors_of("P. Nayeri, C. J. Colbourn and G. Konjevod, Randomized post-optimization") \
    == ["Nayeri", "Colbourn", "Konjevod"]
assert cc.authors_of("X. Bai, Covering arrays: verified improvements") == ["Bai"]

print("all credit_check tests passed")
