#!/bin/bash
# delete one row at a time from the current best and repair (rep, T=0.7), up to 840 s CPU per step
cur=$1; n=$2; seed=$3
while true; do
  m=$((n-1)); seed=$((seed+1))
  nice ./rep $cur 1 $seed 840 0.7 o${m}_122.txt > l$m.log 2>&1
  if [ -f o${m}_122.txt ]; then echo "$(date +%T) $m done seed $seed" >> chain.txt; cur=o${m}_122.txt; n=$m; else echo "$(date +%T) $m failed seed $seed: $(tail -1 l$m.log)" >> chain.txt; break; fi
done
