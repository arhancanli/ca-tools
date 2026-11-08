# Commands (debate 13, 2026-11-08)

Build: cc -O3 -o gcycq gcycq.c -lm ; cc -O3 -o bcyc2 bcyc2.c -lm   (gcycq.c has a portable PEXT fallback)
  ./gcycq 6 26 3 1150 0.55 x26_s3 -o 26x14,13,2,1,1 -r 60        # CA(381; 6, 26, 2), seed 3, 0 holes at 991 s
  ./bcyc2 3 28 2 0 1 1 1 55 0.7 z28a5 -a 1,5 -r 30 -q             # CA(29; 3, 56, 2), seed 1, 7 s
bcyc2 usage: bcyc2 t m c f norb nconst seed secs T outprefix [-a a1,..,ac] [-r reload] [-i genfile] [-q]
  (c blocks of m columns, f fixed columns, block i shifts at speed a_i)
Rebuild exactly from the saved generators:
  ./gcycq 6 26 3 5 0.55 x -o 26x14,13,2,1,1 -i starts/x26_s3_gen.txt
  ./bcyc2 3 28 2 0 1 1 1 5 0.7 y -a 1,5 -i starts/z28a5_gen.txt
