# How this array was built

Construction: column large-neighbourhood search on a strength-2 ternary array at fixed N = 29. Start from the
table's own CA(28; 2, 449, 3) plus one row, extend columns at fixed N (after the CA Extender) to 582 columns, then
repeat: remove about 250 random columns, collect columns that cover all 9 pairs with every kept column, and look for a
larger mutually compatible set among them with a seeded tabu search. Each larger set adds columns. 582 -> 610.

Built from: the table's own CA(28; 2, 449, 3) (CA_28_2_449_3_4123e4fb, a generalized direct product of our own arrays).
No array of Torres-Jimenez is an ingredient or start; his CA Extender and the annealing of Avila-George, Torres-Jimenez
and Hernandez are credited as methods.

Program: programs/ in this folder. README.md there gives the commands, seeds and settings; the intermediate arrays
(520, 548 and 582 columns) are in programs/starts/.
