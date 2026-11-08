# How these arrays were built

Construction: arrays that are unchanged when the columns are shifted cyclically, searched on the rotation classes.

CA(23; 3, 30, 2) and CA(30; 3, 58, 2): block-cyclic. The columns form c blocks of m columns, and Z_m shifts every block
at once. The array is the union of full orbits of a few generator words plus a few rows that are constant on each
block. For 23@30: m = 10, c = 3, two orbits (20 rows) and three block-constant rows. For 30@58: m = 29, c = 2, one orbit
(29 rows) and the row 0^29 1^29.

CA(357; 6, 24, 2): cyclic with orbits of mixed length under Z_24: fourteen full orbits of 24 rows, one word of period 12
(its orbit has 12 rows), one of period 8 (8 rows), and the all-1 row.

Because each array is unchanged by the group, it covers all t-sets as soon as it covers one representative of each
rotation class, so the search (simulated annealing on the generator bits, exact incremental counts, focus moves after
Nurmela 2004) works on far fewer sets. Every search started from random words.

Built from: random starts only. No array of Torres-Jimenez is an ingredient or start, and none of the three has the
fingerprint of one of his arrays.

Program: programs/ in this folder (bcyc.c, gcycq.c). README.md there gives the commands and seeds; programs/starts/
holds the generator files, from which each program rebuilds its array exactly (option -i).
