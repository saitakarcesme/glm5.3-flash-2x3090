#!/usr/bin/env bash
# One recorded pi session on the LLMRig desktop.
# usage: run_session.sh LABEL UPSTREAM PROXY_PORT PI_MODEL WORKSPACE_NUM [TIMEOUT_MIN]
#   e.g. run_session.sh GLM http://127.0.0.1:30270 18100 cmp-glm/glm-5.3-flash 8
set -uo pipefail
LABEL=$1; UP=$2; PP=$3; MODEL=$4; WS=$5; TMO=${6:-75}
BASE=$HOME/pi-compare; W=$HOME/pi-ws/$LABEL; V=$HOME/Videos/glm-compare; mkdir -p "$V"
export XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-1 HYPRLAND_INSTANCE_SIGNATURE=$(ls /run/user/1000/hypr/ | head -1)
LOG=$BASE/$LABEL-requests.jsonl; : > "$LOG"
python3 "$BASE/tokproxy.py" --listen "$PP" --upstream "$UP" --log "$LOG" --label "$LABEL" > "$BASE/$LABEL-proxy.log" 2>&1 &
PROXY=$!
sleep 1
hyprctl dispatch "hl.dsp.focus({workspace = $WS})" >/dev/null
sleep 1
VID=$V/$(date +%Y%m%d-%H%M)-pi-$LABEL.mp4
gpu-screen-recorder -w HDMI-A-1 -f 30 -encoder cpu -k h264 -o "$VID" > "$BASE/$LABEL-rec.log" 2>&1 &
REC=$!
sleep 2
# right: live tok/s + GPU panel; left: the pi session
setsid foot --title="tok/s — $LABEL" bash -c "printf '\e[1;33m$LABEL — live tok/s (proxy log)\e[0m\n'; tail -n +1 -f '$BASE/$LABEL-proxy.log' & while true; do sleep 15; nvidia-smi --query-gpu=index,utilization.gpu,memory.used,power.draw --format=csv,noheader | sed 's/^/  GPU /'; done" >/dev/null 2>&1 < /dev/null &
sleep 1
setsid foot --title="pi — $LABEL" --working-directory="$W" bash -c "$HOME/.pi/agent/bin/pi --model '$MODEL' --thinking high --name 'website-$LABEL' \"\$(cat '$BASE/prompt.txt')\"; exec bash" >/dev/null 2>&1 < /dev/null &
T0=$(date +%s)
echo "$LABEL: session started at $(date +%T), recording $VID"
# done = nothing in flight and no new request for 90 s (agent stopped: final answer, truncation or error); hard timeout
echo 0 > "$LOG.inflight"
while true; do
  sleep 10
  NOW=$(date +%s)
  [ $((NOW - T0)) -gt $((TMO * 60)) ] && { echo "$LABEL: timeout"; break; }
  [ -s "$LOG" ] || continue
  INF=$(cat "$LOG.inflight" 2>/dev/null || echo 1)
  AGE=$(( NOW - $(stat -c %Y "$LOG") ))
  [ "$INF" = "0" ] && [ "$AGE" -ge 90 ] && { echo "$LABEL: agent idle (last finish: $(tail -1 "$LOG" | python3 -c 'import json,sys; print(json.loads(sys.stdin.read()).get("finish"))'))"; break; }
done
sleep 5
kill -INT $REC; wait $REC 2>/dev/null
kill $PROXY 2>/dev/null
python3 - "$LOG" "$LABEL" "$(( $(date +%s) - T0 ))" <<'EOF' | tee "$BASE/$LABEL-summary.json"
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
comp = sum(r["completion_tokens"] or 0 for r in rows); dec = sum(r["decode_s"] for r in rows)
print(json.dumps({"label": sys.argv[2], "wall_s": int(sys.argv[3]), "requests": len(rows), "completion_tokens": comp,
                  "prompt_tokens_total": sum(r["prompt_tokens"] or 0 for r in rows), "decode_s": round(dec, 1),
                  "avg_decode_tok_s": round(comp / dec, 2) if dec else 0, "median_ttft_s": sorted(r["ttft_s"] for r in rows)[len(rows) // 2] if rows else None}))
EOF
echo "$LABEL: video $VID ($(du -h "$VID" | cut -f1))"
