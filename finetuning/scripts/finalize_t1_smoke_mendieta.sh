#!/usr/bin/env bash
set -euo pipefail

ROOT="${EOVRT_T1_ROOT:?set EOVRT_T1_ROOT to the remote T1 working directory}"
SMOKE_JOB_ID="${EOVRT_SMOKE_JOB_ID:?set EOVRT_SMOKE_JOB_ID to the successful smoke job}"
SMOKE_CLUSTER="${EOVRT_T1_SLURM_CLUSTER:-ivb}"
CURRENT_BUNDLE="${ROOT}/bundle"
READY_BUNDLE="${ROOT}/bundle-ready"
ARCHIVED_BUNDLE="${ROOT}/bundle-smoke-${SMOKE_JOB_ID}"
IMAGE="${ROOT}/images/eovrt-t1-yoloe.sif"
RUN_MANIFEST="${ROOT}/runs/smoke-${SMOKE_JOB_ID}/eovrt_run_manifest.json"
SMOKE_HASH_MANIFEST="${ROOT}/smoke-${SMOKE_JOB_ID}.bundle.sha256"
SMOKE_GATE="${ROOT}/smoke-ready.json"
TECHNICAL_MARKER="${ROOT}/technical-smoke-ready.txt"

test -d "${CURRENT_BUNDLE}"
test -d "${READY_BUNDLE}"
test -f "${IMAGE}"
test -f "${RUN_MANIFEST}"
test -f "${SMOKE_HASH_MANIFEST}"
test ! -e "${ARCHIVED_BUNDLE}"
test ! -e "${SMOKE_GATE}"
test ! -e "${TECHNICAL_MARKER}"

state="$(sacct -M "${SMOKE_CLUSTER}" -X -j "${SMOKE_JOB_ID}" --format=State -n -P | head -n 1)"
if [[ "${state}" != "COMPLETED" ]]; then
    echo "smoke ${SMOKE_JOB_ID} is not COMPLETED: ${state}" >&2
    exit 2
fi

(
    cd "${READY_BUNDLE}"
    sha256sum --quiet -c bundle.sha256
)
(
    cd "${ROOT}/images"
    sha256sum --quiet -c eovrt-t1-yoloe.sif.sha256
)

apptainer exec \
    --cleanenv \
    --env PYTHONDONTWRITEBYTECODE=1 \
    --bind "${ROOT}:/t1" \
    "${IMAGE}" \
    python /t1/bundle-ready/scripts/prepare_t1_smoke_gate.py \
        --bundle /t1/bundle-ready \
        --image /t1/images/eovrt-t1-yoloe.sif \
        --run-manifest "/t1/runs/smoke-${SMOKE_JOB_ID}/eovrt_run_manifest.json" \
        --smoke-bundle-hash-manifest "/t1/smoke-${SMOKE_JOB_ID}.bundle.sha256" \
        --output /t1/smoke-ready.json

apptainer exec \
    --cleanenv \
    --env PYTHONDONTWRITEBYTECODE=1 \
    --bind "${ROOT}:/t1" \
    "${IMAGE}" \
    python /t1/bundle-ready/scripts/verify_t1_smoke_gate.py \
        --bundle /t1/bundle-ready \
        --image /t1/images/eovrt-t1-yoloe.sif \
        --gate /t1/smoke-ready.json

mv "${CURRENT_BUNDLE}" "${ARCHIVED_BUNDLE}"
if ! mv "${READY_BUNDLE}" "${CURRENT_BUNDLE}"; then
    mv "${ARCHIVED_BUNDLE}" "${CURRENT_BUNDLE}"
    exit 3
fi

full_test="$(
    EOVRT_T1_ROOT="${ROOT}" \
    EOVRT_T1_SLURM_CLUSTER="${SMOKE_CLUSTER}" \
    bash "${CURRENT_BUNDLE}/scripts/submit_t1_full_mendieta.sh" TEST_ONLY_T1_10_EPOCHS 2>&1
)"
temporary="${TECHNICAL_MARKER}.tmp"
{
    date --iso-8601=seconds
    echo "status=technical_smoke_ready"
    echo "smoke_job_id=${SMOKE_JOB_ID}"
    echo "slurm_cluster=${SMOKE_CLUSTER}"
    sha256sum "${CURRENT_BUNDLE}/bundle.sha256"
    sha256sum "${SMOKE_GATE}"
    sha256sum "${IMAGE}"
    echo "full_sbatch_test=${full_test}"
} >"${temporary}"
mv "${temporary}" "${TECHNICAL_MARKER}"
echo "T1_FINALIZE_OK smoke_job_id=${SMOKE_JOB_ID}"
