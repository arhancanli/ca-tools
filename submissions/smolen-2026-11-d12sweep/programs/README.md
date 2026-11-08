# Commands (Mac job d12_cyclic, record sweep, 2026-11-08)

Build: cc -O3 -o cycq cycq.c -lm
  ./cycq 6 21 15 0 10 900 0.55 t6k21_N315 -r 30 -q   # CA(315; 6, 21, 2), 0 holes at 666 s
  ./cycq 6 23 15 1 12 900 0.55 t6k23_N346 -r 30 -q   # CA(346; 6, 23, 2), 0 holes at 171 s
  ./cycq 6 31 14 2 12 900 0.55 t6k31_N436 -r 30 -q   # CA(436; 6, 31, 2), 0 holes at 635 s
Rebuild exactly from the saved generators:
  ./cycq 6 21 15 0 10 5 0.55 a -i starts/t6k21_N315_gen.txt
  ./cycq 6 23 15 1 12 5 0.55 b -i starts/t6k23_N346_gen.txt
  ./cycq 6 31 14 2 12 5 0.55 c -i starts/t6k31_N436_gen.txt
sweep.csv: the sizes the sweep tried (t, k, best known N then, m orbits, constant rows, N tried).
