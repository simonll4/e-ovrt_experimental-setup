#!/usr/bin/env bash
set -euo pipefail

# Lightweight login-node watcher. It performs no training and requests no GPU.
ROOT="${EOVRT_T1_ROOT:?set EOVRT_T1_ROOT to the remote T1 working directory}"
SMOKE_JOB_ID="${EOVRT_SMOKE_JOB_ID:?set EOVRT_SMOKE_JOB_ID to the smoke job}"
SMOKE_CLUSTER="${EOVRT_T1_SLURM_CLUSTER:-ivb}"
INTERVAL_SECONDS="${EOVRT_WATCH_INTERVAL_SECONDS:-60}"
LOG="${ROOT}/finalize-watch-${SMOKE_JOB_ID}.log"

exec >"${LOG}" 2>&1
echo "watch_started=$(date --iso-8601=seconds)"
echo "smoke_job_id=${SMOKE_JOB_ID}"
echo "slurm_cluster=${SMOKE_CLUSTER}"

while squeue -M "${SMOKE_CLUSTER}" -h -j "${SMOKE_JOB_ID}" | grep -q .; do
    sleep "${INTERVAL_SECONDS}"
done

state=""
for _attempt in 1 2 3 4 5; do
    state="$(
        sacct -M "${SMOKE_CLUSTER}" -X -j "${SMOKE_JOB_ID}" --format=State -n -P \
            | head -n 1
    )"
    [[ -n "${state}" ]] && break
    sleep 5
done
echo "smoke_state=${state}"
if [[ "${state}" != "COMPLETED" ]]; then
    echo "watch_stopped=$(date --iso-8601=seconds)"
    exit 2
fi

for _attempt in 1 2 3 4 5; do
    test -f "${ROOT}/runs/smoke-${SMOKE_JOB_ID}/eovrt_run_manifest.json" && break
    sleep 5
done

EOVRT_T1_ROOT="${ROOT}" \
EOVRT_SMOKE_JOB_ID="${SMOKE_JOB_ID}" \
EOVRT_T1_SLURM_CLUSTER="${SMOKE_CLUSTER}" \
bash "${ROOT}/bundle-ready/scripts/finalize_t1_smoke_mendieta.sh"
echo "watch_completed=$(date --iso-8601=seconds)"
