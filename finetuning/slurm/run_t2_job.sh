#!/usr/bin/env bash
# Runner del job T2 (full fine-tuning con interfaz OV preservada, D-FT-14/D-FT-15).
#
# Espejo de run_t1_job.sh. Dos diferencias deliberadas:
#   - invoca train_t2.py con configs/t2_yoloe26s_full.yaml;
#   - el perfil `full` exige EOVRT_AUTHORIZE_FULL_T2=YES **y** la firma de D-FT-15
#     materializada como t2-authorization.json en la raíz (T-FT-063). El smoke no
#     necesita autorización: no consume el brazo one-shot ni produce cifra citable.
#
# La imagen Apptainer se reutiliza de T1 por defecto (mismo ultralytics 8.4.86): no
# hay razón para construir ni transportar otros 3,5 GB.
set -euo pipefail

PROFILE="${1:?usage: run_t2_job.sh smoke|full}"
if [[ "${PROFILE}" != "smoke" && "${PROFILE}" != "full" ]]; then
    echo "invalid profile: ${PROFILE}" >&2
    exit 2
fi
if [[ "${PROFILE}" == "full" && "${EOVRT_AUTHORIZE_FULL_T2:-}" != "YES" ]]; then
    echo "full T2 is staged but not authorized; set EOVRT_AUTHORIZE_FULL_T2=YES explicitly" >&2
    exit 3
fi

ROOT="${EOVRT_T2_ROOT:?submit with EOVRT_T2_ROOT set to the remote T2 directory}"
BUNDLE="${ROOT}/bundle"
IMAGE="${EOVRT_T2_IMAGE:-${ROOT}/images/eovrt-t1-yoloe.sif}"
RUNS="${ROOT}/runs"
RUNTIME="${ROOT}/runtime/${SLURM_JOB_ID}"
RUN_NAME="${PROFILE}-${SLURM_JOB_ID}"

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

if [[ "${PROFILE}" == "full" ]]; then
    # La puerta de T2 no es un archivo-marcador: es una verificación por hash de que la
    # vara existía antes que el resultado (D-FT-15 firmada, baseline OV congelada, umbral
    # derivado coherente, insumos intactos, smoke técnico COMPLETED). Corre DENTRO del
    # contenedor, como en T1, porque el login tiene Python 3.6.
    apptainer exec \
        --cleanenv \
        --env PYTHONDONTWRITEBYTECODE=1 \
        --bind "${BUNDLE}:/workspace:ro" \
        "${IMAGE}" \
        python /workspace/scripts/verify_t2_authorization.py \
            --protocol /workspace/manifests/t2_yoloe26s_protocol.json \
            --finetuning-root /workspace \
            --experiment-root /workspace
fi

ENV_LOG="${RUNS}/${RUN_NAME}.environment.txt"
{
    date --iso-8601=seconds
    hostname
    echo "profile=${PROFILE}"
    echo "tier=T2"
    echo "slurm_job_id=${SLURM_JOB_ID}"
    echo "slurm_job_name=${SLURM_JOB_NAME}"
    echo "slurm_job_partition=${SLURM_JOB_PARTITION}"
    echo "slurm_job_nodelist=${SLURM_JOB_NODELIST}"
    echo "slurm_cpus_per_task=${SLURM_CPUS_PER_TASK:-}"
    echo "slurm_gpus_on_node=${SLURM_GPUS_ON_NODE:-}"
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
    python /workspace/scripts/train_t2.py \
        --bundle /workspace \
        --config /workspace/configs/t2_yoloe26s_full.yaml \
        --profile "${PROFILE}" \
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
