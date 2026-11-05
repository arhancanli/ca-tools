# How these arrays were built

Construction: four arrays from debate 9 of the ca-tools project (2026-11-05). CA(238; 5, 122, 2): Paley-type doubling
(Colbourn 2015) of the Paley matrix over GF(121), then one row deleted at a time, each time the row with the fewest
unique 5-way interactions (two random rows first), each followed by a full repair by single-cell flips.
CA(92; 4, 90, 2) and CA(108; 4, 114, 2): a Paley array with rows removed (Paley 89 minus one row; Paley 113 after
NCK row elimination to 108 rows) plus spare rows where any, one new column filled by the ExtendCA greedy rule of
Torres-Jimenez and Avila-George (SBSTT), then fixed-temperature simulated annealing. CA(25; 2, 220, 3): generalized
direct product of our own arrays, column extension at fixed N (after the CA Extender), then a new column large-neighbourhood
search: remove many columns, collect columns compatible with the rest, and find a larger mutually compatible set.

Built from: CA(238; 5, 122, 2) from nothing (the Paley matrix over GF(121), via the CAs package of Ulrike Groemping).
CA(92; 4, 90, 2) from the Paley matrix of order 89. CA(108; 4, 114, 2) from our own CA(108; 4, 113, 2) (row elimination
of the Paley array for q = 113, tools/own_arrays). CA(25; 2, 220, 3) from our own CA(12; 2, 7, 3) (built from the Bose
OA(9; 2, 4, 3)) and the table's own CA(15; 2, 20, 3) (CA_15_2_20_3_fd13075b). No array of Torres-Jimenez is an
ingredient or start; his methods (SBSTT, CA Extender, ESA annealing) are credited as methods.

Program: programs/ in this folder (README.md there gives every command, seed and setting, and the start files in
programs/starts/). R script paley121.R; C programs rep.c, uniqcount.c, bsa4x.c, pool.c, kcl.c, caex.c; Python lns3.py;
tools/own_arrays/prod2.py and nck.c in this repository.
