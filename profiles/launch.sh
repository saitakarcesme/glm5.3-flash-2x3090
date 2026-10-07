#!/usr/bin/env bash
# Launch GLM-5.3-Flash (EXL3 2.05 bpw) on 2x RTX 3090 + ~32 GB DDR4 + one NVMe, OpenAI-compatible API on 127.0.0.1:${PORT}.
#
#   profiles/launch.sh fast      # cache-aware routing, ~50-55 tok/s decode, LOSSY (see README "Quality")
#   profiles/launch.sh exact     # bit-exact expert path, ~14 tok/s decode
#
# Both profiles are the same container; the mode can be switched at runtime without a restart:
#   docker exec glm53 sh -c 'echo 0 2 0 1 1 1 > /tmp/glm53_car'          # exact
#   docker exec glm53 sh -c 'echo 3 1 0.15 1 1 0 0.30 > /tmp/glm53_car'  # fast
#
# Required: GLM_MODEL_DIR (turboderp/GLM-5.3-Flash-exl3, branch 2.05bpw) and GLM_STORE_DIR (packed NVMe expert store
# glm53_flash_exl3_2.05bpw_experts.{bin,json}, built once with the upstream image's `pack-store`).
set -euo pipefail
PROFILE=${1:-fast}
HERE=$(cd "$(dirname "$0")/.." && pwd)
: "${GLM_MODEL_DIR:?set GLM_MODEL_DIR to the 2.05bpw EXL3 checkpoint}"
: "${GLM_STORE_DIR:?set GLM_STORE_DIR to the directory holding glm53_flash_exl3_2.05bpw_experts.bin/.json}"
NAME=${NAME:-glm53}
PORT=${PORT:-30270}
CTX=${CTX:-131072}                 # tokens of KV cache (model max 1M; 128k fits with the split below)
CHUNK=${CHUNK:-4096}               # prefill chunk; bigger = faster prefill, more transient VRAM
BUILD=${GLM_BUILD_DIR:-$HERE/.build}
IMG=ghcr.io/0xsero/glm53-flash-offload@sha256:82eef823f95b89fcb14b8379d45315d3a632aaa054fb04e3418b62a3ec2ff1ff
mkdir -p "$BUILD/nv2_dual_0" "$BUILD/nv2_dual_1"

# Layer split: the GPU0 budget (GB of non-expert weights + KV + prefill transient) decides how many MoE layers land on
# GPU0 (PCIe 4.0 x16, 20 GB/s). GPU1 sits on a chipset x4 link (6.4 GB/s), so it gets fewer layers and keeps them
# (almost) fully VRAM-resident. Measured: 8k ctx -> B0 5.2; 128k ctx + 4k chunk -> B0 8.0 gives 27/15.
if [ "$CTX" -le 8192 ]; then B0=${B0:-5.2}; CHUNK=${CHUNK_SMALL:-1024}; else B0=${B0:-8.0}; fi
B1=${B1:-12}

COMMON=(
  -e GLM53_MODE=nvme-exact -e GLM53_MTP_DUAL=1 -e GLM53_MODEL_DOWNLOAD=0 -e MAX_JOBS=1
  -e GLM53_NV_STORE=/nvx/glm53_flash_exl3_2.05bpw_experts.bin
  -e GLM53_MAIN_GPU0_BUDGET="$B0" -e GLM53_MAIN_GPU1_BUDGET="$B1"
  -e GLM53_NV_RAM_GB_0=16.5 -e GLM53_NV_RAM_GB_1=1 -e GLM53_NV_PF_RING=96          # host RAM tier: almost all to GPU0
  -e GLM53_MAIN_CPUS=0 -e GLM53_NV_CTL_CPU_0=2 -e GLM53_NV_CTL_CPU_1=4              # i5-14400F: separate P-cores
  -e GLM53_NV_CTL_CPU=1 -e GLM53_NV_READER_CPUS=12-15 -e GLM53_NV_READER_CPUS_0=12-15 -e GLM53_NV_READER_CPUS_1=8-11
  -e GLM53_NV_CPU_CPUS=2-11 -e GLM53_NV_THREADS=4
  -e GLM53_EC_STAGE_GB=1.8 -e GLM53_EC_MAX_SLOTS=3200 -e GLM53_EC_STAGE_MIN=4096 -e GLM53_WARM_ITERS=30
  -e GLM53_NV_PREFETCH=1
)
case "$PROFILE" in
  fast)  MODE=(-e GLM53_CAR=3 -e GLM53_CAR_KEEP=1 -e GLM53_CAR_THRESH=0.15 -e GLM53_CAR_RENORM=1 -e GLM53_CAR_SMALL=1
               -e GLM53_CAR_PF=0 -e GLM53_CAR_TNV=0.30) ;;
  exact) MODE=(-e GLM53_CAR=0) ;;
  *) echo "profile must be fast or exact" >&2; exit 1 ;;
esac

docker run -d --name "$NAME" --restart unless-stopped --gpus all \
  --memory 26g --memory-swap 26g --shm-size 1g --ulimit memlock=-1 \
  -p 127.0.0.1:"$PORT":30000 \
  "${COMMON[@]}" "${MODE[@]}" \
  -v "$HERE/runtime/nv2.py:/opt/glm53/glm53/nv2.py:ro" \
  -v "$HERE/runtime/serve_claude.py:/opt/glm53/glm53/serve.py:ro" \
  -v "$HERE/runtime/expert_cache.py:/opt/glm53/glm53/expert_cache.py:ro" \
  -v "$HERE/runtime/base/kernels:/opt/glm53/dual/kernels:ro" \
  -v "$HERE/runtime/car_kernel:/opt/glm53/car_kernel:ro" \
  -v "$BUILD/nv2_dual_0:/opt/glm53/build/nv2_dual_0" -v "$BUILD/nv2_dual_1:/opt/glm53/build/nv2_dual_1" \
  -v "$HERE/runtime/base/entrypoint.sh:/opt/glm53/docker/entrypoint.sh:ro" \
  -v "$GLM_MODEL_DIR:/models:ro" -v "$GLM_STORE_DIR:/nvx:ro" \
  "$IMG" -cs 8192 -rcs 0.5 -chunk_size 1024 --max-batch-size 1 -mtp -ndt 1 -cs "$CTX" -chunk_size "$CHUNK"

echo "waiting for the API (first start compiles two extensions + the CAR kernel, ~2-3 min)..."
for i in $(seq 1 120); do
  if curl -sf --max-time 5 "http://127.0.0.1:$PORT/v1/models" >/dev/null; then echo "ready: http://127.0.0.1:$PORT/v1 (model glm-5.3-flash)"; exit 0; fi
  [ "$(docker inspect -f '{{.State.Running}}' "$NAME")" = true ] || { docker logs --tail 40 "$NAME"; exit 1; }
  sleep 5
done
echo "timeout"; exit 1
