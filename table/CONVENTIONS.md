# Conventions of the covering array table (version 1, November 2026)

Parts that describe files not built yet say "will" or "planned". Anything that changes what the CAs package
reads is announced to its author before it goes live (section 5).

This document says what the table's words and numbers mean, what is stable and may be
relied on, and how to get from a size to an array. It separates what the table inherits from Charles
J. Colbourn's covering array tables from what this table adds. A change to it is a new version with a
line in the change log at the end.

## 1. Words

- Covering array CA(N; t, k, v): an N by k array over v symbols in which every choice of t columns
  shows every one of the v^t combinations in some row. N rows, strength t, k columns, v symbols.
- Row: one line of `table/ca_table.csv`. Each row is one claim that N rows suffice for strength t on
  k columns of v symbols, with its evidence, or the record of a check against such a claim.
- Point: a triple (t, v, k).
- Stair step (Colbourn's reading): a row (t, v, k, N) also covers every k' below k. The best value at
  a point is the smallest N among the counted rows with at least k columns. The step of that row is
  called a rung.
- Counting rule: the rule that says which rows count when the table answers "what is the best known
  N at this point". Section 4.
- Tier: the evidence class of a row (section 3). This document says "tier", never "status". Two
  files have their own column named status with other meanings: in `table/MANIFEST.csv` it compares
  an array with the table at entry (equals_best, exceeds_snapshot, above_snapshot, above_best,
  screened), in `table/EXTERNAL.csv` it is verified when a VERIFIED row carries the deposit's hash.
  The page's column headed status shows the MANIFEST status and will be relabelled.
- Provenance class: the column `source_id` (S1 Colbourn snapshot, S4 NIST covering array library,
  S5 Dwyer's CA_Database, S6 data objects of the CAs package, S7 literature and submissions, S8
  arrays built in this project). S2 and S3 are defined in the README and have no rows. This column
  is not Colbourn's "Source" and not the "Source" of CAs, which both mean the construction.
- Construction label: the column `construction`. For the 13,641 rows from Colbourn's tables it is his
  label exactly as recorded ("Source" in his tables and in CAs). For newer rows it is the
  submitter's or the maintainer's description. CAs shows this column as Source.
- Label code: a parameter code inside one of Colbourn's labels, such as T, S, Arc, c, Trin or +p in
  "Power N-CT 5^3T2".
- builds_on: the published work a row rests on, as ids from `table/references.csv`, separated by
  semicolons. The only construction field a program can read without parsing text.
- Constant rows of an array: the largest number of its rows that can be made constant by permuting
  symbols within columns, each symbol counted once (at most v).
- Size rule: one construction's rule for the size of its result as a function of its ingredients'
  sizes.
- Derived size: a size obtained by applying a size rule to sizes in the table. It is not an array in
  hand. A derived size made by a proven rule (fuse and derive, and add1 once implemented) from a
  counted row is as reliable as that row and will count in the frame file (section 6). It is never a row
  of `ca_table.csv`.
- Working: the list of lookups a derived size used, followed back to rows.
- Derived-sizes program: `tools/derive_table.py`, which writes `table/derived.csv`.
- Solved from the record: a parameter computed so that a size rule reproduces Colbourn's recorded
  sizes, because no paper states it. Example: the hash family size of the Power
  N-CT rows, one integer per key.
- Three phrases say how far a construction label was checked here:
  - Not checked here: nothing was tried, or the recipe was never published (for example "Direct
    product generalized", and the labels with no size rule, section 6).
  - Reading not confirmed: a reading of a recipe was tested here and did not give the recorded size
    (the Power N-CT hash family sizes at four keys). The recorded size may still be right.
  - Fails as published: the exact recipe was built here and is not a covering array at the recorded
    size. Such a row gets a DISPUTED row beside it (section 3). It does not mean the size cannot be
    reached another way.
- eCAN, eCAK: the names of the CAs functions and of Colbourn's empirical bounds. The table itself says
  "best known N".

## 2. What is inherited from Colbourn's tables

- The baseline is the November 2024 status of Colbourn's tables, which Ulrike Groemping preserved in
  her CAs package as `colbournBigFrame` after the original site became unavailable. It has 13,641
  rows, 2 <= v <= 25, 2 <= t <= 6, k up to 20,000 at strength 2 and 10,000 at strengths 3 to 6,
  tier CITED, provenance class S1, snapshot `colbourn-2024-11-ug`.
  They are kept exactly as recorded, construction labels included, and never edited.
- Colbourn's tables give one (N, k) per rung and a construction label. They record no arrays and no
  ingredient properties such as constant rows or partitions. Most of their sizes therefore have no
  array that anyone can download. The table says so for each row (section 7, the get column).
- What a label means is known directly only where a paper states it. Where a meaning was worked out
  here from the record itself, the label list (section 8) says so with the basis "solved from the
  record" or "read from the record". A size reached only by such a reading is never counted. Proven
  rules applied to counted rows are different (section 6).

## 3. Tiers of a row

Current counts per tier are in `table/README.md`.

- CITED: traceable to a dated snapshot or a publication. No array checked here.
- VERIFIED: an explicit array was checked here exhaustively at strength t by a named verifier
  (caverify, ca_verify, external_array for deposits, cphfcheck and repcheck for covering
  perfect hash family certificates, construction_cert for construction certificates). The row carries the
  array's SHA-256 (or, for a certificate, the family's) and the
  verifier's stamp. The array itself is not always stored in this repository: section 7 says, row by
  row, where it is.
- SCREENED: an array too large for the public exact check, checked on random column windows only. It
  applies only to new arrays, never to CITED rows.
- FAILED_PENDING_RECHECK: three rows of 2026-08-23, kept as history. Each was explained and
  superseded by a VERIFIED row at the true size. No new rows of this tier are written.
- DISPUTED: an added row beside a CITED row whose cited construction, as implemented and checked
  here, did not give a covering array at the recorded size. The CITED row stays unchanged. A DISPUTED
  row says what failed and how it was checked, not that the size cannot be reached.
- RETRACTED: defined for a VERIFIED row later found wrong. None exists. None is entered without
  telling the maintainer of the CAs package first (section 5).
- Derived sizes are not rows. They live in `table/derived.csv` and, for proven rules, in the frame file
  (section 6).

## 4. Counting rules ("best known")

The page and the files always say which counting rule a value uses. The current default is the
Colbourn rule.

Colbourn rule (current default)
- Counts CITED and VERIFIED rows.
- Does not count SCREENED, FAILED_PENDING_RECHECK, RETRACTED rows or derived sizes.
- A DISPUTED row does not remove the CITED row it disputes.
- It keeps Colbourn's record as the base and adds arrays verified here. Colbourn's record alone is the
  CITED-only lookup.

Frame rule (planned, for the frame file `ca_frame.csv`, section 7)
- It will count what the Colbourn rule counts, plus proven derived sizes (section 6), each with the
  tier of its weakest input.
- The frame will hold only counted steps, so a program reading it needs no tier filter.
- `ca_table.csv` itself is not changed by this rule.

A guarantee for programs that do not filter on tier. CAs 0.25 with frozen=FALSE takes the smallest N
over all rows at (t, v), whatever their tier. So the table guarantees that no SCREENED,
FAILED_PENDING_RECHECK or DISPUTED row has an N below the counted best at its point. This holds today
for all 52 such rows, and `tools/consistency.py` will check it on every push. A RETRACTED row would break
this,
which is why none is entered without notice. Readers are asked to filter on tier
(tier in CITED, VERIFIED) and to ignore rows whose tier or get value they do not know.

## 5. Stability: what may be relied on

The promises below hold from now on. The files they name (the legend, CHANGES.md, the gzipped
copy, the releases) are planned and do not exist yet.

This section is the promise to everyone who reads the table by program, CAs first.

- The 17 columns of `table/ca_table.csv` keep their names and meaning forever. New columns are only
  ever added at the end. A column no longer filled keeps its header and is marked retired in the
  legend.
- Every new column holds an integer, an empty field, a value from a closed list, or, for id only, a
  value of the fixed grammar of section 7. Never free text,
  because R's read.table types a whole column from its values.
- Closed lists (tier, get, constant_rows_basis, and later family) only grow. A new value is announced
  at least 30 days before its first use, in `CHANGES.md`, in the release notes, and by email to
  the maintainer of the CAs package. `tools/consistency.py` refuses any value not in its list (tier
  today, the others once their columns exist).
- The construction text of a row is corrected only to fix credit, through `tools/correct_credit.py`,
  and every correction is logged in `table/CREDIT_CORRECTIONS.csv` with the row's id. CAs shows this
  text as Source, so such corrections are mentioned to its maintainer.
- Rows are never deleted. A wrong row is superseded or disputed by an added row.
- The legend of every column (meaning, allowed values, who fills it, since when) will be
  `schema.json`, with a readable copy `SCHEMA.md` generated from it, and its version
  number. Additions raise the minor version. A breaking change is never made to an existing file.
  If one were ever needed it would go to a new file name, and the old file would keep being written
  for at least 12 months.
- The table will also be offered gzipped as `ca_table.csv.gz` (about 300 KB instead of
  2.8 MB), readable in R through gzcon(url(...)).
- Frozen releases: a dated tag table-YYYY.MM with the CSV, the gzipped CSV, the frame file, the label
  list, the legend, the R data file and a SHA256SUMS file, archived on Zenodo with a DOI through
  GitHub's integration. This is what a paper cites and what CAs can bundle for frozen=TRUE. The first
  is planned as table-2026.12, once the columns of section 7 and the frame file exist and are
  checked.
- If the maintainer stops, the Zenodo record and the frozen copy in CAs remain, and the repository can
  be forked under its code and data licences (section 11).

## 6. Derived sizes

- `tools/derive_table.py` applies published size rules to the counted sizes at every point of the
  table, repeats until nothing changes, and writes `table/derived.csv`. It has one line per point where
  a derived size is below the counted stair step, with columns t, v, k, N, lookup_N (the counted
  value it beats), gain_pct, law (the size rule), arithmetic (every ingredient value used) and round.
  It is regenerated from scratch on every push, so a derived size moves whenever an ingredient
  improves. Past the baseline's column range it also evaluates a ladder of widths up to 100,000, and
  there lookup_N and gain_pct are empty where the table has no counted value.
- Size rules used. The law names the program uses are fuse, derive, comp, CK, CMTW34, kRoux, PCT, DP2,
  OD and SM. They will be renamed to the labels below, which the label list (section 8) will carry. fuse
  (Colbourn,
  Keri, Rivas Soriano, Schlage-Puchta 2010, Lemma 3.1), derive (same paper, (7)), composit
  (composition, same paper, (3)), CK_doubling (Chateauneuf-Kreher doubling, as in Cohen, Colbourn
  and Ling 2008, Theorem 2), CMTW34 (Colbourn, Martirosyan, Tran Van Trung, Walker 2006, Theorem
  3.4), kRoux (k-ary Roux, same paper, Theorem 3.3, with Yin 2003), powerCT (Power CT, Colbourn and
  Zhou 2012, Theorem 2.1 with Lemma 2.4), dp (direct product with the constant-row credit of Colbourn
  and Torres-Jimenez 2013, Corollary 4.3), OD (ordered designs, Cohen, Colbourn and Ling 2008,
  Construction 1), SM (Shokri and Moura 2025).
- Proven derived sizes. A size made from a CITED or VERIFIED row by fuse or derive (and add1 once it
  is implemented) rests on a proven construction, so it is as reliable as the row it comes from. It
  will count in the frame file as its own step, with the tier of its weakest input and its working
  written as CAs writes it (for example RMScopiesCA:fuse:fuse). The frame file will build no derived
  size from the three CITED cyclotomy rows that have DISPUTED rows beside them. Proven derived sizes past
  the baseline's
  column range come later.
- The other size rules (composit, CK_doubling, CMTW34, kRoux, powerCT, dp, OD, SM) stay in
  `table/derived.csv` and on the derived page, and are not counted. Each is added to the proven list
  only after it has been checked, with a line in the change log.
- No derived size is ever a row of `ca_table.csv`. An array built and checked from a derived size
  enters as a row like any other array. Derived sizes will also be shown on the main table page.
- Constant rows in derived sizes: `derived.csv` does not yet record them. Every size rule assumes one
  constant row per ingredient (Colbourn and Torres-Jimenez 2013, Observation 3.2). Once the
  constant_rows column exists, a fused size will inherit its ingredient's count, as the fuse of the
  CAs package does, and the other rules will be credited with what they guarantee.
- Reproducing Colbourn's own labels is a separate question. Of the 13,641 baseline rows, 4,425 are
  reproduced by a known size rule from other table entries. The other 9,216 have no size rule that
  fits them: about 3,600 are search results, 380 were post-optimized, and the rest are direct
  constructions (cyclotomy, Paley, orthogonal arrays and others) or rules not yet wired in. For those
  rows a missing derived size says nothing.

## 7. Getting from a size to an array

Four columns will be added at the end of `table/ca_table.csv`:
- id: a readable identifier stored at entry and never changed, spelled t3-v13-k197-1 (with
  letters naming the parts: strength,
  symbols, columns, then the row's number at that point in file order). The letters avoid the
  misreading of a bare 3-13-197-1 against the usual order CA(N; t, k, v). Every row has one,
  counted or not. The 16-digit hexadecimal row key stays inside the tools only, and
  `table/CREDIT_CORRECTIONS.csv` gains an id column. The id is also the anchor of the row on the
  page (#t3-v13-k197-1).
- constant_rows: an integer, or empty.
- constant_rows_basis: one of exact, lower_bound, inherited, empty. Stored arrays get the exact count
  where it can be computed in reasonable time. Very large arrays and certificates get a guaranteed
  lower bound. Rows cited from Colbourn's tables have no array and stay empty rather than guessed.
- get: one of file, deposit, url, cas, certificate, construction, none. It says where the array is,
  as of the latest regeneration, and `tools/consistency.py` will recompute it on every push.
  - file: in this repository, `table/arrays/` (gzipped when large).
  - deposit: in an archive deposit such as Zenodo, named in `table/EXTERNAL.csv`.
  - url: on a public site the row names (the NIST library, Dwyer's CA_Database).
  - cas: built by a function of the CAs package that the row names.
  - certificate: rebuilt from a covering perfect hash family in `table/certificates/` with the command
    given in the frame file.
  - construction: rebuilt from a construction certificate in `table/constructions/`.
  - none: no array is available from this table. All CITED rows, every row whose array file was
    withdrawn on 2026-10-27 (the files are listed in `table/withdrawn_files.csv`, and most of these
    rows say "array file not stored since 2026-10-27" in their notes), and any other row whose array is
    nowhere the table can
    point to.
- The exact locator (file path, deposit link, URL, R call or rebuild command) is in the frame file,
  not in `ca_table.csv`, to keep the file CAs downloads small.

The frame file will be `ca_frame.csv`, with one line per step under the frame rule (section 4)
and the columns t, v, k, N, basis (row or derived), tier, id, constant_rows, constant_rows_basis, get,
get_ref (the locator), construction (one label, the named row, or the working of a derived step),
family (section 8), constructions_all and ids_all (every counted row that reaches the same N),
prev_id (the previous best at that step), entered, and the date it was generated. The five columns CAs
reads (t, v, k, N, construction) keep their names and meaning here too. It is generated, never edited
by hand, and it is the one table to read for "what is best here, how is it made, and how do I get it".
The full history stays in `ca_table.csv`, which keeps every row.

On the page, every rung gets a "get" link built from get and get_ref (the raw file, the deposit, the
URL, the R call as text, or the certificate with its one-line command, or "no array, cited from ...").
A search box at the top jumps to a point by t, v and k.

## 8. Labels and workings

- `lexicon.csv` will map every construction text to a short family label, with columns label
  (a pattern over the construction text), family, cas_label (the CAs spelling where one exists),
  builds_on, meaning, basis. It is built from the keyword patterns already in
  `table/references.csv`, so the two cannot drift apart. Corrections are welcome by issue or email.
- `families.csv` will be the closed list of family labels. It starts from the 31 CAs labels
  with the CAs spellings (KSK, PALEY, CAEX, CYCLOTOMY, CKRS, powerCT, DWYER, NIST, WKS, CK_doublingCA,
  dpCA, ODbasedCA, pcaCA, cphfCA, scphfCA and the others), and adds the families that list does
  not cover (for example powerCZ, power N-CT, Roux-type, perfect hash family,
  Martirosyan-Tran Van Trung, Sherwood affine CPHF, Shokri-Moura, RMS extension, SBSTT, IPOG-F
  post-optimization, the search methods). The 530 construction texts backfilled on 2026-10-20 from
  catalogue descriptions get basis "from the catalogue".
- Family appears in the frame file and the machine files, not (yet) in `ca_table.csv`, because the
  list will change while it is being agreed.
- Working grammar: unary steps as CAs writes them, FAMILY:step:step (for example
  CYCLOTOMY:fuse:fuse, with fuse, derive and add1). Binary size rules as LAW(id1,id2) with the ids of
  section 7 (for example dp(t2-v3-k20-1,t2-v3-k7-2)). Machine files also carry the working as a list.
  The binary form is shown to the author of CAs before its first use.
- "Direct product generalized" in Colbourn's labels (1,573 rows, plus one with a post-optimization
  suffix): Colbourn and Torres-Jimenez 2013
  define generalized direct products in Section 4, but the tables do not say which one each row used,
  and the recorded sizes need profiles that were not published, so they are not checked here. This
  table does not assume it means Corollary 4.3. Arrays built here by the product of Corollary 4.3 say
  so by name.

## 9. Ties and credit

- When several counted rows reach the same N at a point, the frame file lists all of them in
  constructions_all and ids_all. The construction column of `ca_table.csv` keeps one label per row.
  The headline (the named row) is chosen in this order: a CITED row stays named, then more constant
  rows, then the earlier priority date, then the wider array, then the id.
- An array that only equals a value already in the table is not an improvement and does not take the
  headline from a CITED row. It is still listed and credited.
- Credit is recorded today in the notes column, starting "credit: ". It moves, as roles are needed,
  to `credits.csv` (id, role, name, reference) with the roles method, ingredient, first reached
  and verified. Comparison phrases written at entry stay in notes as history, with one spelling from
  now on: "at entry: previous best N (k=..., tier, provenance class)".

- Corrections of any kind are welcome by issue or email.

## 10. A machine view for programs and AI [planned, nothing of this exists yet]

- `api/v1/` (in docs/) on the project's GitHub page will be a view of the table for programs, generated
  from `table/ca_table.csv` and the files it names by `render_api.py` (in tools/), never edited by hand,
  and checked byte for byte by `tools/consistency.py`. It will never be a second source. Every value in
  it will be computed from the CSV.
- Files: manifest.json (schema version, the commit it was built from, the licence text, the SHA-256 of
  every file), rows.jsonl (one record per row, in file order, only fields that never change),
  t<t>/v<v>.json (the counted rungs as a list of {k, N, id} for a fast lookup, plus the fields that
  change over time, such as get), derived/t<t>/v<v>.json, references.json, lexicon.json, and JSON
  Schemas for the records.
- The same promise as section 5 applies: fields are only added within v1, and a breaking change would
  go to v2 beside v1.
- A claim can be checked without trusting the table: look the point up, fetch the array from get,
  compare its SHA-256 with the row, and run the open verifier (ca_verify, built from this repository
  at the commit in the row's stamp) on it.

## 11. Scope, licence and citation

- Scope: strengths 2 to 6, at most 25 symbols, at most 100,000 columns. The checks refuse claims
  outside it. Fused sizes are never rows. Proven ones count in the frame file (section 6).
- Licence: the compilation (selection, arrangement, identifiers, verification stamps, and the arrays
  and certificates built by this project) is CC BY 4.0. Each row's size and array remain under the
  terms of the source the row names. Sizes themselves are facts and may be reused with a citation.
  The code is MIT.
- Citation: through `CITATION.cff` and the Zenodo DOI of the frozen release used (both planned with
  the first release).

## Change log

- Version 1 (November 2026). First version in force, after drafts 0 to 3 (October and November 2026)
  and comments from readers. Main points are the words of section 1, with three phrases for how far a
  label was checked, and the stability promises of section 5. Proven derived sizes (fuse and derive,
  and add1 once implemented) will count in the frame file with the tier of their inputs, never as rows
  (sections 4 and 6). Section 7 adds the four new columns and the frame file with a pointer to the
  previous best, and section 8 the label list.

