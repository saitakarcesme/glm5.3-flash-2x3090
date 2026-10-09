# GLM-5.3-Flash on 2× RTX 3090 + 32 GB DDR4 + one NVMe

A recipe (and the measurements behind it) for running **GLM-5.3-Flash** (EXL3 **2.05 bpw**, ~76 GB of routed experts,
288 experts × 42 MoE layers, native MTP) on a consumer box that cannot hold the model in VRAM or RAM:

| | |
|---|---|
| GPUs | 2× RTX 3090 24 GB. GPU0 on CPU PCIe 4.0 x16 (measured 20 GB/s H2D), GPU1 on a B760 chipset PCIe 4.0 **x4** (6.4 GB/s). No P2P/NVLink. |
| CPU / RAM | i5-14400F, 32 GB DDR4 (≈17.5 GB usable as expert cache) |
| Disk | 1× Kingston NV3 2 TB (DRAM-less), LUKS + btrfs; ~4.5–5 GB/s sustained O_DIRECT reads |
| Stack | [`sybil-solutions/glm53-flash-offload`](https://github.com/sybil-solutions/glm53-flash-offload) image (ExLlamaV3 1.5.1) + the patches in this repo |

Experts are tiered VRAM → pinned host RAM → packed NVMe store. Everything here was measured on that one machine; your
numbers will differ.

## Profiles (decode tok/s, 3 prompts × 256 tokens, warm cache, concurrency 1, 128k context)

| Profile | Decode tok/s | What it skips | Use it for |
|---|---:|---|---|
| Starting point (21/21 split, RAM tier 6+6 GiB) | 8.5 | nothing | — |
| **exact** | **~13–14** | nothing (bit-exact expert path) | reference, maximum fidelity |
| **faithful** (default) — mode 2 / 20 % | **~29** | only experts that are neither in VRAM nor in RAM *and* carry < 20 % of the token's routing weight | **daily use, reasoning, agents** |
| fast (lossy) — mode 3 / 15 % | ~54 | also RAM-resident experts under 15 % | short single-turn answers only, see the warning below |

**Warning about `fast`.** It looks fine on short tasks (16/16 factual, 53/64 executed coding problems vs 54/64 exact) but it
**breaks long multi-step reasoning**: on the same hard MMLU-Pro questions, exact answers 2/3 correctly in 700–2,000 tokens with
no loops, while `fast` answers 0/3, runs to the 16k-token cap and loops. The extra tok/s is eaten by 10× longer, worse
reasoning. Skipping experts that are already in **RAM** is what does the damage; skipping only rare NVMe-only, low-weight
experts (`faithful`) keeps the exact behaviour on the same questions (mode 2 / 20 %: 3/3 on the 3-question check, 4/8 with
0 loops on the 8 hardest MMLU-Pro questions; the 30 % variant collapsed to 1/8).

Other measurements (128k build):
* Prefill ≈ **515–535 tok/s** (4096-token chunks; it was ≈150 tok/s with 1024-token chunks).
* **Prefix reuse works**: a 21.6k-token prompt took 47.9 s the first time and 0.6–0.8 s on later turns (agent-style use).
* Needle-in-a-haystack: 16k ✅, 64k ✅ (after the post-prefill refill).
* Hosted GLM-5.3-Flash APIs run at ~51 tok/s (Artificial Analysis); `faithful` is ~29 tok/s on this box.

## How the routing modes work (cache-aware routing, CAR)

Experts live in VRAM, then pinned host RAM, then the NVMe store. For each token and each of its 8 routed experts, CAR
decides whether to compute it:

* **exact** (`0 …`): always.
* **faithful / mode 2** (`2 0 0.20 1 1 0 1.01 1.5`): if it is in VRAM or RAM, always; if it is NVMe-only, only when its
  routing weight is ≥ 20 % of the token's total.
* **fast / mode 3** (`3 1 0.15 1 1 0 0.30 1.5`): RAM-resident experts only if top-1 or ≥ 15 %; NVMe-only only if ≥ 30 %.

Skipped experts get weight 0, kept weights are renormalised (capped at 1.5×), and the skipped slot points at a kept
VRAM-resident expert (the MoE kernel rejects id −1). Prefill (staged path) stays exact. Implementation: a fused CUDA kernel
in `runtime/car_kernel/car.cu`, wired into `runtime/nv2.py`; switchable at runtime through `/tmp/glm53_car`.

Earlier quality numbers for the `fast` profile (kept for the record): 16/16 short factual questions; teacher-forced top-1
agreement 88 %; executed coding problems 53/64 vs exact 54/64 after the RAM rebalance. These single-turn checks did not
reveal the reasoning failure above; the agent and hard-reasoning tests did.

## Reliability layer for agent use (server side)

The pi agent sessions exposed failure modes that single-turn benchmarks never hit. Each one was reproduced first, then
fixed in `runtime/serve_claude.py`:

| Failure seen in agent sessions | Cause | Fix |
|---|---|---|
| Garbage tokens / character floods in long turns | Server sampled with top-p 1.0 when the client sent none; the full tail of a 2-bit model derails | Default to the model's `generation_config.json` (temperature 1.0, **top-p 0.95**) |
| Turn spends all 16k tokens thinking (exact mode too), never acts | GLM over-deliberates on noisy inputs | **Thinking budget**: after 6,144 reasoning tokens, close `</think>` and continue (budget forcing) |
| Long prose planning in the answer, no tool call | Same, after the think block | **Act budget**: once per request, a one-line nudge after ~3,000 answer tokens without a tool call |
| Degenerate loops (`OK — OK — …`) | Mostly aggressive CAR (see above) | **Loop guard**: cut back to the loop start, continue with a more faithful routing; a 4th loop ends the turn; agent turns end after 12,288 tokens without a tool call |
| Agent stops with `finish=stop` and no tool call | Model opens `<tool_call>` *inside* the think block; the parser treated it as reasoning | Treat `<tool_call>` during thinking as the end of the thinking (streaming and non-streaming) |
| Runaway amplification when most experts are skipped | Renormalisation scale tot/kept unbounded | Cap at 1.5× (`GLM53_CAR_MAXSCALE`) |

Agent suite (`bench/agentbench`, pi non-interactive, 6 tasks, automatic checks in a `--network none` container):
small and medium tasks (bug fix, feature, refactor, data, single page) pass in fast mode, as they do in exact mode, at 2–5×
the speed. The hardest task (synthesise a site from long, noisy notes) is still being stabilised; see `docs/JOURNAL.md`.

## Things that were measured and did *not* help

| Idea | Result |
|---|---|
| NVMe layer-ahead prefetch in the original 21/21 layout | 9.2 vs 9.7 tok/s (speculative reads polluted the RAM tier) |
| Larger RAM tier split evenly 8.5+8.5 GiB | NVMe reads −38 %, tok/s unchanged (GPU1's x4 link was the wall) |
| MTP with 2 or 3 draft tokens | slower in every mode (12.8 exact; 26.5 / 21.7 fast) |
| Smaller VRAM activation reserve (0.6 GB) | OOM during prefill |
| CUDA graphs (considered) | a CUPTI trace showed one GPU busy ~95 % of wall time, so there are no launch gaps to remove |

The main wins, in order:

1. Moving layers **off** the x4 GPU (27/15) so GPU1 is almost fully VRAM-resident.
2. Moving host RAM to GPU0's tier (later rebalanced to 13.5 / 4 GiB: with CAR, GPU1's misses must be cheap RAM hits, not NVMe). This needed freeing 7.6 GB of orphaned `/dev/shm` torch segments that zram was
   holding.
3. Faithful CAR (never skip VRAM/RAM experts).
4. A full iterative VRAM warm-up (GPU1 started with only 170 of 3,040 slots filled).
5. Prefetch off under CAR.

## Running it

```sh
export GLM_MODEL_DIR=/path/to/GLM-5.3-Flash-exl3-2.05bpw      # turboderp/GLM-5.3-Flash-exl3, 2.05bpw branch
export GLM_STORE_DIR=/path/to/nvme-store                      # packed with the upstream image's `pack-store`
profiles/launch.sh faithful    # or: exact | fast ;  CTX=8192 for the 8k variant
curl http://127.0.0.1:30270/v1/models
```

The container needs `--memory 26g`. Host RAM is tight (~3–5 GB left with a desktop session). The CPU pinning in
`profiles/launch.sh` is specific to a 6P+4E i5-14400F; adapt it to your CPU.

Switch modes without a restart:
`docker exec glm53 sh -c 'echo 0 2 0 1 1 1 > /tmp/glm53_car'` (exact) / `'echo 2 0 0.20 1 1 0 1.01 1.5 > /tmp/glm53_car'` (faithful) /
`'echo 3 1 0.15 1 1 0 0.30 1.5 > /tmp/glm53_car'` (fast). The fields are `mode keep thresh renorm small prefetch tnv maxscale`.

## Repo layout

* `profiles/launch.sh` — the two profiles.
* `runtime/` — patched `nv2.py` (per-GPU RAM tier / CPU pinning, iterative warm-up, CAR) and `serve_claude.py` (configurable
  GPU1 load budget). `runtime/base/` holds the unchanged dual-GPU port it builds on.
* `patches/` — the individual patch scripts, in the order they were applied.
* `bench/` — decode benchmarks, KL / teacher-forced probe, factual check, needle and prefix-reuse tests, `codeeval/`
  (an author-written 32-problem coding benchmark with verified reference solutions; generated code is executed in a
  `--network none` container).
* `results/raw/` — raw logs of every sweep.
* `docs/JOURNAL.md` — chronological notes.

## Open issues / next steps

* ~~Post-prefill cache holes~~ **fixed** (`runtime/expert_cache.py` + `Nv2.refill`): a long prefill hands ~6.6 GB of expert
  VRAM per GPU to activations; the evicted experts are now re-admitted right after prefill (GPU0 1,053 in 0.45 s from RAM,
  GPU1 1,056 in 2.0 s mostly from NVMe). The 64k needle that failed before now passes.
* Terminal-Bench 2.1 run on the `faithful` profile (in progress); every issue found is logged in `docs/ISSUES.md`.
* Claude Code harness needs the host firewall to allow docker networks → the local proxy (see ISSUES T16).
* Contexts above 128k (8-bit KV cache) and the prefill speed for them.

Credits: [0xSero](https://github.com/0xSero) for the offload runtime and NVMe store design, turboderp for ExLlamaV3 and
the EXL3 quants. Tuning and the CAR work were done in a Claude Code session (Opus 5.5).
