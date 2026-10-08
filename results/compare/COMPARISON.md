# pi agent comparison: GLM-5.3-Flash (this recipe) vs Qwen3.8 27B, same rig

Both sessions ran on the same 2× RTX 3090 box, one after the other, with **the same prompt** (`prompt.txt`), the same
pi version and settings (`--thinking high`, context window 98,304 tokens for both, max 16,384 output tokens per turn) and
identical workspaces (`./research` = this repo's README, JOURNAL and raw results). Each session was screen-recorded.
Proxy request logs: `*-requests.jsonl`; analysis: `analysis.json`.

| | GLM-5.3-Flash 2.05 bpw (fast CAR profile, 2× 3090 + NVMe offload) | Qwen3.8 27B W4A16 (vLLM TP2 + DFlash2 speculative) |
|---|---|---|
| Agent wall time | 41 min (67 requests) | 2.6 min (7 requests) |
| Output tokens | 84,624 | 17,428 |
| Decode speed | **58.1 tok/s** (streamed turns) | **~124 tok/s** (vLLM counters: 17,428 tok / 141 s decode) |
| End-to-end output tok/s (incl. prefill) | 34.3 | 112.1 |
| Median TTFT | 10.0 s | 2.8 s |
| How it ended | normal stop | **truncated** (`length`): wrote the whole site as chat text (25k chars thinking + 13.6k chars HTML) instead of using the write tool, and hit the 16,384-token cap |
| Website produced | partial: one 2.6 KB `index.html` (header, nav, hardware table, 1 inline SVG) linking a `style.css` that was never written; it rewrote the file 6× and once deleted everything | **none** |

Honest reading:
* Neither model finished this task well in one unattended pass at these settings.
* Qwen3.8 27B fits fully in VRAM and is ~2× faster at decode and ~4× faster at prefill/TTFT than GLM-5.3-Flash
  streaming experts from RAM/NVMe.
* GLM kept working through tool calls for 41 minutes but produced a thin page. Its output went mostly into thinking.
* This is a single run per model, not a benchmark. The 16k per-turn output cap and `--thinking high` affect both models.

Videos (not in git, on the rig): `~/Videos/glm-compare/20261008-0425-pi-GLM.mp4` (42.8 min),
`~/Videos/glm-compare/20261008-0513-pi-QWEN.mp4` (4.3 min). An earlier GLM attempt with a 32k window was aborted after
the model truncated its own turn: `20261008-0308-pi-GLM-attempt1-FAILED-ctx32k.mp4`.
