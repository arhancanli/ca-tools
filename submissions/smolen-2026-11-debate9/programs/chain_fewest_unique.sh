#!/bin/bash
# delete the row with the fewest unique 5-way interactions, repair with rep (T=0.7), repeat
cur=$1; n=$2; seed=$3
while true; do
  m=$((n-1)); seed=$((seed+1))
  r=$(nice ./uniqcount $cur 5 1 | grep -v '^#' | sort -n -k2 | head -1 | cut -d' ' -f1)
  nice ./rep $cur 1 $seed 840 0.7 o${m}_122.txt $r > l$m.log 2>&1
  if [ -f o${m}_122.txt ]; then echo "$(date +%T) $m done (row $r) seed $seed" >> chain.txt; cur=o${m}_122.txt; n=$m; else echo "$(date +%T) $m failed (row $r) seed $seed: $(tail -1 l$m.log)" >> chain.txt; break; fi
done
