#!/bin/bash
# repeated short ext2 runs with fresh seeds from the last covering array (one process at a time)
cur=$1; end=$((SECONDS+$2)); s=100
while [ $SECONDS -lt $end ]; do
  s=$((s+1)); k=$(head -1 $cur | wc -w)
  SAT=0.3 NEWCOLTRY=$3 nice -n 19 ./ext2 $4 $5 3 $s $6 lp$4 $cur $k > lp.log 2>&1
  k2=$(head -1 lp$4_$4_last.txt | wc -w)
  if [ "$k2" -gt "$k" ]; then cp lp$4_$4_last.txt cur$4.txt; cur=cur$4.txt; fi
  echo "seed $s k $k -> $k2" >> loop$4.log
done
