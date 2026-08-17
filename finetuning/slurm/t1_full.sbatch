#!/usr/bin/env bash
#SBATCH --job-name=eovrt-t1-full
#SBATCH --partition=multi
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --gres=gpu:1
#SBATCH --mem=60G
#SBATCH --time=02:00:00
#SBATCH --no-requeue
#SBATCH --output=full-%j.out
#SBATCH --error=full-%j.err

set -euo pipefail
# Safety guard: staging this file does not authorize the 10-epoch run.
bash "${EOVRT_T1_ROOT:?}/bundle/slurm/run_t1_job.sh" full
