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
