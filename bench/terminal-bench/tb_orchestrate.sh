#!/usr/bin/env bash
# Unattended Terminal-Bench pipeline (runs on the rig):
#  1. wait for the hard-8 validation, pick the routing setting by rule: the faster setting (m2-30) only if it is at least
#     as accurate with no more unanswered questions than m2-20, else m2-20
#  2. wait for the Claude Code smoke test; use claude-code if it ran the agent without a harness error, else terminus-2
#  3. run a 20-task stratified Terminal-Bench 2.1 subset (1 easy, 12 medium, 7 hard; seed 0), timeouts x4
#  4. write ~/tb/RESULT.md with original vs ours + speed
set -u
cd ~/tb
S=$HOME/glm53-flash-fit/claude-opt/STATUS.txt
C=glm53-2bit-claude-final
LOG=~/tb/orchestrate.log
say() { echo "$(date +%T) $*" | tee -a $LOG; echo "TB pipeline: $*" > $S; }

say "waiting for hard-8 validation"
until grep -q HARD8_DONE ~/bench/m2_hard8.txt 2>/dev/null; do sleep 60; done
pick=$(python3 - <<'EOF'
import json, os
def summ(t):
    rows = [json.loads(l) for l in open(os.path.expanduser(f"~/bench/hard8-{t}.jsonl"))]
    return sum(r["correct"] for r in rows), sum(r["pred"] is None for r in rows)
c20, n20 = summ("m2-20"); c30, n30 = summ("m2-30")
print("2 0 0.30 1 1 0 1.01 1.5" if (c30 >= c20 and n30 <= n20) else "2 0 0.20 1 1 0 1.01 1.5")
EOF
)
say "routing setting chosen: [$pick] ($(grep -E '^m2-(20|30) loops' ~/bench/m2_hard8.txt | tr '\n' ' '))"
docker exec $C sh -c "echo $pick > /tmp/glm53_car"

say "waiting for Claude Code smoke test"
until grep -q CC_SMOKE_DONE jobs/cc-smoke.out 2>/dev/null; do sleep 60; done
AGENT=$(python3 - <<'EOF'
import json, glob
r = json.load(open(glob.glob("$HOME/tb/jobs/cc-smoke-fixgit/result.json")[0]))
ex = {}
for e in r["stats"]["evals"].values(): ex.update(e.get("exception_stats") or {})
bad = [k for k in ex if k not in ("AgentTimeoutError",)]
print("terminus" if bad else "claude-code")
EOF
)
CFG=$([ "$AGENT" = claude-code ] && echo claude-code-local.yaml || echo terminus-local.yaml)
say "agent chosen: $AGENT (smoke: $(python3 -c "import json; r=json.load(open('$HOME/tb/jobs/cc-smoke-fixgit/result.json')); print([(e.get('reward_stats'), e.get('exception_stats')) for e in r['stats']['evals'].values()])"))"

TASKS=$(python3 - <<'EOF'
import glob, random, re, collections
by = collections.defaultdict(list)
for f in sorted(glob.glob("$HOME/tb/tb21/tasks/*/task.toml")):
    d = re.search(r'^difficulty = "(\w+)"', open(f).read(), re.M).group(1); by[d].append(f.split("/")[-2])
r = random.Random(0); pick = r.sample(by["easy"], 1) + r.sample(by["medium"], 12) + r.sample(by["hard"], 7)
print(" ".join(f"-i {t}" for t in pick))
open("$HOME/tb/subset20.txt", "w").write("\n".join(pick) + "\n")
EOF
)
say "running 20-task subset with $AGENT: $(tr '\n' ' ' < subset20.txt)"
g() { curl -s localhost:30270/stats | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('completion_tokens') or 0)"; }
t0=$(date +%s); tok0=$(g)
OPENAI_API_KEY=local ./venv/bin/harbor run -c $CFG -p tb21/tasks $TASKS --agent-timeout-multiplier 4 --allow-agent-host 172.17.0.1 \
  -n 2 -o jobs --job-name tb21-subset20 -y -q > jobs/tb21-subset20.out 2>&1
t1=$(date +%s); tok1=$(g)
say "subset done in $(( (t1 - t0) / 60 )) min; writing result"
SPEED=$(cd $HOME/glm53-flash-fit/claude-opt && python3 bench_multi.py --warm 1 --reps 2 --out res-tb-final-speed.json | tail -1)
python3 - "$pick" "$AGENT" "$SPEED" "$((tok1 - tok0))" "$((t1 - t0))" <<'EOF'
import json, sys, glob, math, collections
pick, agent, speed, toks, secs = sys.argv[1:6]
r = json.load(open("$HOME/tb/jobs/tb21-subset20/result.json"))
ev = list(r["stats"]["evals"].values())[0]
trials = {}
for d in glob.glob("$HOME/tb/jobs/tb21-subset20/*/result.json"):
    t = json.load(open(d)); name = t.get("task_name") or d.split("/")[-2].split("__")[0]
    rew = (t.get("verifier_result") or {}).get("rewards") or {}
    trials[name] = {"reward": rew.get("reward", 0.0), "exception": (t.get("exception_info") or {}).get("exception_type")}
n = len(trials); k = sum(1 for v in trials.values() if (v["reward"] or 0) >= 1.0); p = k / n if n else 0
ci = 196 * math.sqrt(p * (1 - p) / n) if n else 0
exc = collections.Counter(v["exception"] for v in trials.values() if v["exception"])
md = f"""# Terminal-Bench 2.1 — GLM-5.3-Flash on 2x RTX 3090 (this recipe) vs original

| Benchmark | Original GLM-5.3-Flash | Ours | Our decode speed |
|---|---:|---:|---:|
| Terminal-Bench 2.1 | **84.3** (Z.ai, Claude Code harness, 6 h timeouts, full 89 tasks) | **{100 * p:.1f} %** ({k}/{n}, ±{ci:.1f} 95 % CI) | {speed} |

* Our run: {agent} harness, 20-task stratified subset (1 easy / 12 medium / 7 hard, seed 0), 1 attempt each, task timeouts x4,
  2.05 bpw, routing [{pick}] (never skip VRAM/RAM experts), reliability layer on, 128k context.
* Server throughput during the run: {int(toks)} output tokens in {int(secs) // 60} min ({int(toks) / max(1, int(secs)):.1f} tok/s averaged over the run, incl. prefill and tool time).
* Exceptions: {dict(exc) or 'none'}

| Task | Reward | Exception |
|---|---:|---|
""" + "".join(f"| {t} | {v['reward']} | {v['exception'] or ''} |\n" for t, v in sorted(trials.items()))
open("$HOME/tb/RESULT.md", "w").write(md); print(md)
EOF
say "DONE — see ~/tb/RESULT.md"
echo TB_PIPELINE_DONE >> $LOG
