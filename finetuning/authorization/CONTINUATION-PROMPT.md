# Contexto — ejecutar T1 full en Mendieta

Ayudame a ejecutar y monitorear por SSH el entrenamiento **T1** (fine-tuning YOLOE-26s,
linear probing, 12 tensores/3.096 params, 10 épocas) del proyecto E-OVRT-VDP en el
clúster Mendieta (CCAD-UNC).

**Runbook completo, ya escrito:** `e-ovrt_experimental-setup/finetuning/authorization/README.md`
— leelo entero, es la fuente de verdad de los comandos. Este mensaje es sólo contexto.

**Estado:** paquete de evidencia (`authorization/evidence/`) preparado y ensayado
localmente (prepare→gates=7, verify→exit 0, prueba negativa de hash OK), pero **nada
subido a Mendieta todavía**. Cero jobs `eovrt-t1-full` enviados. El smoke técnico
(`1166583`) ya está verde allá.

**Qué mide T1:** si el ajuste rescata `bare_head` (hoy AP50 0,000 en la baseline
zero-shot) sin perder más de 10% en person/helmet/vest — márgenes firmados en
D-FT-12, no negociables después del resultado. Un NO-GO es resultado válido.

**Cuidados clave:**
- Verificar que `$EOVRT_T1_ROOT/full-submission.txt` NO exista antes de arrancar (si
  existe, ya se envió antes — parar y avisarme).
- Correr siempre `TEST_ONLY_T1_10_EPOCHS` antes de `RUN_T1_10_EPOCHS`; confirmame
  explícitamente antes de ejecutar el `RUN` real (gasta turno de GPU real).
- Los scripts de `prepare`/`verify` de la autorización corren **dentro del contenedor
  Apptainer**, no en el login (Python 3.6 ahí, scripts necesitan 3.7+).
- No regenerar `smoke-ready.json` localmente (no es determinista, ya existe en el
  clúster).

**Al terminar el job**, juntame: `job_id` + salida de `sacct -j`, `full-submission.txt`,
logs del job, y los checkpoints `best.pt`/`last.pt` (este último nunca se evalúa como
candidato).

Más contexto si hace falta: `docs/operacion/117` y `120`, `docs/decisiones/adr-017`.
