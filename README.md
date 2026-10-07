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

## Results (decode tok/s, greedy, 3 prompts × 256 tokens, warm cache, concurrency 1)

| Profile | Decode tok/s | TTFT (short prompt) | Context | Lossless? |
|---|---:|---:|---:|---|
| Starting point (21/21 split, RAM tier 6+6 GiB) | 8.5 | 3.9 s | 8k | yes |
| **exact** — 27/15 split, RAM 16.5+1 GiB, per-GPU pinning, prefetch | **14.1** | 2.8 s | 8k | **yes** |
| **fast** — exact layout + cache-aware routing (CAR), 8k ctx | **53.8–55.5** | 0.25 s | 8k | **no** |
| **fast**, 128k ctx (4k prefill chunks) | **54.4** | 0.24 s | 128k | **no** |

Other measurements (fast profile, 128k build):
* Prefill ≈ **515–535 tok/s** (4096-token chunks; it was ≈150 tok/s with 1024-token chunks).
* **Prefix reuse works**: a 21.6k-token prompt took 47.9 s the first time and 0.6–0.8 s on the next turns with the same prefix
  (agent-style use).
* Needle-in-a-haystack: 16k ✅; 64k found the right code but in the wrong letter case and with a stray `</think>` ❌
  (decode is CAR-lossy; see open issues).

## What "fast" does, and what it costs

**Cache-aware routing (CAR)** changes the model's computation. For each token, each of the 8 routed experts is kept only if:

* it is already in VRAM, or
* it is in host RAM and is the token's top-1 expert or has ≥ 15 % of the routing weight, or
* it is NVMe-only and has ≥ 30 % of the routing weight.

Skipped experts get weight 0. The kept weights are renormalised to the original sum, and the skipped slot is pointed at
a kept VRAM-resident expert (the MoE kernel rejects id −1). Prefill (staged path) stays exact. Implementation: a fused
CUDA kernel in `runtime/car_kernel/car.cu`, wired into `runtime/nv2.py`; it can be switched at runtime through
`/tmp/glm53_car` inside the container.

Quality measured so far (fast vs exact; the same container is switched at runtime):

| Check | exact | fast |
|---|---|---|
| 16 short exact-answer questions (arithmetic, facts, tiny code) | 16/16 | 16/16 |
| Repeated-4-gram loops in 3 long generations | none | none |
| Tool call + tool-result continuation fixture | pass | pass |
| 6800-token sentinel instruction | pass | pass (42–46 s) |
| Teacher-forced next-token agreement over ~1,200 positions | 100 % | **88 %** (mean KL 0.21) |
| Hard-coding benchmark (32 problems, executed tests), CAR 15 % (`fast`) | **28/32** | **23/32** |
| same, CAR 10 % (`3 1 0.10 1 1 0 0.30`, 47 tok/s) | 28/32 | 27/32 |

**Be clear about this:** on hard code the 15 % fast setting loses ~5 of 32 problems; the 10 % setting loses 1 at 47 tok/s. at the token level the fast profile is a different model (~1 in 8 next-token choices differ
under teacher forcing). The short factual and format checks pass, but that is not a broad quality guarantee. An earlier
variant (no renormalisation) answered `17×23 = 490` once and looped in a Turkish story, and was dropped. Use `exact`
when correctness matters more than speed.

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
2. Moving host RAM to GPU0's tier. This needed freeing 7.6 GB of orphaned `/dev/shm` torch segments that zram was
   holding.
3. CAR.
4. A full iterative VRAM warm-up (GPU1 started with only 170 of 3,040 slots filled).
5. Prefetch off under CAR.

## Running it

```sh
export GLM_MODEL_DIR=/path/to/GLM-5.3-Flash-exl3-2.05bpw      # turboderp/GLM-5.3-Flash-exl3, 2.05bpw branch
export GLM_STORE_DIR=/path/to/nvme-store                      # packed with the upstream image's `pack-store`
profiles/launch.sh fast        # or: profiles/launch.sh exact ;  CTX=8192 for the 8k variant
curl http://127.0.0.1:30270/v1/models
```

The container needs `--memory 26g`. Host RAM is tight (~3–5 GB left with a desktop session). The CPU pinning in
`profiles/launch.sh` is specific to a 6P+4E i5-14400F; adapt it to your CPU.

Switch modes without a restart:
`docker exec glm53 sh -c 'echo 0 2 0 1 1 1 > /tmp/glm53_car'` (exact) / `'echo 3 1 0.15 1 1 0 0.30 > /tmp/glm53_car'` (fast).
The fields are `mode keep thresh renorm small prefetch tnv`.

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

* **Post-prefill cache holes.** A long prefill hands ~6.7 GB of expert VRAM per GPU to activations ("elastic"). GPU0
  writes those experts back to RAM; GPU1 (1 GiB RAM tier) mostly loses them, so decode right after a long prompt runs
  with a half-empty cache and CAR skips more experts. A refill after prefill is the next fix.
* Coding-benchmark comparison of exact vs fast (in progress), then thinking mode.
* Contexts above 128k (8-bit KV cache) and the prefill speed for them.

Credits: [0xSero](https://github.com/0xSero) for the offload runtime and NVMe store design, turboderp for ExLlamaV3 and
the EXL3 quants. Tuning and the CAR work were done in a Claude Code session (Opus 5.5).
