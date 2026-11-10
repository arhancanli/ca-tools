# How this array was built

Construction: the table's Power CZ array CA(110; 4, 120, 2) is kept fixed, and one row and one column are added
around it by search on the new cells only.

CA(111; 4, 121, 2).

The table's CA(110; 4, 120, 2) (Colbourn and Zhou 2012, Theorem 2.2 with Lemma 2.3, type 12^4 10^1) already covers
every set of four of its 120 columns. One free row (121 cells) and one free column (111 cells) are added. Only sets
of four columns that contain the new column can be uncovered. Simulated annealing works on the new cells alone,
with exact counts for those sets. Each move takes one uncovered pattern, tries a few rows that can take it, and
applies the best (after Nurmela 2004). Program programs/extt.c at temperature 3.0 reached 0 uncovered at 303
seconds. Runs at temperatures 2.0 and 1.2, started at the same time, had not finished when this one did.

Why this start. Among the arrays built by a formula, this is the one just below the target, one row and one column
away. An earlier attempt from a 107-row array with four rows and eight columns added stayed far from a solution.

The array was checked exactly with ca_verify on all 8,495,410 sets of four columns.

Built from the table's own CA(110; 4, 120, 2) only. No array of Torres-Jimenez is an ingredient or start, and the
array does not have the fingerprint of one of his arrays.

Program: programs/ in this folder (extt.c).

To rebuild:
    cc -O3 -o extt programs/extt.c -lm
    ./extt 4 CA_110_4_120_2.txt 110 120 1 1 2 1750 3.0 out
Floating point details can differ between machines, so a rebuild may give a different array of the same size.
