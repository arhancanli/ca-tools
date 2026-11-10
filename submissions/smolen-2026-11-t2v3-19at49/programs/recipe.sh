#!/bin/bash
# recipe.sh - builds CA(19;2,49,3) from nothing, twice, and writes RECIPE.txt (every command, the hash of each
# program source, the hash of every input and output) and REPLAY.log. Run from the submission folder:
#     bash programs/recipe.sh
# No random numbers, no time limit, no input array. Needs cc, python3, sha256sum (or shasum -a 256).
set -e
SUB=$(cd "$(dirname "$0")/.." && pwd)
sha() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }
R="$SUB/RECIPE.txt"; L="$SUB/REPLAY.log"
{
echo "RECIPE for CA_19_2_49_3.txt, written by programs/recipe.sh"
echo "date (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "machine: $(uname -sm); compiler: $(cc --version | head -1); python: $(python3 --version)"
echo "seeds: none (exhaustive search, no random numbers); stop rule: search runs to completion, no clock"
echo "inputs: none (no input array)"
for f in orbq6.c mkspec.py s19a.txt; do echo "sha256 programs/$f $(sha "$SUB/programs/$f")"; done
} > "$R"
: > "$L"
for pass in build replay; do
  W=$(mktemp -d); cd "$W"
  run() { echo "[$pass] \$ $*" | tee -a "$R" >> "$L"; }
  run "cc -O3 -o orbq6 programs/orbq6.c";            cc -O3 -o orbq6 "$SUB/programs/orbq6.c"
  run "python3 programs/mkspec.py 19 9,3,3,3 > s19a.txt"; python3 "$SUB/programs/mkspec.py" 19 9,3,3,3 > s19a.txt
  echo "[$pass] sha256 s19a.txt $(sha s19a.txt)" | tee -a "$R" >> "$L"
  run "NOORDER=1 ./orbq6 s19a.txt 5 4 out";          NOORDER=1 ./orbq6 s19a.txt 5 4 out > run.log
  echo "----- [$pass] stdout of orbq6 -----" >> "$L"; cat run.log >> "$L"
  echo "[$pass] sha256 out_dump_19_49.txt $(sha out_dump_19_49.txt)" | tee -a "$R" >> "$L"
  cp out_dump_19_49.txt "$SUB/.recipe_$pass.txt"; cd "$SUB"; rm -rf "$W"
done
{
echo "sha256 CA_19_2_49_3.txt (submitted) $(sha "$SUB/CA_19_2_49_3.txt")"
if cmp -s "$SUB/.recipe_build.txt" "$SUB/CA_19_2_49_3.txt" && cmp -s "$SUB/.recipe_replay.txt" "$SUB/CA_19_2_49_3.txt"; then
  echo "RESULT: build and replay both IDENTICAL to the submitted file"; else echo "RESULT: MISMATCH"; fi
} | tee -a "$R" >> "$L"
rm -f "$SUB/.recipe_build.txt" "$SUB/.recipe_replay.txt"
tail -1 "$R"
