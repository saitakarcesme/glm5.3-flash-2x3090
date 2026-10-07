#!/usr/bin/env bash
# Experiment launcher: identical to dual/launch_final21.sh except container name, restart policy and extra -e/args.
# usage: launch_exp.sh NAME "-e K=V -e K2=V2" ["extra serve.py args"]
set -euo pipefail
NAME=$1; EXTRA_ENV=${2:-}; EXTRA_ARGS=${3:-}
ROOT=/home/isa/Experiments/glm53-flash-fit/2.05bpw
IMG=ghcr.io/0xsero/glm53-flash-offload@sha256:82eef823f95b89fcb14b8379d45315d3a632aaa054fb04e3418b62a3ec2ff1ff
D=/home/isa/Experiments/glm53-flash-fit/dual
NV2=${NV2_PY:-$D/nv2.py}
# shellcheck disable=SC2086
docker run -d --name "$NAME" --gpus all \
  --memory ${MEM:-24g} --memory-swap ${MEM:-24g} --shm-size 1g --ulimit memlock=-1 \
  -p 127.0.0.1:30270:30000 \
  -e GLM53_MAIN_GPU0_BUDGET=4.5 -e GLM53_MODE=nvme-exact -e GLM53_MTP_DUAL=1 -e GLM53_NV_RAM_GB=${RAM_GB:-6} -e GLM53_NV_PF_RING=96 \
  -e GLM53_MAIN_CPUS=0 -e GLM53_NV_CTL_CPU=1 -e GLM53_NV_READER_CPUS=12-15 \
  -e GLM53_NV_CPU_CPUS=2-11 -e GLM53_NV_THREADS=4 \
  -e GLM53_EC_STAGE_GB=1.8 -e GLM53_EC_MAX_SLOTS=3200 \
  -e MAX_JOBS=1 -e GLM53_MODEL_DOWNLOAD=0 -e GLM53_NV_STORE=/nvx/glm53_flash_exl3_2.05bpw_experts.bin \
  $EXTRA_ENV \
  -v $NV2:/opt/glm53/glm53/nv2.py:ro -v "${SERVE_PY:-$D/serve.py}:/opt/glm53/glm53/serve.py:ro" -v "$D/expert_cache.py:/opt/glm53/glm53/expert_cache.py:ro" \
  -v "${KDIR:-$D/kernels}:/opt/glm53/dual/kernels:ro" -v "${BDIR:-$D/build}/nv2_dual_0:/opt/glm53/build/nv2_dual_0" -v "${BDIR:-$D/build}/nv2_dual_1:/opt/glm53/build/nv2_dual_1" \
  -v "/home/isa/Experiments/glm53-flash-fit/entrypoint_llmrig.sh:/opt/glm53/docker/entrypoint.sh:ro" -v "$ROOT/models:/models:ro" -v "$ROOT/nvme:/nvx:ro" \
  "$IMG" -cs 8192 -rcs 0.5 -chunk_size 1024 --max-batch-size 1 -mtp -ndt 1 $EXTRA_ARGS
for i in $(seq 1 120); do
  if curl -sf --max-time 5 http://127.0.0.1:30270/v1/models >/dev/null; then echo "READY after $((i*5))s"; exit 0; fi
  if [ "$(docker inspect -f '{{.State.Running}}' "$NAME")" != true ]; then echo "DIED"; docker logs --tail 40 "$NAME"; exit 1; fi
  sleep 5
done
echo TIMEOUT; exit 1
