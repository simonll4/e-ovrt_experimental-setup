#!/usr/bin/env bash
# Runner de la continuación T2 (D-FT-16), desde el peso base. Espejo de run_t2_job.sh, sin la puerta de
# autorización de bench (esta corrida no toca bench_v3/COCO, sólo entrena).
set -euo pipefail

ROOT="${EOVRT_T2_ROOT:?submit with EOVRT_T2_ROOT set to the remote T2 directory}"
BUNDLE="${ROOT}/bundle_v2"
IMAGE="${EOVRT_T2_IMAGE:-${ROOT}/images/eovrt-t1-yoloe.sif}"
RUNS="${ROOT}/runs_v2"
RUNTIME="${ROOT}/runtime_v2/${SLURM_JOB_ID}"
RUN_NAME="v2-${SLURM_JOB_ID}"

test -f "${IMAGE}"
test -f "${BUNDLE}/bundle.sha256"
mkdir -p \
    "${RUNS}" \
    "${RUNTIME}/home" \
    "${RUNTIME}/cache" \
    "${RUNTIME}/mpl" \
    "${RUNTIME}/ultralytics"
cd "${BUNDLE}"
sha256sum --quiet -c bundle.sha256

ENV_LOG="${RUNS}/${RUN_NAME}.environment.txt"
{
    date --iso-8601=seconds
    hostname
    echo "run_name=${RUN_NAME}"
    echo "amendment=D-FT-16"
    echo "slurm_job_id=${SLURM_JOB_ID}"
    echo "slurm_job_partition=${SLURM_JOB_PARTITION}"
    echo "slurm_job_nodelist=${SLURM_JOB_NODELIST}"
    echo "slurm_cluster=${EOVRT_T2_SLURM_CLUSTER:-ivb}"
    sha256sum "${IMAGE}"
    apptainer --version
    nvidia-smi
} >"${ENV_LOG}" 2>&1

IMAGE_SHA256="$(sha256sum "${IMAGE}" | awk '{print $1}')"
set +e
apptainer exec \
    --nv \
    --cleanenv \
    --home "${RUNTIME}/home" \
    --pwd /workspace/weights/base \
    --bind "${BUNDLE}:/workspace:ro,${RUNS}:/runs,${RUNTIME}:/runtime" \
    --env "XDG_CACHE_HOME=/runtime/cache" \
    --env "MPLCONFIGDIR=/runtime/mpl" \
    --env "YOLO_CONFIG_DIR=/runtime/ultralytics" \
    --env "TORCH_HOME=/runtime/cache/torch" \
    --env "PYTHONDONTWRITEBYTECODE=1" \
    --env "EOVRT_IMAGE_SHA256=${IMAGE_SHA256}" \
    --env "SLURM_JOB_ID=${SLURM_JOB_ID}" \
    --env "SLURM_JOB_NAME=${SLURM_JOB_NAME}" \
    --env "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST}" \
    --env "SLURM_JOB_PARTITION=${SLURM_JOB_PARTITION}" \
    --env "SLURM_CPUS_PER_TASK=${SLURM_CPUS_PER_TASK:-}" \
    --env "SLURM_GPUS_ON_NODE=${SLURM_GPUS_ON_NODE:-}" \
    "${IMAGE}" \
    python /workspace/scripts/train_t2_v2.py \
        --bundle /workspace \
        --config /workspace/configs/t2_yoloe26s_full_v2.yaml \
        --output /runs \
        --run-name "${RUN_NAME}"
RETURN_CODE=$?
set -e

{
    date --iso-8601=seconds
    echo "return_code=${RETURN_CODE}"
    scontrol show job "${SLURM_JOB_ID}" || true
} >>"${ENV_LOG}" 2>&1
exit "${RETURN_CODE}"
