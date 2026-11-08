# Commands (debate 11, 2026-11-08)

Build: gcc -O3 -o rep rep.c -lm ; gcc -O3 -o uniqcount uniqcount.c ; gcc -O3 -o cycq cycq.c -lm

CA(66; 4, 38, 2):
  python3 paley.py 37 double > pd37.txt                      # CA(74; 4, 38, 2) = starts/pd37.txt
  NMIN=66 SAVEBEST=1 ./rep pd37.txt 4 420 1 0.5 d37          # 74 -> 67 rows in 82 s (starts/d37_67.txt)
  NMIN=66 SAVEBEST=1 ./rep d37_67.txt 4 480 11 0.6 f66       # 67 -> 66 rows, 0 holes at 304 s: f66_66.txt
  rep deletes the row with the fewest uniquely covered 4-sets (as uniqcount reports) and repairs by focus moves.

Cyclic t = 6 arrays (cycq t k m nconst seed secs T outprefix -r reload):
  ./cycq 6 20 15 0 4 55 0.55 q6k20_s4 -r 25     # 300 rows, 0 holes at 27 s
  ./cycq 6 21 15 2 1 50 0.55 q6k21_c2 -r 25     # 317 rows, 0 holes at 48 s; drop the all-1 row -> 316
  ./cycq 6 23 15 2 3 100 0.55 q6k23_s3 -r 25    # 347 rows, 0 holes at 75 s
  ./cycq 6 25 15 0 1 60 0.6 q6k25_s1 -r 30      # 375 rows, 0 holes at 14 s
  Each writes OUTPREFIX_gen.txt (the generators, copies in starts/) and OUTPREFIX_N.txt (the array).
