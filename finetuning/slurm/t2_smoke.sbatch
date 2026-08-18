#!/usr/bin/env bash
#SBATCH --job-name=eovrt-t2-smoke
#SBATCH --partition=short
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --gres=gpu:1
# T2 hace backprop sobre 10,35 M de parámetros (T1 sólo 3.096), así que pide más que
# los 16 GB del smoke de T1: 24 GB deja margen sin monopolizar el nodo.
#SBATCH --mem=24G
# El smoke es 1 época sobre fraction=0.05 (~147 imgs). El full de T1 tardó 13 min con
# 10 épocas completas; 20 min acá es margen amplio, no expectativa.
#SBATCH --time=00:20:00
#SBATCH --no-requeue
#SBATCH --output=t2-smoke-%j.out
#SBATCH --error=t2-smoke-%j.err

set -euo pipefail
bash "${EOVRT_T2_ROOT:?}/bundle/slurm/run_t2_job.sh" smoke
