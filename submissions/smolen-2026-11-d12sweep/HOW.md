# How these arrays were built

Construction: cyclic arrays, the method of submission smolen-2026-11-debate11. Each array is a set of generator words of
length k and all k cyclic shifts of each, plus up to two constant rows, so it is unchanged when the columns are shifted
cyclically and covers all 6-sets as soon as it covers one representative of each rotation class. The search (simulated
annealing on the generator bits, exact incremental counts, focus moves after Nurmela 2004) ran on the Mac from random
starts, as part of a sweep that tried one row below the best known size at every binary strength 3 to 6 size with at
most 32 columns (programs/sweep.csv lists the sizes tried).

Built from: random starts only. No array of Torres-Jimenez is an ingredient or start, and none of the three has the
fingerprint of one of his arrays.

Program: programs/cycq.c (with a portable fallback for the PEXT instruction, so it builds on Apple silicon). README.md
there gives the commands; programs/starts/ holds the generators, from which cycq rebuilds each array exactly (option -i).
