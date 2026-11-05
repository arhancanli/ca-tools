# Programs for submission smolen-2026-11-debate9 (own code, CC BY 4.0 like the arrays; C99, Python 3, R)
Build: gcc -O3 -o rep rep.c -lm; gcc -O3 -o uniqcount uniqcount.c -lm; gcc -O3 -march=native -o bsa4x bsa4x.c -lm;
gcc -O3 -o pool pool.c; gcc -O3 -o kcl kcl.c; gcc -O3 -o caex caex.c -lm. Check every result with ca_verify.

## CA(238; 5, 122, 2)
1. Rscript paley121.R -> p121.txt = CA(242; 5, 122, 2).
2. Delete one row and repair by single-cell flips (rep FILE ndel seed seconds T OUT [rows to delete]):
   242->241: ./rep p121.txt 1 2 840 0.7 o241_122.txt (random row, seed 2)
   241->240: ./rep o241_122.txt 1 3 840 0.7 o240_122.txt (random row, seed 3)
   240->239: row = fewest unique 5-way interactions (./uniqcount o240_122.txt 5 1, smallest count: row 236)
             ./rep o240_122.txt 1 21 840 0.7 o239_122.txt 236
   239->238: same rule (row 203), ./rep o239_122.txt 1 22 840 0.7 o238_122.txt 203
   chain_rows.sh and chain_fewest_unique.sh are the loops used. The repair stops at the first hole-free state, so
   the result depends only on the seed (single-threaded).
## CA(92; 4, 90, 2)
starts/CA_88_4_89_2.txt = paley_mat(89) without its first row. ./bsa4x CA_88_4_89_2.txt 92 90 840 3 r92_90c fixT=0.8
m1best=1 rep=60 x=1 pF=0.3 fr=4: 4 random rows (seed 3), column 90 by the ExtendCA greedy rule, fixed-temperature
annealing; 283 missing tuples to 0. Annealing stops at 0; result depends on seed and on the time cap only if not reached.
## CA(108; 4, 114, 2)
starts/CA_108_4_113_2.txt = row elimination (tools/own_arrays/nck.c) of CAs::paleyCA(4,113), an intermediate of the
chain that gave the table's own CA(107; 4, 113, 2). ./bsa4x CA_108_4_113_2.txt 108 114 400 1 r108_114 fixT=0.8 m1best=1
rep=30 x=1 (greedy column 114; 138 -> 1), then ./bsa4x r108_114_1h.txt 108 114 700 2 r108_114b fixT=0.7 m1best=1 rep=60 (1 -> 0).
## CA(25; 2, 220, 3)
Lineage: starts/CA_12_2_7_3.txt (caex.c from Bose OA(9;2,4,3)) x the table's own CA(15;2,20,3) (CA_15_2_20_3_fd13075b)
by the generalized direct product tools/own_arrays/prod2.py -> starts/CA_25_2_140_3_product.txt; caex column extension
-> starts/CA_25_2_199_3.txt (cloud) -> starts/CA_25_2_209_3.txt (Mac, caex_chain.sh, leg 3); then column LNS:
SIDE=1 python3 lns3.py CA_25_2_209_3.txt 25 80 20 25 36000 L25 1 (209 -> 216 -> 218), then with the seeded clique
stage SEEDFIRST=95 SIDE=1 python3 lns3.py <218 file> 25 95 30 30 36000 R25 <seed> (-> 219 -> 220).
Each LNS step: delete R random columns, pool collects columns compatible (all 9 pairs) with every kept column, kcl finds
R+1, R+2, ... mutually compatible pool columns (tabu clique search); a larger set is a gain. Time limits make reruns differ.
Note: CA(12; 2, 7, 3) has the same fingerprint as an array of Torres-Jimenez (CAEX data ca12.2.3.7); six fresh caex
seeds from OA9 all give it, so it is essentially the unique array of that size. It was built here, not copied.
