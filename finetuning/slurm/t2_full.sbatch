#!/usr/bin/env bash
#SBATCH --job-name=eovrt-t2-full
#SBATCH --partition=multi
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --gres=gpu:1
# T2 hace backprop sobre 10,35 M de parámetros (T1 sólo 3.096). El full de T1 usó 8,43 GB
# de 60; 60 GB deja el mismo margen y no monopoliza el nodo.
#SBATCH --mem=60G
# El full de T1 (10 épocas) tardó 13m08s. T2 mueve mucho más gradiente por paso; 3 h es
# margen amplio, no expectativa. Con --no-requeue: un timeout mata la corrida sin retorno.
#SBATCH --time=03:00:00
#SBATCH --no-requeue
#SBATCH --output=t2-full-%j.out
#SBATCH --error=t2-full-%j.err

set -euo pipefail
bash "${EOVRT_T2_ROOT:?}/bundle/slurm/run_t2_job.sh" full
