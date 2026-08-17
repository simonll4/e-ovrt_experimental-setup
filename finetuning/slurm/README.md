# Slurm

Jobs versionados para Mendieta. La imagen se construye una sola vez desde el login con
`scripts/build_t1_image_login.sh`: los nodos de cómputo no alcanzan de forma confiable los
registros OCI. Luego T1 separa smoke y corrida completa; cada job declara recursos, walltime,
logs y salida, y captura versiones, GPU real y variables Slurm relevantes.

El smoke pide 16 GB de RAM y 10 minutos. El primer intento efectivo usó 5,17 GB pero agotó su
límite de 5 minutos esperando que el chequeo AMP descargara `yolo26n.pt` desde un nodo sin red;
el activo ahora viaja dentro del bundle. El job completo conserva
60 GB y está preparado pero exige tanto un `smoke-ready.json` válido como
`EOVRT_AUTHORIZE_FULL_T1=YES`. El operador debe usar `scripts/submit_t1_full_mendieta.sh` con la
confirmación exacta `RUN_T1_10_EPOCHS`; crear o transportar estos archivos no envía las 10 épocas.

El clúster GPU exige al menos una GPU por job, por lo que el postcheck no se somete a Slurm: no
se desperdicia una A30 para calcular hashes. `scripts/watch_finalize_t1_smoke_mendieta.sh` puede
quedar en una sesión `tmux` del login; sólo consulta el estado y, si el smoke termina
`COMPLETED`, audita artefactos, emite el gate, activa el bundle de forma recuperable y prueba el
job completo con `sbatch --test-only`. Nunca invoca el wrapper de envío manual.
