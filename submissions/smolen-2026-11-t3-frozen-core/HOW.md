# How these arrays were built

Construction: the table's CA(33; 3, 121, 2) (Power CT over GF(11)) is kept fixed, and rows and columns are added
around it by search on the new cells only (as in submission smolen-2026-11-t3-roux-patch).

Since the fixed part already covers every triple of old columns, only triples that contain a new column can be
uncovered. Simulated annealing works on the new cells alone, with exact counts for those triples. Each move takes one
uncovered pattern, tries a few rows that can take it, and applies the best (after Nurmela 2004). Program
programs/ext3.c.

CA(38; 3, 141, 2). Five free rows and 20 free columns, random start, temperature 1.4, 0 uncovered at 1153 seconds.

CA(40; 3, 146, 2). Seven free rows and 25 free columns. The new cells start from the CA(39; 3, 143, 2) of the earlier
submission, which has the same fixed part, with one random row and three random columns added (programs/pad.py).
Temperature 1.0, 0 uncovered in 2 seconds. Growing the array one step at a time from a solved smaller one is much
faster than a random start.

Both arrays were checked exactly with ca_verify on every column triple.

Built from the table's own CA(33; 3, 121, 2) and CA(39; 3, 143, 2) only. No array of Torres-Jimenez is an ingredient
or start, and no array here has the fingerprint of one of his arrays.

To rebuild:
    cc -O3 -o ext3 programs/ext3.c -lm
    ./ext3 CA_33_3_121_2.txt 33 121 5 20 3 1700 1.4 e141
    python3 programs/pad.py CA_39_3_143_2.txt 40 146 1 start.txt
    ./ext3 CA_33_3_121_2.txt 33 121 7 25 5 240 1.0 e146 -i start.txt
Floating point details can differ between machines, so a rebuild may give a different array of the same size.
