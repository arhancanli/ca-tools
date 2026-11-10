# How this array was built

Construction: Roux doubling of a Power CT array, with the doubling rows searched again together with four added
columns while the doubled part stays fixed.

CA(42; 3, 180, 2).

1. The table's CA(32; 3, 88, 2) (Power CT over GF(11)) is written twice side by side (32 rows, 176 columns). Below it
   go the 10 rows of a strength-2 array on 88 columns next to its complement. This is the Roux construction and gives
   CA(42; 3, 176, 2). Program programs/roux176.py.

2. That array cannot take one more column as it stands (an exact SAT search for a 177th column has no solution). But
   the 10 bottom rows have room to spare, since 10 rows can carry a strength-2 array on up to 126 columns and only 88
   are used.

3. The top 32 rows of the 176 columns are kept fixed. The 10 bottom rows (all 180 columns) and the 4 new columns (all
   42 rows) are free. Simulated annealing on the free cells, with exact counts on all column triples, starts from the
   Roux array with random new columns. Each move takes one uncovered pattern, tries a few rows that can take it, and
   applies the best (after Nurmela 2004). Program programs/ext3g.c at temperature 1.0 reached 0 uncovered at 127
   seconds. At temperature 0.5 the same run stopped at 18 uncovered.

The array was checked exactly with ca_verify on all 955,860 column triples.

Built from the table's own CA(32; 3, 88, 2) only. No array of Torres-Jimenez is an ingredient or start, and the array
does not have the fingerprint of one of his arrays.

Program: programs/ in this folder (roux176.py, pad.py, ext3g.c).

To rebuild:
    python3 programs/roux176.py CA_32_3_88_2.txt top.txt roux.txt
    python3 programs/pad.py roux.txt 42 180 1 start.txt
    cc -O3 -o ext3g programs/ext3g.c -lm
    ./ext3g top.txt 32 176 10 4 1 150 1.0 g180 -i start.txt -k 2
Floating point details can differ between machines, so a rebuild may give a different array of the same size.
