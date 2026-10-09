#!/usr/bin/env bash
# Terminal-Bench 2.1, 10-task stratified subset (1 easy / 6 medium / 3 hard, from the seed-0 20-task list), Claude Code
# harness (official GLM setup), faithful routing, timeouts x2 (hosted ~51 tok/s vs ours ~29), 1 attempt, one task at a time.
set -u
cd ~/tb
S=/home/isa/Experiments/glm53-flash-fit/claude-opt/STATUS.txt
LOG=~/tb/run10b.log
say() { echo "$(date +%T) $*" | tee -a $LOG; echo "TB10: $*" > $S; }
TASKS=$(python3 - <<'EOF'
import glob, random, re, collections
by = collections.defaultdict(list)
for f in sorted(glob.glob("/home/isa/tb/tb21/tasks/*/task.toml")):
    d = re.search(r'^difficulty = "(\w+)"', open(f).read(), re.M).group(1); by[d].append(f.split("/")[-2])
r = random.Random(0); e = r.sample(by["easy"], 1); m = r.sample(by["medium"], 12); h = r.sample(by["hard"], 7)
pick = e + m[:6] + h[:3]
open("/home/isa/tb/subset10.txt", "w").write("\n".join(pick) + "\n")
print(" ".join(f"-i {t}" for t in pick))
EOF
)
say "running 10 tasks with claude-code: $(tr '\n' ' ' < subset10.txt)"
g() { curl -s localhost:30270/stats | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('completion_tokens') or 0)"; }
t0=$(date +%s); tok0=$(g)

./venv/bin/harbor run -c claude-code-local.yaml -p tb21/tasks $TASKS --agent-timeout-multiplier 2 -n 1 -o jobs --job-name tb21-cc10b -y -q > jobs/tb21-cc10b.out 2>&1
t1=$(date +%s); tok1=$(g)
say "done in $(( (t1 - t0) / 60 )) min; measuring speed and writing result"
SPEED=$(cd /home/isa/Experiments/glm53-flash-fit/claude-opt && python3 bench_multi.py --warm 1 --reps 2 --out res-tb10b-final-speed.json | tail -1)
python3 - "$SPEED" "$((tok1 - tok0))" "$((t1 - t0))" <<'EOF'
import json, sys, glob, math, collections, re
speed, toks, secs = sys.argv[1:4]
trials = {}
for d in glob.glob("/home/isa/tb/jobs/tb21-cc10b/*/result.json"):
    t = json.load(open(d)); name = d.split("/")[-2].split("__")[0]
    rew = ((t.get("verifier_result") or {}).get("rewards") or {}).get("reward", 0.0) or 0.0
    diff = re.search(r'^difficulty = "(\w+)"', open(f"/home/isa/tb/tb21/tasks/{name}/task.toml").read(), re.M).group(1)
    trials[name] = {"reward": rew, "difficulty": diff, "exception": (t.get("exception_info") or {}).get("exception_type")}
n = len(trials); k = sum(1 for v in trials.values() if v["reward"] >= 1.0); p = k / n if n else 0
ci = 196 * math.sqrt(p * (1 - p) / n) if n else 0
m = re.search(r"AGG ([\d.]+)", speed); agg = m.group(1) if m else speed
md = f"""# Terminal-Bench 2.1 — original GLM-5.3-Flash vs ours

| Benchmark | Original GLM-5.3-Flash | Ours (2×3090, faithful profile) | Our decode speed |
|---|---:|---:|---:|
| Terminal-Bench 2.1 | **84.3** | **{100 * p:.0f} %** ({k}/{n} tasks, ±{ci:.0f} pts 95 % CI) | **{agg} tok/s** |

Setup differences (be aware when comparing):
* Original: Z.ai's run, Claude Code harness, all 89 tasks, 6 h task timeouts (leaderboard protocol: 5 attempts per task).
* Ours: Claude Code 2.1.123 harness (same as official GLM entries), **10-task stratified subset** (1 easy / 6 medium / 3 hard,
  seed 0), 1 attempt, task timeouts ×2 (to compensate for ~29 vs ~51 tok/s hosted), GLM-5.3-Flash EXL3 2.05 bpw on
  2× RTX 3090 + 32 GB DDR4 + 1 NVMe, faithful routing (never skips VRAM/RAM experts), reliability layer on, 128k context, prompt-cache fix (billing header stripped).
* Server output during the run: {int(toks)} tokens in {int(secs) // 60} min.

| Task | Difficulty | Reward | Exception |
|---|---|---:|---|
""" + "".join(f"| {t} | {v['difficulty']} | {v['reward']} | {v['exception'] or ''} |\n" for t, v in sorted(trials.items(), key=lambda x: x[1]['difficulty']))
open("/home/isa/tb/RESULT.md", "w").write(md); print(md)
EOF
say "DONE — ~/tb/RESULT.md"
echo RUN10_DONE >> $LOG
