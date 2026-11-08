#!/bin/bash
# chain.sh START N KMAX SEED HOURS TAG : one single-threaded CAEX-style chain at fixed N.
# Runs caex in 30-minute legs; each leg restarts (new seed) from the widest covering array so far.
# Best array so far: db/TAG_best.txt ; every new width also saved as db/TAG_N_k.txt
set -u
START=$1; N=$2; KMAX=$3; SEED=$4; HOURS=$5; TAG=$6
mkdir -p db logs
cur=$START; best=0
end=$(( $(date +%s) + ${HOURS%.*} * 3600 ))
leg=0
export T0=${T0:-0.4} TSTALL=${TSTALL:-0.4} P1=${P1:-0.3} R1=${R1:-4} LMUL=${LMUL:-4} COLSEC=${COLSEC:-600}
while [ $(date +%s) -lt $end ]; do
  ./caex $cur $N $KMAX $((SEED + 1000*leg)) 1800 db/${TAG}_L$leg > logs/${TAG}_L$leg.res 2> logs/${TAG}_L$leg.log
  k=$(awk '{print $2}' logs/${TAG}_L$leg.res)
  if [ -n "$k" ] && [ "$k" -gt "$best" ]; then best=$k; cur=db/${TAG}_L${leg}_${N}_${k}.txt; cp $cur db/${TAG}_best.txt; fi
  echo "leg $leg k=$k best=$best" >> logs/${TAG}.chain
  leg=$((leg+1))
done
