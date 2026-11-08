# How this array was built

Construction: a group-orbit array. Number the 16 columns by the vectors of GF(2)^4. The group Z_2^4 acts on the columns
by adding (XOR) a fixed vector to every column index. The array is the 16 images of each of 6 generator words, 96 rows.
Because the array is unchanged by the group, it covers all 5-sets as soon as it covers one representative of each group
orbit of 5-sets (273 classes), so the search (simulated annealing on the generator bits with exact incremental counts)
works on far fewer sets. The same search with the cyclic group Z_16 (the method of submissions smolen-2026-11-debate11
to -debate13) stops 3 classes short; the choice of group is what closes it. The search started from random words.

Built from: a random start only. No array of Torres-Jimenez is an ingredient or start, and the array does not have the
fingerprint of one of his arrays.

Program: programs/grpq.c (portable C). README.md there gives the command; programs/starts/b96_xor_gen.txt holds the
generators, from which grpq rebuilds the array exactly (option -i).
