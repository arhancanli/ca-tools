# How this array was built

Construction: a doubled Paley array with rows deleted, cut to 34 columns, from which three more rows are removed one
at a time, each removal repaired by simulated annealing on all cells.

CA(63; 4, 34, 2).

1. Start. The table's CA(66; 4, 38, 2) is the Paley matrix for q = 37, doubled as rows [0 | M] and [1 | 1-M]
   (Colbourn 2015) with rows deleted (submission smolen-2026-11-debate11).

2. Cut to 34 columns. Columns 19, 32, 9 and 16 are dropped. They were chosen one after another so that the three
   rows that do the least unique work are left with as little of it as possible. A row's unique work is the number
   of patterns, over all sets of four columns, that only this row covers.

3. Remove a row and repair, three times. The row with the least unique work is deleted. The array then misses some
   patterns, and simulated annealing repairs it. Every cell of every row may change. Counts on all sets of four
   columns are kept exactly. Each move takes one missing pattern and writes it into the closest of a few random
   rows (a focus move after Nurmela 2004). Program programs/fa.c.
   - 65 rows and 64 rows were each reached in seconds (temperature 0.5). The 64-row array is
     programs/CA_64_4_34_2_start.txt.
   - 63 rows needed repeated 30-minute runs at temperatures 0.50 to 0.65. Fresh runs stopped with 3 to 9 patterns
     missing. Runs that continued from the best state so far went from 5 missing to 3, then to 2
     (programs/state_63_34_2holes.txt), and one of six runs from that state reached 0 after 831 seconds.

The array was checked exactly with ca_verify on all 46,376 sets of four columns.

Built from the table's own CA(66; 4, 38, 2) only. No array of Torres-Jimenez is an ingredient or start, and the
array does not have the fingerprint of one of his arrays.

Program: programs/ in this folder (fa.c, the 64-row array and the state with two patterns missing).

To rebuild the last step:
    cc -O3 -o fa programs/fa.c -lm
    ./fa programs/state_63_34_2holes.txt 4 0.60 1800 76 out.txt -A -m 8
The run stops on a time limit, and floating point details can differ between machines, so a rebuild may need
other seeds. Five other runs from the same state ended with two patterns still missing.
