#!/usr/bin/env bash
# Claude-tuned GLM-5.3-Flash 2.05bpw profile (2026-10-07): 27/15 layer split (GPU0 budget 5.2), RAM tier 16.5 GiB on GPU0 /
# 1 GiB on GPU1, per-GPU controller/reader CPU pinning, layer-ahead NVMe prefetch. Uses claude-opt/nv2.py (per-GPU env overrides).
set -euo pipefail
cd /home/isa/Experiments/glm53-flash-fit/claude-opt
NV2_PY=$PWD/nv2.py MEM=26g ./launch_exp.sh glm53-2bit-claude27 \
  "--restart unless-stopped -e GLM53_MAIN_GPU0_BUDGET=5.2 -e GLM53_NV_RAM_GB_0=16.5 -e GLM53_NV_RAM_GB_1=1 -e GLM53_NV_CTL_CPU_0=2 -e GLM53_NV_CTL_CPU_1=4 -e GLM53_NV_READER_CPUS_0=12-15 -e GLM53_NV_READER_CPUS_1=8-11 -e GLM53_NV_PREFETCH=1"
