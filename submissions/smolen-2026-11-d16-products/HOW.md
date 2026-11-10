# How these arrays were built

Construction: the four ternary arrays are profile products of two arrays of this table, followed by column
extension by simulated annealing. The binary strength-5 array is a group-orbit array found by annealing on orbit
classes.

## The ternary arrays: CA(27; 2, 436, 3), CA(33; 2, 1969, 3), CA(34; 2, 2306, 3), CA(37; 2, 4556, 3)

Profile product (the method of Colbourn and Torres-Jimenez 2013, "Profiles of covering arrays of strength two",
Thm 4.2 / Cor 4.5; no array of theirs is used). Take A = CA(N; 2, k, 3) with two rows that agree in d1 columns and
B = CA(M; 2, l, 3) with two rows that agree in d2 columns. Rename the symbols of each column so that in A the first
chosen row is all 0 and the second is 2 where the two differ and 0 where they agree, and in B the first chosen row
is all 1 and the second is 2 where they differ and 1 where they agree. Columns are the pairs (a, b). Drop the two
first chosen rows, merge the two second chosen rows into one row, and drop the d1 x d2 columns where both pairs
agree. The result is CA(N + M - 3; 2, kl - d1 d2, 3). Program programs/pprod.py. programs/agree.py lists the row
pairs with the fewest agreements.

Column extension. The repo's tools/own_arrays/ext2.c adds one column at a time to a covering array and repairs it
by simulated annealing (SAT = temperature; NEWCOLTRY = number of random candidate columns tried for each new
column). All cells, old and new, may change. Long runs stall on one column, so after the first runs the search
was done in short runs, each with a new seed, each starting from the last covering array (programs/reseed_loop.sh).
Most of the gain comes in the first seconds of each run.

In fact the product survives almost unchanged: the first columns of each final array, in the same row order, are
the raw product with only 10 (27 rows), 15 (33 rows), 2 (34 rows) and 0 (37 rows) cells changed. The other
columns were added by ext2.

| Array | Product (rows used, agreements) | Raw product | Extension |
|---|---|---|---|
| CA(27; 2, 436, 3) | 15@20 (0, 3; 5) x 15@20 (0, 3; 5) | 27@375 | ext2 to 419, then 15 s runs, seeds 101 to 114 |
| CA(33; 2, 1969, 3) | 15@20 (0, 3; 5) x 21@93 (14, 20; 21) | 33@1755 | ext2 seeds 3, 4, 5 to 1878, then 15 s runs, seeds 101 to 105 |
| CA(34; 2, 2306, 3) | 15@20 (0, 3; 5) x 22@107 (15, 16; 24) | 34@2020 | short runs, seeds 101 to 108 |
| CA(37; 2, 4556, 3) | 15@20 (0, 3; 5) x 25@220 (0, 3; 48) | 37@4160 | 25 s runs, seeds 101 to 104 |

The 34- and 37-row runs were stopped for time while still gaining. The 33-row run had a cap of 1970 columns.

## The binary array: CA(98; 5, 17, 2)

Columns 0 to 15 are indexed by the vectors of GF(2)^4, and the group Z_2^4 acts on them by XOR on the index.
Column 16 is fixed by the group. The rows are the 16 images of each of 6 generator words of 17 bits, plus the
all-zero and all-one rows: 6 x 16 + 2 = 98 rows. Annealing changes the generator words and counts coverage exactly
on one representative of each group orbit of 5-sets (413 classes). It starts from random words; no array is read.
programs/mkact.py writes the group action and the word list (spec file) and programs/grpm.c anneals. The
generator words are in programs/CA_98_5_17_2_gen.txt (the last two lines are the constant rows).

Built from: the ternary arrays are built from the table's own arrays only:
- CA_15_2_20_3_fd13075b.txt (row S8, tabu search from a random start, tools/own_arrays/ext2.c),
- CA_21_2_93_3.txt (row S7, submission smolen-2026-11-t2v3-k93),
- CA_22_2_107_3_eed6545c.txt (row S8, generalized direct product with the Bose OA(9; 2, 4, 3), then ext2.c),
- CA_25_2_220_3.txt (row S7, submission smolen-2026-11-debate9).
The files used are the table files (the same arrays: canonical sha256 fd13075b..., 2a3647eb..., eed6545c...,
1891199a...). None of the four has the fingerprint of a Torres-Jimenez array or of a withdrawn file
(table/tj_fingerprints.csv, table/withdrawn_fingerprints.csv). The CA(25; 2, 220, 3) has its own chain, stated in
its row: a CA(12; 2, 7, 3) built here by caex.c from the Bose OA(9; 2, 4, 3), which has the same fingerprint as a
Torres-Jimenez array of that size, times the CA(15; 2, 20, 3), then column extension and column search. The binary
array is built from nothing (random start).

Program: everything below runs from a folder holding the programs and the four table files. ext2 is
tools/own_arrays/ext2.c of this repository. All programs here, and ext2.c, were written by AI agents working for
this project.

    cc -O3 -o ext2 tools/own_arrays/ext2.c -lm
    A=CA_15_2_20_3_fd13075b.txt
    python3 programs/pprod.py $A 0 3 $A 0 3 p27.txt
    python3 programs/pprod.py $A 0 3 CA_21_2_93_3.txt 14 20 p33.txt
    python3 programs/pprod.py $A 0 3 CA_22_2_107_3_eed6545c.txt 15 16 p34.txt
    python3 programs/pprod.py $A 0 3 CA_25_2_220_3.txt 0 3 p37.txt

    # 27 rows: a 45 s calibration run reached 416 columns (its seed was not recorded; 1 here); seed 2 reached 419
    SAT=0.3 NEWCOLTRY=20 ./ext2 27 440 3 1 45 x27a p27.txt 375
    SAT=0.3 NEWCOLTRY=20 ./ext2 27 440 3 2 800 x27c x27a_27_last.txt 416
    ./programs/reseed_loop.sh x27c_27_last.txt 420 200 27 445 15

    # 33 rows (runs stopped by hand after about 300 s, 330 s and 100 s, when they stalled)
    SAT=0.3 NEWCOLTRY=20 ./ext2 33 1970 3 3 800 x33a p33.txt 1755
    SAT=0.3 NEWCOLTRY=20 COLRESAMPLE=8000000 ./ext2 33 1970 3 4 780 x33b x33a_33_last.txt 1867
    SAT=0.5 SAT1=0.2 SAL=15000000 NEWCOLTRY=20 ./ext2 33 1970 3 5 480 x33c x33b_33_last.txt 1874
    ./programs/reseed_loop.sh x33c_33_last.txt 500 200 33 1970 15

    # 34 rows (budget 240 s; stopped by hand after about 145 s and 8 seeds, 101 to 108; the run length per seed
    # was not written down, 15 s as above, and a rerun of seed 101 at 15 s gives the logged 2020 to 2181 columns)
    ./programs/reseed_loop.sh p34.txt 240 200 34 2400 15

    # 37 rows (stopped after 4 seeds)
    ./programs/reseed_loop.sh p37.txt 420 200 37 4700 25

reseed_loop.sh START SECONDS NEWCOLTRY N KCAP RUNSECONDS runs
`SAT=0.3 NEWCOLTRY=... ./ext2 N KCAP 3 seed RUNSECONDS lpN START k` with seeds 101, 102, ... and keeps the widest
covering array in curN.txt (log in loopN.log). The four products are deterministic and were rebuilt and checked
again. The extension runs stop on time, so a rebuild gives arrays of about these sizes, not the same arrays.

    cc -O3 -o grpm programs/grpm.c -lm
    python3 programs/mkact.py Z2^4 1,G 6x1,G,G -o u17_98.spec
    ./grpm 5 u17_98.spec 1 150 5.5 u17_98_s1 -r 40

The run that found the array used a binary built from an earlier copy of grpm.c (64-bit class masks were added
later, for k above 32). The copy here, with seed 1, gives the same array: u17_98_s1_98.txt has the same rows as
CA_98_5_17_2.txt. Closing depends on the seed (seed 5 stood at 28 classes uncovered after 20 s).

All five arrays were checked exactly with ca_verify, and again with a separate brute-force checker.
