# Pesos base locales

Inputs de entrenamiento materializados por tarea y excluidos de Git. No copiar aquí pesos del
media-plane sin emitir antes un manifiesto que registre origen, licencia, tamaño y SHA-256.

T1 usa `manifests/t1_base_weights.json` y se materializa con
`scripts/stage_t1_base_assets.py`; el script rehúsa sobrescribir y comprueba la copia por hash.
