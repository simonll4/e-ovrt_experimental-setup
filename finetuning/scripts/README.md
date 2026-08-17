# Scripts

Fuente canónica de preparación, entrenamiento, evaluación y verificación T1. Los scripts
rechazan inventarios extra, perfiles desviados, vocabulario reordenado y cualquier optimizador
distinto de la firma congelada de 12 tensores/3.096 parámetros. El smoke técnico y la
autorización científica del full son artefactos independientes; ningún script de cierre del
smoke envía las diez épocas.

Los generadores históricos de `e-ovrt_datasets/main` se usan sólo como referencia para
trazabilidad y exportación. El builder vigente debe operar sobre `canonical_v2`, agrupar por
linaje/duplicado perceptual, validar disjunción con `bench_v3` y producir el split derivado sin
modificar datasets fuente.

## Dataset `finetuning_v1`

```bash
python3 finetuning/scripts/audit_finetuning_v1.py
python3 finetuning/scripts/build_finetuning_v1.py
```

El auditor es la única implementación de hashes y agrupación. Emite el inventario que consume
el builder, comprobando antes el SHA-256 congelado de `bench_v3`. El builder sólo produce un
manifiesto `train`/`val`; la materialización de imágenes corresponde a T-FT-014.

El stem Roboflow se conserva como `source_key`. En PPE, donde esos nombres pueden reutilizarse,
el auditor lo refina a un `lineage_id` mediante similitud visual. Se selecciona una representante
por linaje PPE; las cinco augmentaciones documentadas de cada fuente CSS se conservan juntas.

Instalar la dependencia local del auditor con
`python3 -m pip install -r finetuning/requirements-audit.txt`. Ambos comandos aceptan rutas por
CLI y descubren el repo hermano de datasets sin codificar rutas personales.

## Cierre remoto del smoke

`watch_finalize_t1_smoke_mendieta.sh` espera el estado terminal desde una sesión `tmux` liviana
del login. Sólo ante `COMPLETED` delega en `finalize_t1_smoke_mendieta.sh`, que audita hashes y
checkpoints, emite `smoke-ready.json`, activa el bundle final y ejecuta `sbatch --test-only` para
el full. Ninguno de los dos scripts envía el entrenamiento de 10 épocas.

`submit_t1_full_mendieta.sh` es la única ruta de envío manual: exige el gate técnico y
`full-authorization.json`, fija el cluster `ivb`, evita duplicados y deja recibo. Los scripts
`watch_finalize_t1_full_mendieta.sh`/`finalize_t1_full_mendieta.sh` sólo monitorean, auditan y
sellan un full ya enviado. `create_t1_source_snapshot.py` genera la procedencia determinística
desde un inventario explícito y rechaza artefactos pesados, symlinks, ignorados y credenciales.
