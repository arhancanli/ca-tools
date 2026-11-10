# How this array was built

Construction: a profile product of two of our arrays, followed by column extension by simulated annealing. This
is the route of submission smolen-2026-11-t2v3-32rows, run again as one seeded run with a complete recipe, and it
replaces that submission's array.

CA(32; 2, 1427, 3).

1. Profile product (the method of Colbourn and Torres-Jimenez 2013, "Profiles of covering arrays of strength two",
   Thm 4.2 / Cor 4.5; no array of theirs is used). A is the table's CA(15; 2, 20, 3), rows 0 and 3, which agree in 5
   columns. B is our CA(20; 2, 61, 3), built on 2026-11-09 and included here as
   programs/CA_20_2_61_3_ingredient.txt, rows 0 and 3, which agree in 13 columns. The product has 15 + 20 - 3 = 32
   rows and 20 x 61 - 5 x 13 = 1155 columns. Program programs/pprod.py.

2. Column extension at 32 rows. Program programs/ext2t.c adds one column at a time and saves the array after each
   added column. Each new column starts as the best of 200 random columns. Simulated annealing with exact counts
   on all column pairs then repairs it, and only the new column may change (temperature 0.7, seed 13). A column
   that stays stuck for 200000 moves is thrown away and drawn again. The array saved after the 272nd added column
   has 1427 columns and is the array of this submission. It was saved at move 46,965,623 of the run. The first
   1155 columns are exactly the product.

The array was checked exactly with ca_verify on all 1,017,451 column pairs.

Replication. The run is deterministic. Three separate executions, one on an Apple Silicon Mac and two on Linux
x86_64, gave the identical file (sha256 901be6e03091c1795f1383c1aa6e9ba5da971a6a11d34e025ceb4211f091c0e2). The
record is programs/REPLAY.md, and programs/RECIPE.log is the log written by the recipe script itself, with the
sha256 of every input and output.

Built from the table's CA(15; 2, 20, 3) and our CA(20; 2, 61, 3) only. No array of Torres-Jimenez is an ingredient
or start, and neither the ingredients nor the result has the fingerprint of one of his arrays.

Program: programs/ in this folder (recipe32.sh, pprod.py, ext2t.c, and the two ingredient arrays).

To rebuild:
    cd programs && bash recipe32.sh
which runs
    python3 pprod.py CA_15_2_20_3.txt 0 3 CA_20_2_61_3_ingredient.txt 0 3 p32_1155.txt
    cc -O3 -o ext2t ext2t.c -lm
    ./ext2t p32_1155.txt 32 1155 0 0 13 1000000 0.7 out/t32f -chain 600 -ntry 200 -kick 200000
and stops the last command once out/t32f_32_1427.txt has been saved.
