#!/usr/bin/env bash
# Claude fast profile (2026-10-07): claude27 layout (27/15 split, RAM 16.5/1 GiB, per-GPU pinning) + iterative full VRAM warm +
# tier-aware cache-aware routing (CAR mode 3: VRAM picks always; RAM picks if top-1 or w >= 15% of row; NVMe-only picks only if
# w >= 30%), prefetch off. LOSSY (teacher-forced top-1 ~88% vs exact; 16/16 factual). Runtime switch, no restart:
#   exact: docker exec glm53-2bit-claude50 sh -c "echo 0 2 0 1 1 1 > /tmp/glm53_car"
#   fast:  docker exec glm53-2bit-claude50 sh -c "echo 3 1 0.15 1 1 0 0.30 > /tmp/glm53_car"
set -euo pipefail
cd /home/isa/Experiments/glm53-flash-fit/claude-opt
NV2_PY=$PWD/nv2_claude50.py MEM=26g ./launch_exp.sh glm53-2bit-claude50 \
  "--restart unless-stopped -v $PWD/car_kernel_claude50:/opt/glm53/car_kernel:ro -e GLM53_WARM_ITERS=30 -e GLM53_MAIN_GPU0_BUDGET=5.2 -e GLM53_NV_RAM_GB_0=16.5 -e GLM53_NV_RAM_GB_1=1 -e GLM53_NV_CTL_CPU_0=2 -e GLM53_NV_CTL_CPU_1=4 -e GLM53_NV_READER_CPUS_0=12-15 -e GLM53_NV_READER_CPUS_1=8-11 -e GLM53_NV_PREFETCH=1 -e GLM53_EC_STAGE_MIN=4096 -e GLM53_CAR=3 -e GLM53_CAR_KEEP=1 -e GLM53_CAR_THRESH=0.15 -e GLM53_CAR_RENORM=1 -e GLM53_CAR_SMALL=1 -e GLM53_CAR_PF=0 -e GLM53_CAR_TNV=0.30"
