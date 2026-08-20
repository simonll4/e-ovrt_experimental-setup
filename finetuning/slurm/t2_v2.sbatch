#!/usr/bin/env bash
#SBATCH --job-name=eovrt-t2-v2
#SBATCH --partition=multi
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --gres=gpu:1
#SBATCH --mem=60G
# Techo de 60 épocas a ~1,7 min/época (medido en 1167864) ≈ 1h43m; patience=15 puede
# parar mucho antes. 4h da margen amplio sin monopolizar el nodo. --no-requeue: un
# timeout mata la corrida sin retorno, así que el margen es deliberado.
#SBATCH --time=04:00:00
#SBATCH --no-requeue
#SBATCH --output=t2-v2-%j.out
#SBATCH --error=t2-v2-%j.err

set -euo pipefail
bash "${EOVRT_T2_ROOT:?}/bundle_v2/slurm/run_t2_v2_job.sh"
