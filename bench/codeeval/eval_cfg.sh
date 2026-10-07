#!/usr/bin/env bash
# usage: eval_cfg.sh CONTAINER TAG "car cfg" [think 0|1] [max_tokens] [problems.jsonl]
# Sets the runtime CAR config, generates solutions, runs the tests in a --network none container.
cd /home/isa/Experiments/glm53-flash-fit/claude-opt/codeeval
C=$1; TAG=$2; CFG=$3; TH=${4:-0}; MT=${5:-1536}; PR=${6:-hard32.jsonl}
docker exec "$C" sh -c "echo $CFG > /tmp/glm53_car"; sleep 3
echo "Coding eval: $TAG [$CFG] think=$TH on $PR" > ../STATUS.txt
t0=$(date +%s)
python3 gen.py --problems "$PR" --out "gen-$TAG.jsonl" --think "$TH" --max-tokens "$MT" > /tmp/claude_live.log 2>&1
t1=$(date +%s)
R=$(docker run --rm --network none -m 2g --cpus 2 -v "$PWD":/w:ro --entrypoint python3 \
    ghcr.io/0xsero/glm53-flash-offload@sha256:82eef823f95b89fcb14b8379d45315d3a632aaa054fb04e3418b62a3ec2ff1ff \
    /w/run_tests.py "/w/$PR" "/w/gen-$TAG.jsonl" 2>/dev/null | tail -1)
TOK=$(python3 -c "import json;r=[json.loads(l) for l in open('gen-$TAG.jsonl')];t=sum(x['completion_tokens'] or 0 for x in r);s=sum(x['s'] for x in r);print(f'tokens {t} gen_s {s:.0f} e2e_tok_s {t/max(s,1):.1f}')")
echo "[$TAG $CFG think=$TH] $R | $TOK | wall $((t1-t0))s"
