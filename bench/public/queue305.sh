#!/usr/bin/env bash
# Full benchmark pass on the 3.05 bpw build (26/16 split, RAM 13.5/4 GiB, CAR fast, reliability layer, 128k ctx).
cd $HOME/glm53-flash-fit/claude-opt
S=$PWD/STATUS.txt
IMG=ghcr.io/0xsero/glm53-flash-offload@sha256:82eef823f95b89fcb14b8379d45315d3a632aaa054fb04e3418b62a3ec2ff1ff
echo "Benchmarks (3.05 bpw): starting service" > $S
docker stop glm53-2bit-claude-final >/dev/null 2>&1
docker rm -f glm53-claude-ctx glm53-3bit-claude-final >/dev/null 2>&1
STAGE_GB=2.75 GLM_ROOT_DIR=$HOME/glm53-flash-fit GLM_STORE_FILE=glm53_flash_exl3_3.05bpw_experts.bin CARK=car_kernel_v3 \
  RAM0=13.5 RAM1=4 NV2_PY=$PWD/nv2_q.py EC_PY=$PWD/expert_cache_claude.py B0=8.5 B1=14 SERVE_PY=$PWD/serve_claude.py \
  CTXARGS="-cs 131072 -chunk_size 4096" ./launch_ctx.sh
docker rename glm53-claude-ctx glm53-3bit-claude-final
docker exec glm53-3bit-claude-final sh -c "echo 3 1 0.15 1 1 0 0.30 1.5 > /tmp/glm53_car"
python3 bench_multi.py --warm 1 --reps 2 --out res-305-final-speed.json | tail -1 > ~/bench/speed-305.txt
cd ~/bench
echo "Benchmark 1/4 (3.05): GPQA Diamond 80" > $S
python3 run_mcq2.py --data data/gpqa_diamond.json --n 80 --seed 0 --max-tokens 65536 --out gpqa-305.jsonl > gpqa-305.log 2>&1
echo "Benchmark 2/4 (3.05): MMLU-Pro 70" > $S
python3 run_mcq2.py --data data/mmlu_pro_test.json --per-cat 5 --seed 0 --max-tokens 65536 --out mmlupro-305.jsonl > mmlupro-305.log 2>&1
echo "Benchmark 3/4 (3.05): LiveCodeBench v6 60" > $S
python3 lcb_gen.py data/lcb_sel.json lcb-305.jsonl > lcb-305.log 2>&1
docker run --rm --network none -m 4g --cpus 4 -v $PWD:/w --entrypoint python3 $IMG /w/lcb_grade.py /w/data/lcb_sel.json /w/lcb-305.jsonl 2>/dev/null | tail -1 > lcb-305.score
echo "Benchmark 4/4 (3.05): AA-LCR 15" > $S
python3 aalcr_run.py --n 15 --out aalcr-305.jsonl > aalcr-305.log 2>&1
echo "Benchmarks (3.05) done" > $S
echo QUEUE305_DONE
