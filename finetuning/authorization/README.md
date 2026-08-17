# Paquete de autorización T1 full — runbook para Mendieta

- **Fecha:** 2026-08-15 · **Para:** el paso manual del usuario (T-FT-043).
- **Qué es esto:** la evidencia de las **7 gates** que `full-authorization.json` exige,
  ya reunida, hasheada y **ensayada de punta a punta localmente**. Lo que falta es
  subirla y emitir la autorización en el clúster, donde viven los dos archivos que la
  atan por hash (`smoke-ready.json` y `bundle/bundle.sha256`).
- **Estado del ensayo local (2026-08-15):** `prepare` → `gates=7` · `verify` → `exit 0` ·
  **prueba negativa**: alterando un archivo de evidencia, `verify` falla con
  `evidence hash mismatch for T-FT-005` y vuelve a verde al restaurarlo. El guard es real.

> **Qué NO hace este paquete:** no envía nada, no autoriza nada por sí solo y no toca el
> clúster. Es evidencia + un runbook.

---

## 0. Antes de empezar

**Conexión** (wiki CCAD, *Conexión a un clúster*): no lleva contraseña — autentica con la
clave pública que enviaste al pedir la cuenta. `$USUARIO` es el que te llegó en el mail de
alta.

```bash
ssh $USUARIO@mendieta.ccad.unc.edu.ar
```

Te conectás al **nodo cabecera**: sirve para preparar y encolar, **no** para calcular.

**Dato que sólo vos tenés:** la ruta del directorio de trabajo remoto, la misma que usaste
en el smoke — el `EOVRT_T1_ROOT`. Para encontrarla:

```bash
ls -d ~/*t1* ~/*eovrt* 2>/dev/null
# Debe contener: bundle/  images/  smoke-ready.json  technical-smoke-ready.txt
export EOVRT_T1_ROOT=<esa ruta>
```

**Chequeo de que el punto de partida es el correcto** (todo esto debería existir ya, y
**`full-authorization.json` NO debe existir**):

```bash
cd "$EOVRT_T1_ROOT"
ls -l bundle/bundle.sha256 images/eovrt-t1-yoloe.sif smoke-ready.json technical-smoke-ready.txt
grep -x "status=technical_smoke_ready" technical-smoke-ready.txt   # debe imprimir la línea
ls full-authorization.json full-submission.txt 2>/dev/null         # ambos deben faltar
```

Si `full-submission.txt` existe, **el full ya se envió alguna vez** y el script se negará a
enviar de nuevo (por diseño). Avisame antes de tocar nada.

---

## 1. Subir la evidencia (desde tu máquina, no desde el clúster)

```bash
cd e-ovrt_experimental-setup/finetuning/authorization
rsync -avz evidence/ $USUARIO@mendieta.ccad.unc.edu.ar:"$EOVRT_T1_ROOT"/evidence/
```

`-a` preserva atributos, `-v` muestra el detalle, `-z` comprime en tránsito. Son archivos
JSON chicos: la transferencia es de segundos.

**Verificar que llegó íntegra** (en el clúster):

```bash
cd "$EOVRT_T1_ROOT" && sha256sum -c evidence/../MANIFEST.sha256 2>/dev/null || \
  ( cd "$EOVRT_T1_ROOT" && sha256sum evidence/t1_dft08_decision.json )
```

Si preferís, subí también `MANIFEST.sha256` y corré `sha256sum -c MANIFEST.sha256` desde
`$EOVRT_T1_ROOT`.

---

## 2. Emitir la autorización — **dentro del contenedor**

**Por qué dentro:** el login de Mendieta tiene **Python 3.6**, y el script usa
`from __future__ import annotations` (3.7+). Fuera del contenedor falla. Se usa la misma
imagen Apptainer del smoke, con el mismo patrón que ya usa `submit_t1_full_mendieta.sh`.

Ojo con el bind: acá va **sin `:ro`** en la raíz, porque hay que escribir la salida.

```bash
cd "$EOVRT_T1_ROOT"
apptainer exec \
    --cleanenv \
    --env PYTHONDONTWRITEBYTECODE=1 \
    --bind "$EOVRT_T1_ROOT/bundle:/workspace:ro,$EOVRT_T1_ROOT:/authorization-root" \
    "$EOVRT_T1_ROOT/images/eovrt-t1-yoloe.sif" \
    python /workspace/scripts/prepare_t1_full_authorization.py \
        --approval APPROVE_D_FT_08 \
        --bundle-manifest /workspace/bundle.sha256 \
        --smoke-gate /authorization-root/smoke-ready.json \
        --evidence T-FT-005=evidence/t1_dft08_decision.json \
        --evidence T-FT-023=evidence/t1_source_provenance_attestation.json \
        --evidence T-FT-026=technical-smoke-ready.txt \
        --evidence T-FT-030=evidence/t1_smoke_1166583_media_plane.json \
        --evidence T-FT-031=evidence/t1_yoloe26s_bench_v3_protocol.json \
        --evidence T-FT-032=evidence/t1_baseline_eval/artifact.sha256 \
        --evidence T-FT-042R=smoke-ready.json \
        --output /authorization-root/full-authorization.json
```

**Salida esperada:** `full_authorization_created=... gates=7`

Notas:
- El token `APPROVE_D_FT_08` es **exacto**; cualquier otro string y el script aborta.
- Las rutas de `--evidence` son **relativas a la raíz de autorización** (`$EOVRT_T1_ROOT`).
- Si `full-authorization.json` ya existe, **se niega a pisarlo**. Para rehacerlo hay que
  borrarlo a mano y volver a emitir.

---

## 3. Ensayo sin enviar nada — **hacé esto primero**

```bash
cd "$EOVRT_T1_ROOT"
EOVRT_T1_ROOT="$EOVRT_T1_ROOT" bundle/scripts/submit_t1_full_mendieta.sh TEST_ONLY_T1_10_EPOCHS
```

Valida bundle, imagen, hashes y el gate del smoke, y corre `sbatch --test-only` — que según
la wiki *"verifica si el script es válido y estima cuándo podría ejecutarse, pero **no** lo
pone en la cola"*. **No envía el entrenamiento.**

> `TEST_ONLY` **no** verifica la autorización (esa comprobación corre sólo en modo `RUN`).
> Si querés validarla por separado antes del envío real, corré a mano el
> `verify_t1_full_authorization.py` con el mismo bind `:ro` que usa el submit.

---

## 4. El envío real

```bash
cd "$EOVRT_T1_ROOT"
EOVRT_T1_ROOT="$EOVRT_T1_ROOT" bundle/scripts/submit_t1_full_mendieta.sh RUN_T1_10_EPOCHS
```

Antes de mandar nada, el script exige y comprueba, en orden: bundle + imagen + hashes ·
`smoke-ready.json` · `technical-smoke-ready.txt` con `status=technical_smoke_ready` ·
**la autorización, verificada dentro del contenedor** · que no exista `full-submission.txt` ·
que no haya otro `eovrt-t1-full` en cola · y toma un lock para que no haya envíos
simultáneos. Recién entonces hace `sbatch`.

Deja **recibo** en `full-submission.txt` con el `job_id`.

---

## 5. Seguirlo

La partición es **`multi`**, que en Mendieta admite **hasta 2 días** — el pedido es de 2 h de
walltime, así que entra con margen. El costo estimado real es **≈16 min** de punto central
(30–45 min prudente): las 2 h son margen, no expectativa.

```bash
squeue --me                      # PD = pendiente, R = corriendo, CG = terminando
scontrol show job $JOBID         # confirma que encoló con los recursos pedidos
sacct -X -S now-4weeks           # historial
```

Si el `squeue` muestra `PD` con `(Priority)` o `(Resources)`, es cola normal — no es un error.

Para no depender de la sesión SSH, la wiki recomienda **tmux** (ya instalado):

```bash
tmux            # abrir sesión
# Ctrl+b, luego d   -> desconectarse dejándola viva
tmux a          # volver a entrar
```

> **Cuidado con `/scratch`:** es local a cada nodo de cómputo y **se borra al terminar el
> trabajo**. Nada que haya que conservar puede quedar sólo ahí.

---

## 6. Cuando termine, mandame esto

Con estos cuatro datos sigo yo la cadena (T-FT-044 → 050 → 051 → 052):

1. El `job_id` y la salida de `sacct -j $JOBID`.
2. `full-submission.txt`.
3. Los logs del job y el directorio de salida del entrenamiento.
4. El **checkpoint** `best.pt` (y `last.pt`, que se conserva para auditoría y **nunca** se
   evalúa como segundo candidato).

A partir de ahí: promoción por hash al catálogo `yoloe-26s-ft-t1.yaml` (ya preparado) →
evaluación **única** con `evaluate_t1_bench_v3.py --arm tuned` → aplicar el go/no-go con los
márgenes **ya firmados** (D-FT-12: ΔAP50 ≥ +0,05 **o** rescate de recall <0,1→>0,5;
retención in-domain ≤10 %) → medición pareada de latencia (F-120.1).

---

## Inventario de las 7 gates

| Gate | Significado | Archivo | Origen |
|---|---|---|---|
| **T-FT-005** | `fixed_vocabulary_decision_approved` | `evidence/t1_dft08_decision.json` | **creado en este paquete** — certifica la firma de D-FT-08 del 2026-08-15 y el contrato exacto |
| **T-FT-023** | `provenance_frozen` | `evidence/t1_source_provenance_attestation.json` | sube en este paquete |
| **T-FT-026** | `dual_authorization_gate_implemented` | `technical-smoke-ready.txt` | **ya está en el clúster** |
| **T-FT-030** | `fixed_vocabulary_serving_passed` | `evidence/t1_smoke_1166583_media_plane.json` | sube en este paquete |
| **T-FT-031** | `checkpoint_evaluation_passed` | `evidence/t1_yoloe26s_bench_v3_protocol.json` | sube — **congelado el 2026-08-15** |
| **T-FT-032** | `bench_v3_baseline_frozen` | `evidence/t1_baseline_eval/artifact.sha256` | sube — **baseline corrida el 2026-08-15** |
| **T-FT-042R** | `technical_smoke_passed` | `smoke-ready.json` | **ya está en el clúster** |

Los hashes de todo lo que se sube están en `MANIFEST.sha256`. `t1_baseline_eval/` lleva
además los tres JSON de la evaluación, para que la evidencia sea auditable y no sólo
hasheable.

**Por qué `smoke-ready.json` no está en este paquete:** lo genera
`prepare_t1_smoke_gate.py` en el clúster y escribe un `created_at` con la hora actual —
**no es determinista**. Regenerarlo acá daría otro sha256 y rompería el `binding`. Tiene
que ser exactamente el que ya está allá.
