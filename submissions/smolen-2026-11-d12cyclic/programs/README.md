# Commands (Mac job d12_cyclic, 2026-11-08)

Build: cc -O3 -o cycq cycq.c -lm
  ./cycq 6 19 15 0 1 7200 0.55 s1 -r 30 -q    # CA(285; 6, 19, 2): writes s1_285.txt
  ./cycq 6 22 15 0 1 7200 0.55 s1 -r 30 -q    # CA(330; 6, 22, 2): writes s1_330.txt
Rebuild exactly from the saved generators:
  ./cycq 6 19 15 0 1 5 0.55 a -i starts/n19_s1_gen.txt
  ./cycq 6 22 15 0 1 5 0.55 b -i starts/n22_s1_gen.txt
