# How this array was built

Construction: an array that is invariant under a permutation of its rows, with five column orbits of length 9 and
four further columns, found by exhaustive search.

CA(19; 2, 49, 3).

Let tau be the permutation of the 19 rows with one cycle of length 9 (rows 0 to 8), three cycles of length 3 (rows
9 to 11, 12 to 14, 15 to 17) and one fixed row (row 18). Applying tau to a column gives another column. A column
whose 9 images are pairwise qualitatively independent (every pair of them shows all 9 symbol pairs) is kept, one
per orbit and up to renaming of symbols. There are 423,360 such orbits among 189,751,059 candidate columns.

Two orbits are joined when every column of one is qualitatively independent of every column of the other. Five
mutually joined orbits are a covering array with 19 rows and 45 columns. The program lists all such sets of five
up to the normaliser of tau (rotations of each cycle, exchanges of the cycles of length 3, and the maps i to j*i
on the cycles). No set of six exists. In the order used here there are 7936 sets of five.

For each set of five the program lists every further column that is qualitatively independent of all 45 columns,
and finds the largest set of such columns that are independent of one another. 7888 of the sets take exactly 3
further columns and 48 take exactly 4. None takes 5. The array here is the first set that takes 4, which gives
45 + 4 = 49 columns. So this row permutation, with five full orbits, gives 49 columns and not 50.

The search is exhaustive and uses no random numbers, so a rebuild gives the same array. The count of sets of five
depends on the order in which orbits are processed. The outcome does not.

The array was checked exactly with ca_verify on all 1176 pairs of columns, and with a separate brute force check.

Built from: nothing. There is no input array. No array of Torres-Jimenez is an ingredient or start, and the array
does not have the fingerprint of one of his arrays.

Program: programs/ in this folder (orbq6.c, mkspec.py, and the group file s19a.txt that mkspec.py writes). The
program was written by an AI model for this project.

To rebuild:
    cc -O3 -o orbq6 programs/orbq6.c
    python3 programs/mkspec.py 19 9,3,3,3 > s19a.txt
    NOORDER=1 ./orbq6 s19a.txt 5 4 out
    cmp out_dump_19_49.txt CA_19_2_49_3.txt
The run takes about 5 minutes on one core and under 1 GB of memory.
