# Commands (debate 12, 2026-11-08)

Build: gcc -O3 -o bcyc bcyc.c -lm ; gcc -O3 -o gcycq gcycq.c -lm

  ./bcyc 3 10 3 2 3 1 100 0.7 k30_z10_23 -r 25 -q          # CA(23; 3, 30, 2), seed 1, under 100 s
  ./bcyc 3 29 2 1 1 1 120 0.7 k58_z29_30 -r 30 -q          # CA(30; 3, 58, 2), seed 1
  ./gcycq 6 24 1 170 0.55 r24_s1 -o 24x14,12,8,1 -r 30 -q  # CA(357; 6, 24, 2), seed 1, under 170 s

bcyc usage: bcyc t m c norb nconst seed secs T outprefix [-r reload] [-i genfile] [-q]
gcycq usage: gcycq t k seed secs T outprefix -o SPEC [-c] [-r reload] [-i genfile] [-q]  (SPEC lists orbit periods)
Each writes OUTPREFIX_gen.txt and, at 0 holes, OUTPREFIX_N.txt. Rebuild exactly from the saved generators:
  ./bcyc 3 10 3 2 3 1 5 0.7 x -i starts/k30_z10_23_gen.txt
  ./bcyc 3 29 2 1 1 1 5 0.7 y -i starts/k58_z29_30_gen.txt
  ./gcycq 6 24 1 5 0.55 z -o 24x14,12,8,1 -i starts/r24_s1_gen.txt
gcycq.c has a portable fallback for the PEXT instruction (Apple silicon).
