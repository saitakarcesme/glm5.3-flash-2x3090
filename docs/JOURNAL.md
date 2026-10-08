# Journal (2026-10-07 → )

All decode numbers are greedy, concurrency 1, warm cache. "1-prompt" is a single 256-token explanation prompt; "3-prompt"
is three prompts (DB explanation, Python code, Turkish prose), aggregated as total tokens / total decode time.

## Day 1 — lossless tuning (8.5 → 14.1 tok/s)

| Step | 1-prompt | 3-prompt | Note |
|---|---:|---:|---|
| Starting profile (21/21, RAM 6+6 GiB, MTP1) | 9.69 | 8.52 | warm for 3 h |
| + NVMe layer-ahead prefetch | 9.20 | | speculative reads evicted useful RAM entries |
| + per-GPU controller/reader pinning | 9.50 | | both controllers had been spinning on one logical CPU |
| RAM tier 8.5+8.5 GiB (after freeing 7.6 GB of orphaned `/dev/shm`) | 9.24 | | NVMe reads −38 %, no speedup |
| Budget 5.4 → 29/13 split | 10.28 | | GPU1 had zero misses, so its RAM tier sat idle |
| 29/13 + RAM 15/1 GiB | 12.54 | | |
| 27/15 + RAM 15/1 GiB | 15.55 | | GPU1 near-zero NVMe |
| 27/15 + RAM 16.5/1 + pinning + prefetch | | **14.06** | deployed as the lossless profile |

Diagnosis that drove this: raw NVMe does 4.5–5 GB/s (no throttling at 55–60 °C), GPU0 H2D does 20 GB/s and GPU1 (chipset
x4) does 6.4 GB/s. In the 21/21 split GPU1 was link-bound copying experts. Changing the split changes the greedy text
(near-tie at token 2), but the logit probe vs a single-GPU reference got *closer* (KL 0.00027 → 0.00006).

## Day 1 evening — cache-aware routing (14 → 54 tok/s, lossy)

| Step | 3-prompt | Quality signal |
|---|---:|---|
| CAR mode 1 (skip non-VRAM), keep top-2 | 28.1 | top-1 90.0 %, ppl 1.18 → 1.36 |
| keep top-1 + w ≥ 15 %, no renorm | 31.3 | top-1 91.3 %, KL 0.106 |
| fused kernel + iterative full VRAM warm-up | 31.5 | same |
| CUPTI: GPU-bound; py-spy: main thread 76 % waiting on GPU | — | — |
| prefetch off under CAR | 43.1 (1-prompt) | MTP acceptance back to 75 % |
| mode 3 (tier-aware: RAM ≥ 15 %, NVMe-only ≥ 30 %), no renorm | 51.2–53.9 | once: 17×23 = 490, Turkish loop |
| **mode 3 + renorm** | **53.8–55.6** | 16/16 factual, no loops, teacher-forced top-1 88 % |

## Day 2 — context and daily use

* 128k context: the loader budget must include the KV cache and the prefill transient. With `B0=8.0`, `B1=12` and
  4096-token chunks you get 27/15 again. Fast decode is 54.4 tok/s; prefill went from ~150 to ~520 tok/s.
* Prefix reuse across turns works (47.9 s → 0.6–0.8 s TTFT on a 21.6k-token repeated prefix).
* Needle 16k pass; 64k right code, wrong format (post-prefill cache holes + CAR).
* Coding benchmark (author-written, 32 problems, executed tests): in progress.

## Day 2 — accuracy

* Post-prefill refill: the 64k needle that failed now passes; long-context coding (unique ~4k context per problem): exact 27/32, fast 27/32, mid 25/32.
* Per-GPU CAR: running GPU1 exact halves speed (its misses are NVMe over an x4 link), and most of the token-level deviation came from GPU1 skipping experts.
* Fix: RAM tier 13.5 GiB (GPU0) / 4 GiB (GPU1). Short coding set, same container: exact 27/32, fast 26/32 at 54.7 tok/s (it was 23/32 before).
* The teacher-forced probe is noisy here (it runs without admission, so it depends on whatever is resident); executed coding pass rate is the decision metric.

## Day 2 — agent reliability

* pi website sessions failed for both models. GLM's failure was traced through the saved sessions, not guessed:
  1. Exact and fast both spent whole 16k-token turns thinking (exact: coherent re-derivation of numbers; fast: `OK — OK —` loop).
  2. The server sampled with top-p 1.0 when the client sent nothing (the model card says 0.95).
  3. The model sometimes starts `<tool_call>` before closing `</think>`; the parser then returned no tool call and pi ended the run.
* Prefix reuse is bit-exact (same 496-char greedy output with and without the cache), and long-context recall at ~41k tokens
  is 6/6 in every mode, so neither caused the failures.
* Fixes: official sampling defaults, thinking budget, act budget, loop guard (exact fallback), think/tool parser fix,
  renorm cap. Loop-detector thresholds were tightened after a false positive (≥ 6 repeats over ≥ 400 chars; 1,000 for
  non-alphanumeric units).
* Agent suite (fast, before the parser fix): bug fix, data, feature, refactor and single-page site pass, matching exact.
  The report-site task produced its first correct 10 KB page with the guards, then stopped because of the
  think/tool parser bug, which is now fixed.

## Day 3 — public benchmarks and the quantization question

* Benchmark targets (original GLM-5.3-Flash): GPQA Diamond 86.4 (Vals) / 91.2 (AA), MMLU-Pro 86.1 (Vals), LiveCodeBench 80.5
  (Vals), AA-LCR 80.0 (AA); agentic Terminal-Bench 2.1 84.3 and DeepSWE v1.1 63.4 (Z.ai, 6 h/task harnesses).
* First MMLU-Pro pass on the 2.05 build (53/70 done, 32k cap): 30/33 correct when it answers (above the original 86.1 %), but
  20 of 53 runs never commit: 90k–150k characters of coherent but circular reasoning until the cap.
* Hard set (8 of those questions, same settings): 2.05 baseline 3/8 (5 unanswered); presence penalty 3/8; budget forcing at
  12k thinking tokens 3/8; DRY (multiplier 0.8, range 4096) 5/8 but 28 tok/s; DRY range 512 no help; **3.05 bpw 5/8** at
  ~42 tok/s. The indecision is mostly the 2-bit quantization, not the routing.
* 3.05 bpw on the same stack: 26/16 split (`B0=8.5`), staging 2.75 GB (2.05's 1.8 GB overflowed with 9.44 MB experts),
  42.8 tok/s on the 3-prompt benchmark. Full benchmark pass running on this build.
* Server additions: SSE keep-alive (fixes client "terminated" on long held tool calls), loop detector v2 (units up to 600
  chars), think-stop guard, per-request `thinking_budget`, OpenAI penalties + DRY passthrough.
