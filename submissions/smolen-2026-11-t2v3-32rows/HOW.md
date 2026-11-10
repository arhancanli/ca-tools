# How this array was built

Construction: a profile product of two of our arrays, followed by column extension by simulated annealing (the
same route as submission smolen-2026-11-d16-products, with a new ingredient).

CA(32; 2, 1390, 3).

1. Profile product (the method of Colbourn and Torres-Jimenez 2013, "Profiles of covering arrays of strength two",
   Thm 4.2 / Cor 4.5; no array of theirs is used). A is the table's CA(15; 2, 20, 3), rows 0 and 3, which agree in 5
   columns. B is our CA(20; 2, 61, 3), built on 2026-11-09 and included here as
   programs/CA_20_2_61_3_ingredient.txt, rows 0 and 3, which agree in 13 columns. The product has 15 + 20 - 3 = 32
   rows and 20 x 61 - 5 x 13 = 1155 columns. Program programs/pprod.py.

2. Column extension at 32 rows. Program programs/ext2t.c adds one column at a time. Each new column starts as the
   best of 100 or 200 random columns. Simulated annealing with exact counts on all column pairs then repairs it,
   and only the new column and the one merged row of the product may change (temperature 0.7). A column that stays
   stuck for 200000 moves is thrown away and drawn again. Three runs took the array from 1155 to 1242, to 1322 and
   to 1390 columns, in about two minutes of computing in all. The merged row ended unchanged, so the first 1155
   columns are exactly the product.

The run was stopped while it was still adding columns.

The array was checked exactly with ca_verify on all 965,355 column pairs.

Built from the table's CA(15; 2, 20, 3) and our CA(20; 2, 61, 3) only. No array of Torres-Jimenez is an ingredient
or start, and neither the ingredient nor the result has the fingerprint of one of his arrays.

Program: programs/ in this folder (pprod.py, ext2t.c, and the ingredient array).

To rebuild:
    python3 programs/pprod.py CA_15_2_20_3_fd13075b.txt 0 3 programs/CA_20_2_61_3_ingredient.txt 0 3 p32_1155.txt
    cc -O3 -o ext2t programs/ext2t.c -lm
    ./ext2t p32_1155.txt 32 1155 0 235 1 600 0.7 out -chain 400 -frl 1 -ntry 200 -kick 200000
Only the command of the middle run was recorded with its seed (it is in claims.csv), so a rebuild gives a
different array of about the same width.
