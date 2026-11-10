#!/bin/bash
# recipe32.sh: build CA(32;2,1427,3) under DECISIONS B7 (recipe rule). This script runs every command and writes
# RECIPE.log itself (commands, sha256 of every input and output, program hashes).
# The extension is stopped on a COUNT (the array saved after the 272nd added column, 1427 columns), not on a
# clock; the seconds argument of ext2t is only an abort limit.
cd "$(dirname "$0")"
sha(){ if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -c1-64; else shasum -a 256 "$1" | cut -c1-64; fi; }
LOG=RECIPE.log; : > $LOG
cc -O3 -o ext2t ext2t.c -lm || exit 1
echo "recipe32 start on $(uname -sm); ext2t.c $(sha ext2t.c); pprod.py $(sha pprod.py)" >> $LOG
echo "inputs: CA_15_2_20_3.txt $(sha CA_15_2_20_3.txt); CA_20_2_61_3_ingredient.txt $(sha CA_20_2_61_3_ingredient.txt)" >> $LOG
C1="python3 pprod.py CA_15_2_20_3.txt 0 3 CA_20_2_61_3_ingredient.txt 0 3 p32_1155.txt"
$C1 > step1.out 2>&1; echo "step1 | $C1 | out p32_1155.txt $(sha p32_1155.txt) | $(tail -n 1 step1.out)" >> $LOG
mkdir -p out
C2="./ext2t p32_1155.txt 32 1155 0 0 13 1000000 0.7 out/t32f -chain 600 -ntry 200 -kick 200000"
# The program adds one column at a time and saves the array after each. The recipe takes the array saved at 1427
# columns (the 272nd added column) and then stops the program. The -chain value must stay 600: it changes the path.
$C2 > step2.out 2>&1 & PID=$!
while [ ! -f out/t32f_32_1427.txt ] && kill -0 $PID 2>/dev/null; do sleep 5; done; sleep 3; kill $PID 2>/dev/null; wait $PID 2>/dev/null
echo "step2 | $C2 | stopped after the array at 1427 columns was saved | in p32_1155.txt $(sha p32_1155.txt) | out out/t32f_32_1427.txt $(sha out/t32f_32_1427.txt) | $(grep '_1427.txt' step2.out | tail -n 1)" >> $LOG
cp out/t32f_32_1427.txt CA_32_2_1427_3.txt; echo "DONE CA_32_2_1427_3.txt sha256 $(sha CA_32_2_1427_3.txt)" >> $LOG
