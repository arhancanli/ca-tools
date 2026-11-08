# How these arrays were built

Construction: arrays that are unchanged when the columns are shifted by a cyclic group, searched on the rotation
classes (as in submissions smolen-2026-11-debate11 and smolen-2026-11-debate12).

CA(381; 6, 26, 2): Z_26 acts on the 26 columns by rotation. The array is 14 full orbits (26 rows each), one word of
period 13 (13 rows), one of period 2 (2 rows), and the all-0 and all-1 rows.

CA(29; 3, 56, 2): the columns form two blocks of 28. One step of Z_28 shifts the first block by 1 and the second block by
5 (a twisted action). The array is the 28 images of one word of length 56, plus the all-1 row. With both blocks shifting
at the same speed this shape stops at one uncovered triple; the different speed removes it.

Because each array is unchanged by its group, it covers all t-sets as soon as it covers one representative of each
class, so the search (simulated annealing on the generator bits, exact incremental counts, focus moves after Nurmela
2004) works on far fewer sets. Every search started from random words.

Built from: random starts only. No array of Torres-Jimenez is an ingredient or start, and neither array has the
fingerprint of one of his arrays.

Program: programs/ in this folder (gcycq.c, bcyc2.c). README.md there gives the commands; programs/starts/ holds the
generators, from which each program rebuilds its array exactly (option -i).
