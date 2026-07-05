# Plataforma E-OVRT — deploy integral (DBE single-host)

Consola web + fleet de instancias del servicio media-plane (una por modelo, mismo
image, distinto `EOVRT_MODEL_REF`). Las instancias arrancan **apagadas** (profile
`models`); se encienden/apagan desde la página **Plataforma** de la consola, con la
política *una activa a la vez* (switch atómico).

## Bootstrap (una vez)

```bash
cp .env.example .env                # ajustar EOVRT_WORKSPACE (raíz absoluta del workspace)
docker compose build                # imágenes eovrt/media-plane + eovrt/console (lento la 1ª vez)
docker compose up -d console        # solo la consola; el fleet lo maneja ella
```

Abrir http://localhost:8090 → página **Plataforma** → Activar `mp-mock` (o un modelo).
Requisitos en el host: pesos en `e-ovrt_media-plane/models/` (`make download-models`),
`nvidia-container-toolkit` para instancias GPU.

## Smoke de aceptación

1. `docker compose up -d console` → http://localhost:8090 responde y `/platform` lista el fleet.
2. Activar `mp-mock` → pasa a TARGET ready; lanzar una corrida `demo_v2` corta → succeeded.
3. Activar `mp-gdino-tiny` (apaga mock solo) → correr BENCH corto (`bench_v2_test`,
   `max_units` 10) → Evaluar → métricas visibles.
4. `docker compose stop` para bajar todo.

**Ejecutado y verificado (2026-07-05):** imágenes `eovrt/media-plane:latest` (13.2GB) y
`eovrt/console:latest` (399MB) construidas; consola healthy, `/api/platform/instances`
listó las 7 instancias (absent, sin target); `mp-mock` activado → run `demo_v2` (5 imgs)
succeeded; switch a `mp-gdino-tiny` (apagó mock automático) → BENCH `bench_v2_test`
(10 imgs, cuda) succeeded → evaluate → mAP50=0.6762 (person 0.82, helmet 0.82, vest 0.52,
bare_head 0.55; n_gt en decenas, no las 196 imgs completas del split) → `docker compose
stop` dejó todo `Exited` y los puertos 8080/8090 libres. Detalle en
`.superpowers/sdd/progress-plataforma-docker.md` (Task 10).

## Operación

- La consola ejecuta `docker compose --project-name eovrt up -d --no-build <instancia>` /
  `stop` contra este directorio (montado en `/repo/infra/platform`). El `.env` con
  `EOVRT_WORKSPACE` viaja con el directorio: **paths absolutos de host**, necesarios
  porque compose corre dentro del contenedor de la consola pero los binds los resuelve
  el daemon en el host.
- `runs/` es compartido entre TODAS las instancias: historial y compare cross-model
  completos desde cualquier target.
- Cambiar de modelo NO recarga in-process (Spec A): siempre es stop + up + carga.

## Seguridad

El socket de Docker montado en la consola es **root-equivalente en el host**. Aceptado
para este despliegue de laboratorio (single-user, sin exposición externa). Mitigación:
el BFF solo ejecuta 3 verbos compose con nombres validados contra el fleet declarado.
No exponer el puerto 8090 fuera del host sin revisar esto.
