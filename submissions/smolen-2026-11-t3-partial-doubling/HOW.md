# How this array was built

Construction: partial Roux doubling of a Power CT array, then eight more columns added by search with the base
kept fixed.

CA(41; 3, 163, 2).

1. Partial doubling (exact, no search). Start from the table's CA(33; 3, 121, 2). Write 34 of its columns a second
   time, so that each of them has a twin. A triple of columns that contains a column and its twin is not covered
   by the 33 rows, because the two always agree there. Add 8 helper rows in which each twinned column and its twin
   are complementary, and the helper entries of the twinned columns together with one more vector form a
   strength-2 family on 8 rows (one zero row plus a 4-subset of the other 7 rows; there are C(7,4) = 35 of these,
   34 for the twinned columns and one shared by all other columns). The result is CA(41; 3, 155, 2). Program
   programs/pd155.py. With b helper rows the same recipe doubles up to C(b-1, floor(b/2)-1) - 1 columns; at b = 10
   it is the full Roux doubling.

2. Eight more columns by search. The 33 rows of the 121 base columns stay fixed. The 8 helper rows, the 34 twin
   columns and 8 new columns may change. Simulated annealing with exact counts on every triple that contains a
   column beyond the base starts from the array of step 1 with 8 random columns added. Each move takes one
   uncovered pattern, tries a few rows that can take it, and applies the best (after Nurmela 2004). Program
   programs/ext3.c at temperature 1.0 reached 0 uncovered at 124 seconds.

Why this start. Growing the array one column at a time from our CA(40; 3, 146, 2) stopped at 156 columns after
hours. That array has 7 helper rows and room for only 14 twinned columns, and with 8 rows the room is 34. The
search does not find that rearrangement by itself, so the start has to have the right number of twins.

The array was checked exactly with ca_verify on all 708,561 column triples.

Built from the table's own CA(33; 3, 121, 2) only. No array of Torres-Jimenez is an ingredient or start, and the
array does not have the fingerprint of one of his arrays.

Program: programs/ in this folder (pd155.py, pad.py, ext3.c).

To rebuild (this reproduced the same array on a second run here):
    python3 programs/pd155.py CA_33_3_121_2.txt PD_41_3_155_2.txt
    python3 programs/pad.py PD_41_3_155_2.txt 41 163 5 start.txt
    cc -O3 -o ext3 programs/ext3.c -lm
    ./ext3 CA_33_3_121_2.txt 33 121 8 42 32 300 1.0 out -i start.txt
Floating point details can differ between machines, so a rebuild elsewhere may give a different array of the same size.
