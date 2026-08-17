#!/usr/bin/env bash
set -euo pipefail

# Lightweight login-node watcher. It never requests a GPU or submits a job.
ROOT="${EOVRT_T1_ROOT:?set EOVRT_T1_ROOT to the remote T1 working directory}"
FULL_JOB_ID="${EOVRT_FULL_JOB_ID:?set EOVRT_FULL_JOB_ID to the T1 full Slurm job}"
CLUSTER="${EOVRT_T1_SLURM_CLUSTER:-ivb}"
INTERVAL_SECONDS="${EOVRT_WATCH_INTERVAL_SECONDS:-60}"
LOG="${ROOT}/finalize-full-watch-${FULL_JOB_ID}.log"

exec >"${LOG}" 2>&1
echo "watch_started=$(date --iso-8601=seconds)"
echo "full_job_id=${FULL_JOB_ID}"
echo "slurm_cluster=${CLUSTER}"

while squeue -M "${CLUSTER}" -h -j "${FULL_JOB_ID}" | grep -q .; do
    sleep "${INTERVAL_SECONDS}"
done

state=""
for _attempt in 1 2 3 4 5; do
    state="$(
        sacct -M "${CLUSTER}" -X -j "${FULL_JOB_ID}" --format=State -n -P \
            | head -n 1
    )"
    [[ -n "${state}" ]] && break
    sleep 5
done
echo "full_state=${state}"
if [[ "${state}" != "COMPLETED" ]]; then
    echo "watch_stopped=$(date --iso-8601=seconds)"
    exit 2
fi

for _attempt in 1 2 3 4 5; do
    test -f "${ROOT}/runs/full-${FULL_JOB_ID}/eovrt_run_manifest.json" && break
    sleep 5
done

EOVRT_T1_ROOT="${ROOT}" \
EOVRT_FULL_JOB_ID="${FULL_JOB_ID}" \
EOVRT_T1_SLURM_CLUSTER="${CLUSTER}" \
bash "${ROOT}/bundle/scripts/finalize_t1_full_mendieta.sh"
echo "watch_completed=$(date --iso-8601=seconds)"
