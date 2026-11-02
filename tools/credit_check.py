"""credit_check.py - flags for the maintainer's review of credit in a submission.

The submission check proves that an array is a covering array. It cannot
prove that the credit is right: who found the array, whose arrays it was
built from, and whose methods it uses. This module does not decide any
of that. It lists what a careful reviewer would want to look at, so that
the review of credit by a person is quick and nothing is overlooked.
Nothing here fails a claim, and nothing here is applied to the table.

Flags, for each claim:

  deposit-as-new   'new <link>' in builds_on is a DOI that is already a
                   reference id, or the source of table rows credited to
                   someone else. 'new' is only for the submitter's own
                   description of a method of their own.
  doi-authors      'new <doi>' whose DOI record (DataCite or Crossref)
                   names authors none of whom appear in the credit field.
  starting-array   the construction or notes name an array CA(N; t, k, v)
                   that is a row of the table, and builds_on does not list
                   the reference of that row's source (its deposit), or the
                   row is credited to someone with no reference id yet.
  inherited        a method id that the starting array's own row builds on
                   is not in this claim's builds_on (milder: the reviewer
                   decides whether the new construction still rests on it).
  named            the text names an author of a reference in
                   table/references.csv, and none of that author's
                   references is in builds_on.
  new-vs-known     'new' is claimed while the construction text matches
                   the keywords of known methods.

and for the submission:

  first-time       the credit field names someone with no earlier
                   submission or table row; their credit gets a full read.

Standard library only. The DOI lookup is optional (online=False skips it)
and a failed lookup is reported as such, never as a flag.
"""
import csv
import json
import os
import re
import urllib.request

import builds_on as bo

DOI_RE = re.compile(r"10\.\d{4,9}/[^\s,;()\"<>]+", re.I)
CA_RE = re.compile(r"\bCA\(\s*(\d+)\s*;\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)")
INITIAL = r"(?:[A-Z]\.(?:-?[A-Z]\.)*\s?)"
AUTHOR_RE = re.compile(r"^(?:%s)+((?:(?:van|von|de|der|da|di|le|la)\s)*[A-Z][A-Za-z'\-]+"
                       r"(?:[ -][A-Z][A-Za-z'\-]+)?)$" % INITIAL)
CREDIT_RE = re.compile(r"credit:\s*([^;]+)", re.I)


def short(text, n=90):
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0].rstrip(",;:") + " ..."


def norm_doi(s):
    s = (s or "").strip().lower()
    for p in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "doi:"):
        if s.startswith(p):
            s = s[len(p):]
    return s.rstrip(".")


def dois_in(text):
    return [norm_doi(m.group(0)) for m in DOI_RE.finditer(text or "")]


def ref_ids_by_doi(refs):
    out = {}
    for rid, r in refs.items():
        if r.get("doi"):
            out[norm_doi(r["doi"])] = rid
        for d in dois_in(r.get("reference", "")):
            out.setdefault(d, rid)
    return out


def authors_of(reference):
    """Surnames from a reference string 'A. B. Name, C. Other and D. Third, Title...'."""
    out = []
    head = reference.split(",")
    parts = []
    for h in head:
        parts.extend(p.strip() for p in re.split(r"\s+and\s+", h.strip()))
    for p in parts:
        m = AUTHOR_RE.match(p)
        if not m:
            break
        out.append(m.group(1).split()[-1] if " " in m.group(1) else m.group(1))
    return out


def surname_index(refs):
    idx = {}
    for rid, r in refs.items():
        if rid in bo.SOURCE_IDS:
            continue
        for s in authors_of(r.get("reference", "")):
            if len(s) >= 3:
                idx.setdefault(s, set()).add(rid)
    return idx


def tokens(s):
    return {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z'\-]{2,}", s or "")}


def same_person(credit_a, credit_b):
    """Loose match of two credit strings by a shared name token of 3+ letters
    that is not a common word."""
    stop = {"and", "the", "for", "from", "with", "this", "array", "arrays", "search",
            "construction", "built", "research", "university", "team", "group", "labs"}
    a, b = tokens(credit_a) - stop, tokens(credit_b) - stop
    return bool(a & b)


def row_credit(row):
    m = CREDIT_RE.search(row.get("notes") or "")
    if m:
        return m.group(1).strip()
    m = re.search(r"\(([^()]*?\b(?:19|20)\d\d)\b", row.get("source_detail") or "")
    return m.group(1).strip() if m else ""


def row_source(row):
    """Who a row's array comes from, for messages: the person named in the
    source detail, else the credit in the notes, else the source detail."""
    m = re.search(r"\(([^(),;]*?)\s(?:19|20)\d\d\b", row.get("source_detail") or "")
    if m:
        return m.group(1).strip()
    rc = row_credit(row)
    return (rc or row.get("source_detail") or "")[:60]


def find_rows(rows, N, t, k, v):
    """Table rows that are the array CA(N; t, k, v): exact first, else rows with
    the same N, t, v and more columns (the array with columns deleted)."""
    exact = [r for r in rows if (r["t"], r["v"], r["k"], r["N"]) == (str(t), str(v), str(k), str(N))]
    if exact:
        return exact
    return [r for r in rows if r["t"] == str(t) and r["v"] == str(v) and r["N"] == str(N)
            and int(r["k"]) > k]


def doi_lookup(doi, timeout=10):
    """Creator family names of a DOI from DataCite, then Crossref. Returns
    (names, None) or (None, why)."""
    try:
        req = urllib.request.Request("https://api.datacite.org/dois/" + doi,
                                     headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as f:
            data = json.load(f)
        names = []
        for c in data["data"]["attributes"].get("creators", []):
            names.append(c.get("familyName") or c.get("name", "").split(",")[0])
        return [n for n in names if n], None
    except Exception:
        pass
    try:
        req = urllib.request.Request("https://api.crossref.org/works/" + doi,
                                     headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as f:
            data = json.load(f)
        names = [a.get("family", "") for a in data["message"].get("author", [])]
        return [n for n in names if n], None
    except Exception as e:
        return None, "DOI record not available (%s)" % type(e).__name__


def known_credits(repo, slug, table_rows):
    """Credit strings of earlier submissions and table rows."""
    out = []
    sdir = os.path.join(repo, "submissions")
    if os.path.isdir(sdir):
        for d in sorted(os.listdir(sdir)):
            if d == slug or d == "example":
                continue
            for name in ("claims.csv", "certificates.csv", "external.csv", "constructions.csv",
                         "upgrade.csv"):
                p = os.path.join(sdir, d, name)
                if not os.path.isfile(p):
                    continue
                with open(p, newline="", encoding="utf-8") as f:
                    for r in csv.DictReader(f):
                        if r.get("credit"):
                            out.append(r["credit"])
    for r in table_rows:
        c = row_credit(r)
        if c:
            out.append(c)
    return out


class Checker:
    def __init__(self, refs, table_rows, repo=None, slug="", online=True):
        self.refs = refs
        self.slug = slug
        # rows entered from this submission (on a re-check after the merge)
        # are not "earlier" rows
        self.rows = [r for r in table_rows if not slug or slug not in (r.get("notes") or "")]
        self.by_doi = ref_ids_by_doi(refs)
        self.surnames = surname_index(refs)
        self.online = online
        self.repo = repo
        self._known = None
        self._doi_cache = {}

    def _authors(self, doi):
        if doi not in self._doi_cache:
            self._doi_cache[doi] = doi_lookup(doi) if self.online else (None, "not looked up")
        return self._doi_cache[doi]

    def claim_flags(self, raw, ids, links):
        """raw: the claims.csv row; ids, links: parsed builds_on. Returns a list
        of (kind, text)."""
        flags = []
        credit = raw.get("credit", "")
        text = " ".join((raw.get("construction") or "", raw.get("notes") or ""))
        alltext = text + " " + (raw.get("source_detail") or "")
        ids = list(ids)

        # new <link>
        for link in links:
            for d in dois_in(link):
                if d in self.by_doi:
                    rid = self.by_doi[d]
                    if any(a.lower() in credit.lower()
                           for a in authors_of(self.refs[rid]["reference"])):
                        continue    # the submitter's own deposit: 'new' is right
                    flags.append(("deposit-as-new",
                                  "'new %s' is the reference %s (%s), so it is not a new "
                                  "method of this submission; cite it as %s"
                                  % (link, rid, short(self.refs[rid]["reference"]), rid)))
                    continue
                others = [r for r in self.rows
                          if d in dois_in((r.get("source_detail") or "") + " " + (r.get("snapshot_id") or ""))
                          and row_credit(r) and not same_person(row_credit(r), credit)]
                if others:
                    flags.append(("deposit-as-new",
                                  "'new %s' is the source of %d table rows credited to %s, "
                                  "not to %s; 'new' is only for the submitter's own method"
                                  % (link, len(others), row_credit(others[0]), credit)))
                    continue
                names, why = self._authors(d)
                if names is None:
                    if self.online:
                        flags.append(("doi-authors", "'new %s': %s, authors not compared "
                                      "with the credit field" % (link, why)))
                elif names and not any(n.lower() in credit.lower() for n in names):
                    flags.append(("doi-authors",
                                  "'new %s': the DOI record names %s, and the credit field "
                                  "is %r" % (link, ", ".join(names[:6]), credit)))
        if links:
            known = [s for s in bo.suggest(raw.get("construction", ""), self.refs) if s not in ids]
            if known:
                flags.append(("new-vs-known",
                              "'new' is claimed, and the construction text matches the known "
                              "method%s %s; check that the method is not one of these"
                              % ("s" if len(known) > 1 else "", ", ".join(known))))

        # starting arrays named in the text
        me = (raw.get("N"), raw.get("t"), raw.get("k"), raw.get("v"))
        seen = set()
        for m in CA_RE.finditer(text):
            N, t, k, v = (int(x) for x in m.groups())
            if (str(N), str(t), str(k), str(v)) == me or (N, t, k, v) in seen:
                continue
            seen.add((N, t, k, v))
            rows = find_rows(self.rows, N, t, k, v)
            if not rows:
                continue
            arr = "CA(%d; %d, %d, %d)" % (N, t, k, v)
            need_dep, need_inh, uncited = [], [], []
            for r in rows:
                src = (r.get("source_detail") or "") + " " + (r.get("snapshot_id") or "")
                rc = row_credit(r)
                mine = rc and same_person(rc, credit)
                if r["source_id"] != "S1" and not mine:
                    deps = [self.by_doi[d] for d in dois_in(src) if d in self.by_doi]
                    if deps:
                        need_dep += [x for x in deps if x not in ids and x not in need_dep]
                    elif rc and not same_person(rc, text):
                        uncited.append(rc)
                for x in (r.get("builds_on") or "").split(";"):
                    x = x.strip()
                    if x in self.refs and x not in ids and x not in need_inh and x not in need_dep \
                            and x not in bo.SOURCE_IDS:
                        need_inh.append(x)
            if need_dep:
                flags.append(("starting-array",
                              "the text names %s, a table row from %s; builds_on does not "
                              "list %s" % (arr, "; ".join(sorted({row_source(r) for r in rows})),
                                           ", ".join(need_dep))))
            if uncited:
                flags.append(("starting-array",
                              "the text names %s, credited in the table to %s, who has no "
                              "reference id yet and is not named in this claim"
                              % (arr, "; ".join(sorted(set(uncited))))))
            if need_inh:
                flags.append(("inherited",
                              "%s itself builds on %s, not listed here; list %s if this "
                              "construction still rests on %s"
                              % (arr, ", ".join(need_inh), "it" if len(need_inh) == 1 else "them",
                                 "it" if len(need_inh) == 1 else "them")))

        # authors named in the text
        listed = set(ids)
        flagged = set()
        for kind, msg in flags:
            if kind in ("starting-array", "deposit-as-new"):
                flagged.update(re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)+", msg))
        for name, rids in sorted(self.surnames.items()):
            if not re.search(r"\b%s\b" % re.escape(name), alltext):
                continue
            if rids & listed or name.lower() in credit.lower():
                continue
            rl = sorted(rids)
            if any(x in flagged for x in rl):
                continue    # already reported as a missing starting-array reference
            if len(rl) == 1:
                msg = "the text names %s, and the reference %s is not in builds_on" % (name, rl[0])
            else:
                msg = ("the text names %s, and none of the %d references with that author "
                       "(%s%s) is in builds_on" % (name, len(rl), ", ".join(rl[:4]),
                                                   ", ..." if len(rl) > 4 else ""))
            flags.append(("named", msg))
        return flags

    def submission_flags(self, credits):
        if self.repo is None:
            return []
        if self._known is None:
            self._known = known_credits(self.repo, self.slug, self.rows)
        out = []
        for c in sorted(set(c for c in credits if c)):
            if not any(same_person(c, k) for k in self._known):
                out.append(("first-time", "first submission credited to %r: read the credit "
                            "and sources of every claim" % c))
        return out


def render(sub_flags, claim_flags):
    """Markdown section for the PR report. claim_flags: list of (label, flags)."""
    n = len(sub_flags) + sum(len(f) for _, f in claim_flags)
    L = ["### Credit check", ""]
    L.append("Flags for the maintainer's review of credit. They do not affect the "
             "result above; the maintainer reads the credit of every submission "
             "before merging.")
    L.append("")
    if n == 0:
        L.append("No flags.")
    for kind, text in sub_flags:
        L.append("- **%s**: %s" % (kind, text))
    for label, flags in claim_flags:
        for kind, text in flags:
            L.append("- %s, **%s**: %s" % (label, kind, text))
    L.append("")
    return "\n".join(L) + "\n", n
