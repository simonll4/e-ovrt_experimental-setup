#!/usr/bin/env bash
#SBATCH --job-name=eovrt-t1-smoke
#SBATCH --partition=short
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --gres=gpu:1
# El smoke medido alcanzó <6 GB de RAM; 16 GB deja margen sin monopolizar el nodo.
#SBATCH --mem=16G
#SBATCH --time=00:10:00
#SBATCH --no-requeue
#SBATCH --output=smoke-%j.out
#SBATCH --error=smoke-%j.err

set -euo pipefail
bash "${EOVRT_T1_ROOT:?}/bundle/slurm/run_t1_job.sh" smoke
