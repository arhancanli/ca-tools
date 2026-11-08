# Commands (debate 14, 2026-11-08)

Build: cc -O3 -o grpq grpq.c -lm
  ./grpq 5 16 6 0 xor 3 90 2.0 b96_xor -r 30     # CA(96; 5, 16, 2), seed 3, T 2.0, 0 holes in under 90 s
Rebuild exactly from the saved generators:
  ./grpq 5 16 6 0 xor 3 5 2.0 x -i starts/b96_xor_gen.txt
usage: grpq t k m nconst group seed secs T outprefix [-r reloadsec] [-i genfile]
groups: rot (Z_k), xor (Z_2^n, k = 2^n), z4z4 and z2z8 (k = 16), dih (dihedral)
