#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-}"
if [[ "${MODE}" != "RUN_T1_10_EPOCHS" && "${MODE}" != "TEST_ONLY_T1_10_EPOCHS" ]] \
    || [[ "$#" -ne 1 ]]; then
    echo "usage: EOVRT_T1_ROOT=<remote-root> $0 RUN_T1_10_EPOCHS|TEST_ONLY_T1_10_EPOCHS" >&2
    exit 2
fi

ROOT="${EOVRT_T1_ROOT:?set EOVRT_T1_ROOT to the remote T1 working directory}"
CLUSTER="${EOVRT_T1_SLURM_CLUSTER:-ivb}"
BUNDLE="${ROOT}/bundle"
IMAGE="${ROOT}/images/eovrt-t1-yoloe.sif"
IMAGE_HASH="${ROOT}/images/eovrt-t1-yoloe.sif.sha256"
SMOKE_GATE="${ROOT}/smoke-ready.json"
TECHNICAL_MARKER="${ROOT}/technical-smoke-ready.txt"
FULL_AUTHORIZATION="${ROOT}/full-authorization.json"
SUBMISSION_RECEIPT="${ROOT}/full-submission.txt"
SUBMISSION_LOCK="${ROOT}/.submit-t1-full.lock"

if ! mkdir "${SUBMISSION_LOCK}" 2>/dev/null; then
    echo "another T1 full submission is already being prepared: ${SUBMISSION_LOCK}" >&2
    exit 4
fi
trap 'rmdir "${SUBMISSION_LOCK}" 2>/dev/null || true' EXIT

if [[ -e "${SUBMISSION_RECEIPT}" ]]; then
    echo "T1 full was already submitted; refusing to submit again: ${SUBMISSION_RECEIPT}" >&2
    exit 5
fi
active_full="$(squeue -M "${CLUSTER}" -u "${USER}" -h -o '%i|%j|%T' | awk -F'|' '$2 == "eovrt-t1-full" {print}')"
if [[ -n "${active_full}" ]]; then
    echo "an eovrt-t1-full job already exists on ${CLUSTER}: ${active_full}" >&2
    exit 6
fi

test -f "${BUNDLE}/bundle.sha256"
test -f "${IMAGE}"
test -f "${IMAGE_HASH}"
test -f "${SMOKE_GATE}"
if [[ "${MODE}" == "RUN_T1_10_EPOCHS" ]]; then
    test -f "${TECHNICAL_MARKER}"
    test -f "${FULL_AUTHORIZATION}"
    grep -qx "status=technical_smoke_ready" "${TECHNICAL_MARKER}"
    command -v tmux >/dev/null
fi
(
    cd "${BUNDLE}"
    sha256sum --quiet -c bundle.sha256
)
(
    cd "${ROOT}/images"
    sha256sum --quiet -c eovrt-t1-yoloe.sif.sha256
)
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
if [[ "${MODE}" == "RUN_T1_10_EPOCHS" ]]; then
    apptainer exec \
        --cleanenv \
        --env PYTHONDONTWRITEBYTECODE=1 \
        --bind "${BUNDLE}:/workspace:ro,${SMOKE_GATE}:/smoke-ready.json:ro,${ROOT}:/authorization-root:ro" \
        "${IMAGE}" \
        python /workspace/scripts/verify_t1_full_authorization.py \
            --authorization /authorization-root/full-authorization.json \
            --bundle-manifest /workspace/bundle.sha256 \
            --smoke-gate /smoke-ready.json
fi

SBATCH_ARGS=(
    -M "${CLUSTER}"
    --chdir="${ROOT}"
    --export="ALL,EOVRT_T1_ROOT=${ROOT},EOVRT_T1_SLURM_CLUSTER=${CLUSTER},EOVRT_AUTHORIZE_FULL_T1=YES"
)
if [[ "${MODE}" == "TEST_ONLY_T1_10_EPOCHS" ]]; then
    full_test="$(sbatch "${SBATCH_ARGS[@]}" --test-only "${BUNDLE}/slurm/t1_full.sbatch" 2>&1)"
    echo "T1_FULL_TEST_ONLY_OK cluster=${CLUSTER} epochs=10 result=${full_test}"
    exit 0
fi
job_id="$(sbatch "${SBATCH_ARGS[@]}" --parsable "${BUNDLE}/slurm/t1_full.sbatch")"
job_id="${job_id%%;*}"
watcher_session="eovrt-t1-finalize-${job_id}"
temporary="${SUBMISSION_RECEIPT}.tmp"
{
    date --iso-8601=seconds
    echo "status=submitted"
    echo "job_id=${job_id}"
    echo "slurm_cluster=${CLUSTER}"
    echo "epochs=10"
    echo "watcher_session=${watcher_session}"
    sha256sum "${BUNDLE}/bundle.sha256"
    sha256sum "${SMOKE_GATE}"
    sha256sum "${FULL_AUTHORIZATION}"
    sha256sum "${IMAGE}"
} >"${temporary}"
mv "${temporary}" "${SUBMISSION_RECEIPT}"
tmux new-session \
    -d \
    -s "${watcher_session}" \
    "EOVRT_T1_ROOT='${ROOT}' EOVRT_FULL_JOB_ID='${job_id}' EOVRT_T1_SLURM_CLUSTER='${CLUSTER}' bash '${BUNDLE}/scripts/watch_finalize_t1_full_mendieta.sh'"
echo "T1_FULL_SUBMITTED job_id=${job_id} cluster=${CLUSTER} epochs=10 receipt=${SUBMISSION_RECEIPT}"
