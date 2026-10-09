#!/usr/bin/env bash
# same 3 hardest MMLU-Pro questions with the server default thinking budget (6144), as used day to day
until grep -q FINAL_DONE ~/finalcheck/FINAL_CHECK.txt; do sleep 10; done
cd ~/bench
python3 run_mcq2.py --data data/mmlu_pro_test.json --ids hard_ids.json --limit 3 --max-tokens 16384 --extra "{\"thinking_budget\": 6144}" --out final-hard3-default.jsonl > final-hard3-default.log 2>&1
echo "hard reasoning, server default (thinking budget 6144): $(tail -1 final-hard3-default.log)" >> ~/finalcheck/FINAL_CHECK.txt
echo HARD3B_DONE >> ~/finalcheck/FINAL_CHECK.txt
