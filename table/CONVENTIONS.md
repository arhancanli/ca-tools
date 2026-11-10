# Conventions of the covering array table (version 1.6, November 2026)

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
  hand. A derived size made by a proven rule (fuse, derive and add1) from counted rows is as
  reliable as the weakest of those rows and counts in the frame file (section 6). It is never a row
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
- Since November 2024 the table adds every array submitted and checked here and published bounds from the
  literature, which is checked every month starting November 2026 ("What the table covers" in the README).

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
  (section 6). A derived line of the frame file carries the tier of its weakest input row: VERIFIED
  there means that every input row is VERIFIED, not that the derived array was built or checked here
  (it was not, and its get is none).

## 4. Counting rules ("best known")

The page and the files always say which counting rule a value uses. The current default is the
Colbourn rule.

Colbourn rule (current default)
- Counts CITED and VERIFIED rows.
- Does not count SCREENED, FAILED_PENDING_RECHECK, RETRACTED rows or derived sizes.
- A DISPUTED row does not remove the CITED row it disputes.
- It keeps Colbourn's record as the base and adds arrays verified here. Colbourn's record alone is the
  CITED-only lookup.

Frame rule (for the frame file `ca_frame.csv`, section 7)
- It counts what the Colbourn rule counts, plus proven derived sizes (section 6), each with the
  tier of its weakest input.
- The frame holds only counted steps, so a program reading it needs no tier filter.
- Past the counted range of its t and v it counts a derived step only where section 6's comparison
  with `derived.csv` allows. The counted range ends at the widest counted row, except that a row past
  the baseline's column range that `derived.csv` beats at its own width does not widen it (section 6).
- `ca_table.csv` itself is not changed by this rule.

A guarantee for programs that do not filter on tier. CAs 0.25 (on CRAN since 2026-11-07) with
frozen=FALSE reads `ca_table.csv` and takes the smallest N over all rows at (t, v), whatever their
tier; its default is still frozen=TRUE. The development version of CAs on GitHub (0.25-1) reads
`ca_frame.csv` instead, which holds only counted steps. So the table guarantees that no SCREENED,
FAILED_PENDING_RECHECK or DISPUTED row has an N below the counted best at its point. This holds today
for every such row (SCREENED, FAILED_PENDING_RECHECK and DISPUTED), and `tools/consistency.py` checks it on every push: a pull request that adds a
row breaking it fails, and a row already on main that breaks it is reported as a warning so the page
is still regenerated. One case can break it for a short time: a SCREENED improvement entered before
its exact check, which usually follows within one to three days. A RETRACTED row would break
this,
which is why none is entered without notice. Readers are asked to filter on tier
(tier in CITED, VERIFIED) and to ignore rows whose tier or get value they do not know.

## 5. Stability: what may be relied on

The promises below hold from now on. Of the files they name, the gzipped copy exists. The legend,
CHANGES.md and the releases are planned and do not exist yet.

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
- The table is also offered gzipped as `ca_table.csv.gz` (about 300 KB instead of
  2.8 MB), readable in R through read.csv(text = readLines(gzcon(url(...)))) (read.csv cannot read
  a gzcon connection directly). It is written without a file name or time, so the same table always
  gives the same bytes.
- Frozen releases: a dated tag table-YYYY.MM with the CSV, the gzipped CSV, the frame file, the label
  list, the legend, the R data file and a SHA256SUMS file, archived on Zenodo with a DOI through
  GitHub's integration. This is what a paper cites and what CAs can bundle for frozen=TRUE. The first
  is planned as table-2026.12, once the columns of section 7 exist and are
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
- Size rules used. The law names the program uses are fuse, derive, add1, comp, CK, CMTW34, kRoux, PCT,
  DP2, OD and SM. They will be renamed to the labels below, which the label list (section 8) will carry. fuse
  (Colbourn,
  Keri, Rivas Soriano, Schlage-Puchta 2010, Lemma 3.1), derive (same paper, (7)), add1 (same paper,
  Theorem 3.2, t >= 3), composit
  (composition, same paper, (3)), CK_doubling (Chateauneuf-Kreher doubling, as in Cohen, Colbourn
  and Ling 2008, Theorem 2), CMTW34 (Colbourn, Martirosyan, Tran Van Trung, Walker 2006, Theorem
  3.4), kRoux (k-ary Roux, same paper, Theorem 3.3, with Yin 2003), powerCT (Power CT, Colbourn and
  Zhou 2012, Theorem 2.1 with Lemma 2.4), dp (direct product with the constant-row credit of Colbourn
  and Torres-Jimenez 2013, Corollary 4.3), OD (ordered designs, Cohen, Colbourn and Ling 2008,
  Construction 1), SM (Shokri and Moura 2025).
- Proven derived sizes. A size made from CITED or VERIFIED rows by fuse, derive or add1 rests on a
  proven construction, so it is as reliable as the weakest row it comes from. add1 is Colbourn, Keri,
  Rivas Soriano, Schlage-Puchta 2010, Theorem 3.2, inequality (8), for one added column: CAN(t, k, v)
  <= CAN(t, k-1, v) + v(v-1) CAN(t-2, k-2, v) (Colbourn's label "Add 1 factors"; it reproduces all 133
  of his rows with that label from his own rows). It has two inputs, and it is used for t >= 3. The
  construction (copy a column; for each ordered pair of distinct symbols in the two copies, append a
  strength t-2 array on the other columns) is valid for every t >= 2, by the case analysis of the
  three kinds of t-sets, and was checked on arrays built here from arrays on file and verified
  exhaustively (31 at t = 2 and 3, 21 at t = 4 to 6). For t >= 4 the second input, the strength t-2
  ingredient, is a row (or a row fused or derived); for t = 3 it is the trivial strength 1 array
  CA(v; 1, k-2, v), the v constant rows, so a step at t = 3 adds v(v-1)v and names no ingredient. A
  proven derived size counts in the frame file as its own step, with the tier of its weakest input
  (CITED if one of its rows is CITED) and its working: the source row's own construction label
  followed by ':fuse', ':derive' or ':add1' for each step, in the order applied (for example
  Sherwood covering perfect hash family (affine):fuse:fuse, or SCPHF Random Extension (CLS):add1).
  This is close to CAs's Source labels but not the same: CAs 0.25 writes a run of ':fuse' or of
  ':add1', never both, and ':derive' last, while a working here may mix them (for example
  ':fuse:add1' or ':derive:fuse'). The source
  row's id is in ids_all, followed by '+' and the id of each add1 step's ingredient row at t >= 4, so
  every author stays traceable. The ingredient of an add1 step at t >= 4 is the smallest size at
  strength t-2 that fuse and derive give from the rows (never itself made by add1), and only its row
  is named, not its own steps; among ingredients of that size a VERIFIED row is named before a CITED
  one, so the step keeps the highest tier it can have. The frame file
  builds no derived size from the three CITED cyclotomy rows that have DISPUTED rows beside them,
  neither as source nor as ingredient. Fuse keeps the width, derive lowers it by one and add1 raises
  it by one, so past the baseline's column range a proven derived size appears only near a counted
  row (at its width, one less per derive, one more per add1). No ladder of widths is used for the
  frame file. Past every counted row of its t and v, only sizes made by fuse alone count for now, and
  such a size counts only if no line of `table/derived.csv` at the same t and v, at a width k' >= k,
  by any size rule counted or not, has a smaller N. An uncounted rule is used there only to withhold a
  line, never to give a value, so a line withheld today returns if its size drops to the derived.csv
  value or below, if that value rises, or once a counted row at that width or wider puts it inside
  the counted range. Between two steps the frame line speaks for every narrower width down to the
  previous step, and there an uncounted rule may give less: today the frame line is up to 10 percent
  above it (93,623 against 84,909 at t = 3, v = 24, k = 17,500), and up to 23 percent above it inside
  the counted range (CA(11295781276; 6, 10000, 20) against 9,178,224,188 by PCT at k = 30,000). As only
  fuse counts there, no line there ends in an add1 or derive step (a working may pass through such a
  point and land inside the counted range of another t or v, for example after a derive or a fuse);
  derived points beyond the counted range by derive or add1 come later. The counted range of a t and v
  ends at its widest counted row, with one exception (version 1.4): a row past the baseline's column
  range whose N is above a line of `derived.csv` at the same t and v and a width k' >= k (by any size
  rule) counts as a row, but does not widen the range, so the derived sizes between the range and that
  row are judged as above. Without it a weak row would let derived sizes in unchecked: a VERIFIED
  CA(1000; 3, 100000, 2), against PCT 99, would have let in 231 lines of 80 to 996 against
  `derived.csv` values of 77 to 99. Such a row is flagged for the maintainer, who decides each one:
  `tools/check_submission.py` shows "above a published size rule" with the `derived.csv` value and
  width (and the number of flagged claims in its result line), and how many frame lines a row past
  the counted range lets in, and `tools/consistency.py` reports every such row as a warning on every
  run, so also a row that a regenerated `derived.csv` comes to beat, unless
  `table/above_rule_rows.csv` lists it as accepted knowingly (id, reason, decided_by, date). It
  is a flag, not a refusal: the array is correct, and the uncounted rules in `derived.csv` are not
  checked enough to refuse an array. Today one row is such a row and is listed:
  CA(6580; 6, 10051, 2) (Power CZ), against PCT 6555 at k = 11,000; the frame is unchanged by it. The search for add1 chains
  stops a chain only once no later step can land below a counted row inside the counted range of any
  t and v it can reach, so it finds every step the rule gives.
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
    rows say "array file not stored since 2026-10-27" in their notes), the three Torres-Jimenez rows of
    the CAs data TJ2level_CAs whose arrays were never stored (CA(177; 4, 338, 2), CA(178; 4, 354, 2),
    CA(179; 4, 358, 2), listed in the same file on 2026-11-09), and any other row whose array is
    nowhere the table can
    point to.
- The exact locator (file path, deposit link, URL, R call or rebuild command) is in the frame file,
  not in `ca_table.csv`, to keep the file CAs downloads small.
- Until these columns are added, the frame file computes id, constant_rows, constant_rows_basis and
  get itself (`tools/build_frame.py`), by the same rules. constant_rows is filled only where the
  array is in `table/arrays/` with its exact count, and a derived step has get none. When the named
  row of a step has get none but another counted VERIFIED row tied at the same step (same t, v, k
  and N) has an array, the frame line takes get and get_ref from the first such row in the order of
  section 9; its id, tier, constant_rows and construction stay those of the named row, and the row
  lending the array is in ids_all.

The frame file is `ca_frame.csv`, with one line per step under the frame rule (section 4)
and the columns t, v, k, N, basis (row or derived), tier, id, constant_rows, constant_rows_basis, get,
get_ref (the locator), construction (one label, the named row, or the working of a derived step: the
source row's label, then ':fuse', ':derive' or ':add1' for each step; the steps are the trailing
':fuse', ':derive' and ':add1' pieces, v of the source - v, t of the source - t and k - k of the source
+ t of the source - t of them, and no label ends in one, so a colon or comma inside a label never
confuses the split; fields with commas are quoted as CSV quotes them),
family (section 8), constructions_all and ids_all (every counted row that reaches the same N),
prev_id (the previous best at that step: on a row line the best counted row entered before the first
row that reached the step's N, the rows of one snapshot entered on one day counting as one entry;
on a derived line the row of the Colbourn-rule value it improves on), entered, and the date it was
generated (the latest entry date in `ca_table.csv`, so an unchanged table gives the same file). The five columns CAs
reads (t, v, k, N, construction) keep their names and meaning here too. It is generated, never edited
by hand (`tools/build_frame.py`; after every merge to main, `tools/consistency.py` in table-page.yml
compares it with a fresh build),
and it is the one table to read for "what is best here, how is it made, and how do I get it".
The full history stays in `ca_table.csv`, which keeps every row.

[planned, not built yet] On the page, every rung will get a "get" link built from get and get_ref (the
raw file, the deposit, the URL, the R call as text, or the certificate with its one-line command, or
"no array, cited from ..."), and a search box at the top will jump to a point by t, v and k. Today the
page links the array file, deposit or certificate where a row has one, and the rebuild command is in
the frame file only.

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
- Working grammar: unary steps after the source label, LABEL:step:step in the order applied (for
  example Sherwood covering perfect hash family (affine):fuse:fuse, with fuse, derive and add1; the
  order may mix them, which CAs's own labels do not, section 6). add1 has a second input but is
  written as a step, as CAs writes it; its second input is named in ids_all (section 6). A source
  row whose label is empty, contains " || " or ends in ':fuse', ':derive' or ':add1' is written by
  its id instead, in a working and in constructions_all, so a working always splits. Binary size rules as
  LAW(id1,id2) with the ids of section 7 (for example dp(t2-v3-k20-1,t2-v3-k7-2)). Machine files also carry the working as a list.
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
  rows (a row whose count is unknown ranks below every row with a known count, even an earlier one),
  then the earlier priority date, then the wider array, then the id.
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
- Version 1.1 (November 2026). The frame file `ca_frame.csv` and the gzipped copy `ca_table.csv.gz`
  exist (sections 4 to 7, which said "will"). The frame counts fuse and derive, not add1 yet, and its
  derived steps past the baseline's column range come only from rows of that width (by fuse alone
  past every counted row of the same t and v). A derived step's construction is the source row's
  label followed by ':fuse' or ':derive' for each step, and its source row's id is in ids_all. A step
  whose named row has no array takes get and get_ref from a tied VERIFIED row that has one (section 7).
  The guarantee of section 4 is checked on every push.
- Version 1.2 (November 2026). add1 now counts in the frame file (sections 1, 4, 6, 7, 8 and 9): Colbourn,
  Keri, Rivas Soriano, Schlage-Puchta 2010, Theorem 3.2, one added column, CAN(t, k, v) <= CAN(t, k-1,
  v) + v(v-1) CAN(t-2, k-2, v), for t >= 3 (at t = 3 the ingredient is the trivial strength 1 array,
  v constant rows, and no ingredient row is named). A step made with add1 has the tier of its weakest
  row (a VERIFIED ingredient named before a CITED one of the same size), its working ends in ':add1'
  once per added column, and ids_all names the source row, then '+' and each add1 ingredient row at
  t >= 4. Workings are written in the order applied, which may mix steps in ways CAs's labels do not
  (sections 6 and 8). `tools/derive_table.py` uses the same rule for `table/derived.csv`. Section 9
  says how an unknown constant-row count ranks.
- Version 1.3 (November 2026). Past the counted range a fused size counts only where no size rule in
  derived.csv gives less (sections 4 and 6); 10 lines at t = 3, v = 2 and 3 removed, reported by
  Arhan Canli (#62).
- Version 1.4 (November 2026). A counted row past the baseline's column range that derived.csv beats
  at its own width counts, but does not widen the counted range of the frame, and is flagged for the
  maintainer by tools/check_submission.py and, on every run, tools/consistency.py, with a list of rows accepted
  knowingly, table/above_rule_rows.csv (sections 4 and 6). The frame file is unchanged by it.
- Version 1.5 (November 2026). Section 2 says what the table adds to the baseline and that the literature is
  checked every month starting November 2026. No rule changed.
- Version 1.6 (November 2026). Wording only, after the audit of 2026-11-10; no rule changed. Section 3
  says what the tier of a derived line means, section 4 which file each version of CAs reads, and
  section 7 marks the get links and the search box of the page as planned.
