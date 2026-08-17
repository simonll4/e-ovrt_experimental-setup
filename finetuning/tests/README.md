# Tests del tooling

Fixtures sintéticas y tests de los scripts de fine-tuning. Deben cubrir como mínimo paths
portables, ids de clase, conteos, colisiones de stems, normalización de linajes Roboflow,
agrupación perceptual, disjunción con el bench, ausencia de symlinks absolutos, manifiestos y
política de selección de checkpoint.

Ejecutar desde la raíz del repositorio:

```bash
python3 -m pytest finetuning/tests -q
```
