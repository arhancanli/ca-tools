# How these arrays were built

Construction: a strong array already in the table is kept fixed, and a few rows and columns are added around it by
search on the new cells only. For two of the four arrays the fixed array is a Roux doubling of a Power CT array.

CA(44; 3, 244, 2), in three steps.

1. Doubling. The table's CA(33; 3, 121, 2) (Power CT over GF(11)) is written twice side by side. Below it go the 10
   rows of a strength-2 array on 121 columns next to its complement. This is the Roux construction and gives
   CA(43; 3, 242, 2). The strength-2 array is one zero row plus 121 distinct 5-subsets of the other 9 rows.
   Program programs/roux242.py.

2. A list of candidate columns. One free row is added. A SAT solver then lists columns of length 44 that can be
   appended to the 242 columns, where the free row is allowed to cover the triples the column leaves uncovered.
   Each listed column comes with the entries it needs in the free row. Program programs/ppool.py (2868 columns in
   300 seconds; the list was not run to completion).

3. Two columns that fit together. Two listed columns are joined when their needs in the free row do not conflict
   and every triple made of one old column and the two new ones is covered. Program programs/ppair.py. The first
   such pair appeared at once.

CA(47; 3, 262, 2). The CA(43; 3, 242, 2) of step 1 is kept fixed. Four free rows and 20 free columns are added.
Since the fixed part already covers every triple of old columns, only triples that contain a new column can be
uncovered. Simulated annealing works on the new cells alone, with exact counts for those triples. Each move takes
one uncovered pattern, tries a few rows that can take it, and applies the best (after Nurmela 2004). Program
programs/ext3.c at temperature 1.8 reached 0 uncovered in under 100 seconds. Lower temperatures stall (64 uncovered
at 0.3, 17 at 0.8, 2 at 1.2 in the same time).

CA(51; 3, 486, 2). The table's CA(50; 3, 484, 2) (Power CT over GF(11)) is kept fixed. One free row and two free
columns are added and searched the same way (programs/ext3.c, temperature 1.8, 0 uncovered at 107 seconds).

CA(39; 3, 143, 2). The table's CA(33; 3, 121, 2) is kept fixed. Six free rows and 22 free columns are added and
searched the same way (programs/ext3.c, temperature 1.3, 0 uncovered at 185 seconds). With more free rows a lower
temperature works better.

All four arrays were checked exactly with ca_verify on every column triple.

Built from the table's own CA(33; 3, 121, 2) and CA(50; 3, 484, 2) only. No array of Torres-Jimenez is an ingredient
or start, and no array here has the fingerprint of one of his arrays.

To rebuild (python-sat needed for step 2):
    python3 programs/roux242.py CA_33_3_121_2.txt CA_43_3_242_2.txt
    python3 programs/ppool.py CA_43_3_242_2.txt 100000 300 > pool.txt
    python3 programs/ppair.py CA_43_3_242_2.txt pool.txt CA_44_3_244_2.txt
    cc -O3 -o ext3 programs/ext3.c -lm
    ./ext3 CA_43_3_242_2.txt 43 242 4 20 2 100 1.8 e262
    ./ext3 CA_50_3_484_2.txt 50 484 1 2 1 200 1.8 e486
    ./ext3 CA_33_3_121_2.txt 33 121 6 22 3 1500 1.3 e143
The solver's order of solutions and floating point details can differ between machines, so a rebuild may give a
different array of the same size.
