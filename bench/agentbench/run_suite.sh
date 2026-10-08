#!/usr/bin/env bash
# usage: run_suite.sh TAG MODEL THINKING [CONTAINER CAR_CFG]
# Runs every task with pi -p (non-interactive) in a fresh copy, then checks it in a --network none container.
cd "$(dirname "$0")"
TAG=$1; MODEL=$2; TH=$3; C=${4:-}; CFG=${5:-}
[ -n "$C" ] && [ -n "$CFG" ] && { docker exec "$C" sh -c "echo $CFG > /tmp/glm53_car"; sleep 3; }
IMG=ghcr.io/0xsero/glm53-flash-offload@sha256:82eef823f95b89fcb14b8379d45315d3a632aaa054fb04e3418b62a3ec2ff1ff
mkdir -p runs; PASS=0; N=0; OUT=runs/$TAG.txt; : > "$OUT"
for t in ${TASKS:-tasks/*/}; do
  name=$(basename "$t"); W=runs/$TAG/$name; rm -rf "$W"; mkdir -p "$W"; cp -r "$t/start/." "$W/"
  echo "agentbench $TAG: $name" > /tmp/glm53_status.txt
  t0=$(date +%s)
  ( cd "$W" && timeout 1500 "$HOME/.pi/agent/bin/pi" -p --no-session --model "$MODEL" --thinking "$TH" "$(cat "../../../$t/PROMPT.txt")" > ../$name.pi.log 2>&1 )
  t1=$(date +%s)
  cp "$t/check.py" "$W/.check.py"
  R=$(docker run --rm --network none -m 1g --cpus 1 -v "$PWD/$W":/w -w /w --entrypoint python3 "$IMG" .check.py 2>&1); ok=$([ $? -eq 0 ] && echo 1 || echo 0)
  PASS=$((PASS + ok)); N=$((N + 1))
  echo "$TAG $name pass=$ok $((t1 - t0))s | $(echo "$R" | tail -1 | cut -c1-200)" | tee -a "$OUT"
done
echo "[$TAG] $PASS/$N tasks passed" | tee -a "$OUT"
