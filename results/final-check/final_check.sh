#!/usr/bin/env bash
# Final release check on the faithful profile: speed, tools + prompt cache, hard reasoning (3 MMLU-Pro), coding (32 executed)
set -u
F=~/finalcheck; O=$F/FINAL_CHECK.txt; C=glm53-2bit-claude-final; CAR="2 0 0.20 1 1 0 1.01 1.5"
docker exec $C sh -c "echo $CAR > /tmp/glm53_car"; sleep 3
echo "# final check $(date)" > $O
cd /home/isa/Experiments/glm53-flash-fit/claude-opt
echo "speed: $(python3 bench_multi.py --warm 1 --reps 2 --out res-final-release-speed.json | tail -1)" >> $O
echo "tools+cache: $(python3 $F/tools_cache.py 2>&1 | tail -1)" >> $O
cd ~/bench
python3 run_mcq2.py --data data/mmlu_pro_test.json --ids hard_ids.json --limit 3 --max-tokens 16384 --out final-hard3.jsonl > final-hard3.log 2>&1
echo "hard reasoning (3 hardest MMLU-Pro, 16k cap): $(tail -1 final-hard3.log)" >> $O
cd $F/codeeval
echo "coding (32 executed problems, no thinking): $(./eval_cfg.sh $C final-faithful "$CAR" 0 1536 hard32.jsonl | tail -1)" >> $O
echo "guards: $(docker logs --since 2h $C 2>&1 | grep -c -- '-- guard')" >> $O
echo FINAL_DONE >> $O
