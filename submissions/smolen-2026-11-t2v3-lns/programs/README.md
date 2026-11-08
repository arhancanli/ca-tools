# Programs for smolen-2026-11-t2v3-lns (own code, CC BY 4.0; C99 and Python 3)
Build: gcc -O3 -o pool pool.c; gcc -O3 -o kcl kcl.c; gcc -O3 -o caex caex.c -lm. Check every result with ca_verify.
1. CA(28; 2, 449, 3) from the table (CA_28_2_449_3_4123e4fb) plus one random row -> caex chain at N = 29
   (caex_chain.sh START 29 KMAX SEED HOURS TAG): 520 columns (starts/CA_29_2_520_3.txt), then 548
   (starts/CA_29_2_548_3.txt), then on the Mac round 2 chain (seed 209, 30-minute legs) 582 (starts/CA_29_2_582_3.txt).
2. Column LNS from 582: SEEDFIRST=250 SIDE=1 python3 lns3.py CA_29_2_582_3.txt 29 250 40 40 36000 m29 2
   (pool and kcl in the same folder). Gains were written as m29_29_<k>.txt; 610 was reached after about 6 hours on one core.
   The search has time limits, so a rerun gives a different path; the array file is the record.
