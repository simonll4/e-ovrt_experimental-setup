#!/usr/bin/env bash
set -euo pipefail

ROOT="${EOVRT_T1_ROOT:?set EOVRT_T1_ROOT to the remote T1 working directory}"
FULL_JOB_ID="${EOVRT_FULL_JOB_ID:?set EOVRT_FULL_JOB_ID to the T1 full Slurm job}"
CLUSTER="${EOVRT_T1_SLURM_CLUSTER:-ivb}"
BUNDLE="${ROOT}/bundle"
IMAGE="${ROOT}/images/eovrt-t1-yoloe.sif"
SMOKE_GATE="${ROOT}/smoke-ready.json"
RUN_MANIFEST="${ROOT}/runs/full-${FULL_JOB_ID}/eovrt_run_manifest.json"
OUTPUT="${ROOT}/full-ready-${FULL_JOB_ID}.json"

test -d "${BUNDLE}"
test -f "${IMAGE}"
test -f "${SMOKE_GATE}"
test -f "${RUN_MANIFEST}"
test ! -e "${OUTPUT}"

state="$(sacct -M "${CLUSTER}" -X -j "${FULL_JOB_ID}" --format=State -n -P | head -n 1)"
if [[ "${state}" != "COMPLETED" ]]; then
    echo "full T1 ${FULL_JOB_ID} is not COMPLETED: ${state}" >&2
    exit 2
fi

apptainer exec \
    --cleanenv \
    --env PYTHONDONTWRITEBYTECODE=1 \
    --bind "${BUNDLE}:/workspace:ro" \
    "${IMAGE}" \
    python /workspace/scripts/verify_t1_bundle.py /workspace
apptainer exec \
    --cleanenv \
    --env PYTHONDONTWRITEBYTECODE=1 \
    --bind "${BUNDLE}:/workspace:ro,${SMOKE_GATE}:/smoke-ready.json:ro,${IMAGE}:/image.sif:ro" \
    "${IMAGE}" \
    python /workspace/scripts/verify_t1_smoke_gate.py \
        --bundle /workspace \
        --image /image.sif \
        --gate /smoke-ready.json
apptainer exec \
    --cleanenv \
    --env PYTHONDONTWRITEBYTECODE=1 \
    --bind "${ROOT}:/t1" \
    "${IMAGE}" \
    python /t1/bundle/scripts/audit_t1_full.py \
        --bundle /t1/bundle \
        --image /t1/images/eovrt-t1-yoloe.sif \
        --run-manifest "/t1/runs/full-${FULL_JOB_ID}/eovrt_run_manifest.json" \
        --job-id "${FULL_JOB_ID}" \
        --output "/t1/full-ready-${FULL_JOB_ID}.json"
echo "T1_FULL_FINALIZE_OK job_id=${FULL_JOB_ID} output=${OUTPUT}"
