# How these arrays were built

Construction: two methods.

CA(66; 4, 38, 2): the Paley matrix for q = 37 doubled (rows [0 | M] and [1 | 1-M], Colbourn 2015) is a CA(74; 4, 38, 2)
in which every row covers only a few 4-way interactions by itself. Rows were deleted one at a time, always the row with
the fewest uniquely covered interactions, and after each deletion the missing interactions were repaired by
single-cell changes at a fixed temperature (focus moves after Nurmela 2004), down to 66 rows.

CA(300; 6, 20, 2), CA(316; 6, 21, 2), CA(347; 6, 23, 2), CA(375; 6, 25, 2): cyclic arrays. Each consists of 15
generator words of length k and all k cyclic shifts of each, plus the all-0 and all-1 rows where noted. Because such
an array is unchanged by rotating its columns, it covers all 6-sets as soon as it covers one representative of each
rotation class, so the search (simulated annealing on the generator bits with exact incremental counts) works on about
C(k, 6)/k classes. For k = 21 the all-1 row of the 317-row array turned out to be redundant and was removed.

Built from: nothing but the Paley matrix (q = 37) and random starts. No array of Torres-Jimenez is an ingredient or
start, and none of the five has the fingerprint of one of his arrays.

Program: programs/ in this folder (paley.py, uniqcount.c, rep.c, cycq.c). README.md there gives the commands, seeds and
settings; programs/starts/ holds the doubled Paley array, the 67-row intermediate, the generator files and the 317-row
array for k = 21.
