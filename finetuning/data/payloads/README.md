# Payloads locales

Bundles materializados para transportar al clúster. Su contenido está ignorado por Git. El
payload T1 contiene sólo las filas `train`/`val` aprobadas de `finetuning_v1`, derivadas
de CSS + PPE Siabar, y acompañarse con un manifiesto versionado en `../../manifests/`.
`bench_v3`, CHV, SHEL5K y los linajes excluidos no forman parte del bundle.

Se materializa y verifica con `scripts/materialize_t1_payload.py`: 2.946 train, 483 val, copias
reales (sin symlinks), `payload.json` y `payload.sha256`.
