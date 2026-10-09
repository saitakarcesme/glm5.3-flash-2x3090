# Issues log

Every problem found while making this setup usable and benchmarking it, with its cause, the fix (if any) and its status.
This file is the input for the next full re-benchmark. Newest entries at the bottom of each section.

## Model quality

| # | Issue | Evidence | Cause | Fix / status |
|---|---|---|---|---|
| Q1 | 2.05 bpw never commits on ~38 % of MMLU-Pro questions | 20/53 runs hit the 32k cap with 90k–150k chars of circular, coherent reasoning; 30/33 correct when it answers | 2-bit quantization makes the model indecisive | **Open.** Presence penalty: no help. Budget forcing (12k): no help. DRY 0.8/range 4096: 5/8 on the hard set but 28 tok/s. DRY range 512: no help. **3.05 bpw: 5/8 at ~43 tok/s**, now the benchmark build |
| Q2 | Fast mode (CAR) loops in long agent turns (`OK — OK —`, `module-vs-X audit + …`) | pi sessions, agent suite | Expert skipping compounds over long generations | Loop guard (cut + exact for the rest of the request), detector v2 for long cycles |
| Q3 | Loops also recur after switching to exact | guard logs show restarts #2/#3 with exact=True | 2-bit model itself, not only CAR | Same as Q1 |
| Q4 | Teacher-forced probe is noisy | KL of the same config varies 0.24→0.43 between containers | Probe runs without admission; depends on what is resident | Use executed benchmarks for decisions, probe only as a rough guide |
| Q5 | Fast mode leaks "thinking out loud" into answers with thinking off | "Looking at the README…", "The user is asking…" | Distribution shift from CAR | Cosmetic, open |

## Serving / harness bugs (all fixed)

| # | Issue | Cause | Fix |
|---|---|---|---|
| S1 | Garbage tokens / character floods | Server sampled top-p 1.0 when the client sent none | Defaults from `generation_config.json` (top-p 0.95) |
| S2 | Agent turn ends with no tool call | `<tool_call>` opened inside the think block, parser treated it as reasoning | Parser treats `<tool_call>` during thinking as end of thinking |
| S3 | Client error "terminated" mid-turn | Tool-call content is held until parsable; no bytes for minutes → client body timeout | SSE keep-alive every 10 s |
| S4 | Turns spend all tokens thinking (exact too) | Over-deliberation | Thinking budget 6,144 tokens for agent requests (per-request override `thinking_budget`) |
| S5 | Long prose planning without a tool call | Same, after the think block | Act budget nudge (once per request) |
| S6 | Turn ends inside the think block with no answer | EOS while reasoning | Think-stop guard: close thinking, continue exact |
| S7 | Loop-guard false positive cut real content | Unit ≥ 240 chars matched markdown/table rules | Stricter thresholds (≥ 6 repeats over ≥ 400 chars; 1,000 for non-alphanumeric) |
| S8 | Renorm could amplify a lone kept expert many times | Scale tot/kept unbounded | Cap at 1.5× |
| S9 | `/v1/completions` crashed after the guard patch | Patch referenced a variable that only exists in chat | Separate call site |
| S10 | Decode after a long prompt ran with half-empty VRAM | Elastic prefill evicted ~6.6 GB of experts per GPU; GPU1 lost them | Post-prefill refill |
| S11 | GPU1 starts with 170/3040 slots filled | Warm-up only from that GPU's 1 GiB RAM tier | Iterative warm-up |
| S12 | 3.05 bpw crashed in prefill ("staging overflow 218 > 204") | Staging sized for 6.3 MB experts | `GLM53_EC_STAGE_GB=2.75` for 3.05 |

## Benchmark-harness pitfalls (ours)

| # | Issue | Fix |
|---|---|---|
| H1 | pi context window set to 32k to match Qwen → GLM truncated its own turn | Qwen's vLLM had 101k KV available; both run at 96k |
| H2 | Session runner only treated `stop` as finished → 75 min idle video | In-flight-aware idle detection |
| H3 | Agent workspace could see the other model's files and logs | Separate workspace roots |
| H4 | Task dir named `site` made `./site` ambiguous | Renamed to `webpage` |
| H5 | Proxy "decode tok/s" wrong for buffered tool calls and vLLM bursts | Use end-to-end tok/s and server-side counters |
| H6 | 32k output cap too low for full-effort GLM reasoning | 64k for benchmarks (official runs allow 64k–160k) |
| H7 | `pkill -f` patterns matched our own SSH command | Process control only through uploaded scripts |
| H8 | Stopping a benchmark let the queue chain into the next one | Stop the queue script before the benchmark process |
| H9 | GPQA is gated | HF token on the rig (read-only; revoke after) |
| H10 | 3 AA-LCR questions (80, 81, 98) have unmatched document filenames | Excluded |
| H11 | git hangs in the iCloud-synced Desktop folder | Working clone in `~/code` |

## Infrastructure

| # | Issue | Note |
|---|---|---|
| I1 | Tailscale SSH re-auth prompts every few hours | Needs the user to click the approval link |
| I2 | Mac disk ~2–5 GB free | Keep artifacts on the rig |
| I3 | Rig RAM tight (~3–5 GB free with desktop + 26 GB container) | Container cap 26 GB |

## Terminal-Bench 2.1 (in progress)

| # | Issue | Cause | Fix / status |
|---|---|---|---|
| T1 | Smoke test fix-git: AgentTimeoutError after only 1 completed model call | 2nd call ran > 14 min | see T2–T5 | — |
| T2 | Loop guard false positive on terminus-2 tool batches (`"keystrokes": …, "duration": 0.1}, {`) | 8-gram rule sees legit repetitive JSON as a loop | **fix**: n-gram rule only outside tool-call/JSON content; stricter unit rule there |
| T3 | Exact-mode fallback too slow for agents (~14 tok/s on 3.05) → task timeout | exact = every expert, NVMe-bound | **fix**: fallback to gentle CAR (10 %) instead of exact |
| T4 | Gibberish thinking on 3.05 fast ("collision audit.max, 363. Final keys access_submit invariant sig span…") | 3.05 fits only ~29 % of experts in VRAM; CAR 15 % skips many more experts than on 2.05 | **test**: gentler CAR on 3.05 |
| T5 | Genuine degenerate command list (`git log --max-parents=100 …` variants) | same as T4 | guard catches it; root cause T4 |
| T6 | Default agent timeouts (900 s) assume hosted-API speed | local ~43 tok/s | run with `--agent-timeout-multiplier 4` and report it |
| T7 | Loops persist on 3.05 even at CAR 10 % ("ORG ORG? ORG IS SEQUENTIAL", repeated `xxd -g1 -e -c`) | 3.05 keeps only ~29 % of experts in VRAM, so CAR still skips a lot | **study running**: loop rate CAR 15 % vs exact on identical prompts |
| T8 | Suspected MTP sampling distortion | Reviewed `iterate_draftmodel_mtp_gen` + verify loop: target tokens are sampled from the target logits, drafts accepted only on exact match (sample-and-match) | **Not a cause**: verification is distributionally exact |
| T9 | Guard log label `exact=True` is misleading after v3 | the fallback is now gentle CAR, not exact | cosmetic; rename to `fallback=` |
| T10 | TB cleanup script removed every non-GLM running container | pattern too broad (only safe because none were running) | narrowed to Harbor task containers (`__` in name) |
| T11 | LiteLLM `openai/` provider sent Claude Code's /v1/messages to an endpoint our server lacks (404) | translated to the Responses API | use `hosted_vllm/` provider (chat completions) |
| T12 | LiteLLM refuses to start without a master key | safe default | random local key, owner-only file; proxy bound to docker0 (172.17.0.1) only |
| T13 | **Root cause of indecision/loops: CAR**, not MTP or (mainly) quantization | 3.05, same 3 hard questions, 16k cap: exact 2/3 correct in 728 / 1,920 tokens, 0 loops; CAR 15 % 0/3, 2 unanswered, ~16k tokens each, 5 loops | Skipping experts makes the model indecisive; the tok/s gain is eaten by 10× longer, worse reasoning. **Next**: near-lossless CAR / faster exact |
| T14 | **Q1 re-diagnosed: 2.05 is not the problem** | 2.05 exact on the same 3 hard questions: 2/3 correct in 1,565 / 711 tokens, 0 loops (= 3.05 exact). Near-lossless CAR (mode 2: keep VRAM+RAM experts, drop NVMe-only < 5 %): 2/3, 0 loops, 15.6 tok/s | The earlier "2-bit is indecisive" conclusion was confounded by CAR 15 %. Direction: 2.05 + faithful routing |
| T15 | Which experts may be skipped | 2.05, 3 hard questions: mode 2 (never skip VRAM/RAM experts, skip NVMe-only < 20 %) 3/3 correct at 30.5 tok/s; < 10 %: 2/3 at 18.1; mode 3 (also skips RAM experts) 2/3 at 17.5 | **Never skip RAM-resident experts**; only NVMe-only, low-weight ones. Validating on the 8-question set |
| T16 | Claude Code harness in task containers: "API Error: Unable to connect to API (ConnectionRefused)" | The host firewall blocks container → host connections (even the default bridge can't reach a host service on 172.17.0.1); fixing it needs root | **Open (needs the owner)**: allow docker bridges → 172.17.0.1:4000 in the host firewall. Tonight's run uses terminus-2 (host-side agent, unaffected) and reports the harness difference |
| T17 | TB subset: first 2 tasks AgentTimeoutError (60 min) with only 8–12 short turns | one call took 33 min: 3 consecutive thinking loops caught by the guard, each costing thousands of tokens; `-n 2` made two contexts alternate, churning the expert cache (more NVMe-only experts skipped → more loops) and making each task wait | **fix**: `-n 1`; loop fallback = mode 2 / 10 % (the old fallback, mode 3 / 10 %, skipped RAM experts) |
| T18 | One agent call ran 42+ min (build-cython-ext) | after the guard's 3 restarts it stopped intervening and the model looped to the 32k output cap (~30 min at this speed) | **fix (guard v4)**: a 4th loop ends the turn with the text before the loop; agent turns also end after 12,288 tokens without a tool call. Subset restarted from scratch at 15:03 |
