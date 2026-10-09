#!/usr/bin/env bash
# One prompt -> Claude Code (headless) on our GLM-5.3-Flash in a fresh folder; records time, tokens, context, speed.
# usage: run_site.sh <name> <prompt-file>
set -u
NAME=$1; PROMPT=$2; B=~/sitebench; D=$B/$NAME; R=$B/$NAME.run
mkdir -p "$D" "$R"; cp "$PROMPT" "$R/prompt.txt"
[ -z "$(ls -A "$D")" ] || { echo "folder $D not empty"; exit 1; }
K=$(cat ~/tb/.litellm_key)
T0=$(date -u +%Y-%m-%dT%H:%M:%SZ); S0=$(date +%s); echo "$T0" > "$R/start"
cd "$D"
ANTHROPIC_BASE_URL=http://172.17.0.1:4000 ANTHROPIC_AUTH_TOKEN=$K ANTHROPIC_API_KEY= \
ANTHROPIC_MODEL=glm-5.3-flash ANTHROPIC_SMALL_FAST_MODEL=glm-5.3-flash ANTHROPIC_DEFAULT_HAIKU_MODEL=glm-5.3-flash \
ANTHROPIC_DEFAULT_SONNET_MODEL=glm-5.3-flash ANTHROPIC_DEFAULT_OPUS_MODEL=glm-5.3-flash \
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 DISABLE_TELEMETRY=1 DISABLE_AUTOUPDATER=1 \
CLAUDE_CODE_AUTO_COMPACT_WINDOW=131072 API_TIMEOUT_MS=3600000 \
  claude -p "$(cat "$R/prompt.txt")" --model glm-5.3-flash --dangerously-skip-permissions \
         --output-format stream-json --verbose < /dev/null > "$R/session.jsonl" 2> "$R/claude.err"
echo "exit $?" > "$R/exit"; S1=$(date +%s)
docker logs --since "$T0" glm53-2bit-claude-final 2>&1 | grep -- "-- req \|-- guard" > "$R/server.log"
python3 ~/sitebench/report.py "$R" $((S1 - S0)) | tee "$R/REPORT.md"
echo SITE_DONE >> "$R/exit"
