# Pendientes — lo que falta cerrar

> **Actualización del 2026-09-10:** P-2 y P-1 cerrados en ese orden; P-3/P-5
> completados. P-4 está registrado en el cierre como **dos decisiones de alcance
> pendientes del usuario**, no aprobadas. Ver [cierre vigente](02-cierre-implementacion.md)
> y [salidas completas](punch-list-verificaciones.md). Se conservan debajo la
> auditoría y sus decisiones para explicar el trabajo. No se iniciaron los tramos 6/7.

Auditoría del 2026-09-10 sobre el árbol entregado. Todo lo de acá se midió
ejecutando, no leyendo reportes.

**El trabajo se acepta.** Las siete decisiones se respetaron menos una, los dos
defectos conocidos están arreglados, la distribución quedó intacta y no se aflojó
un solo test. Lo que sigue es deuda, no rechazo.

Estado medido:

| | Base `50b666b` | Entregado |
|---|---|---|
| Backend | 668 ✅ | **784 ✅** (0 fallas, 0 skips) |
| Frontend | 387 ✅ | **454 ✅** (69 archivos) |
| `tsc && vite build` | — | **pasa** |
| ruff | 36 | **36** (cero nuevos) |

---

## P-1 · No hay ni un commit (D-6 incumplido) — **bloqueante para revisar**

La rama `feature/webconsole-adopcion-front-design` tiene HEAD en `50b666b`, el
mismo tip que la rama operativa. Los 98 archivos están sin commitear, en un
bloque único.

D-6 pedía **un commit por tramo**. La consecuencia no es cosmética: no hay forma
de revisar por tramo ni de retroceder uno solo, y la premisa del tramo 0 —el
contrato verde **antes** de tocar código— dejó de ser auditable desde la
historia.

**Qué hacer:** partir el árbol en los seis commits por tramo, en el orden de
`00-diseno.md` §6, con los mensajes que indica cada `tramo-N.md`. El corte de
cada uno tiene que quedar compilando; si un archivo no puede separarse
limpiamente, decilo en el mensaje del commit en vez de forzarlo.

**No hagas merge ni push.** Eso lo hace el usuario.

---

## P-2 · La mitad del contrato no prueba paridad

Se levantó la rama operativa intacta (`50b666b`) y se corrió el contrato contra
ella. Resultado: **5 de 10 tests fallan**.

| Test | Falla porque busca |
|---|---|
| `nueva-corrida` × 3 | `/^Lanzar corrida$/i` — la consola vieja dice **«Lanzar»** a secas |
| `nueva-corrida` | un `button` llamado `helmet` — la UI vieja no dibujaba las clases como botones |
| `experimentos-distribucion` × 2 | `/^Partir de este$/i` y `/^Ejecutar$/i` — rótulos **nuevos** |

Esos cinco se escribieron contra la UI nueva. No prueban que el comportamiento se
conservó: describen el que se construyó. El tramo 0 pedía lo contrario.

**Esto NO es un reproche al producto.** Cambiar «Lanzar» por «Lanzar corrida» es
exactamente la mejora visual que se pidió. El problema es que el contrato perdió
su capacidad de demostrar la paridad justo en el flujo más importante.

Los otros cinco **sí** son evidencia genuina, porque pasan en ambos mundos —
entre ellos el de **outcomes de distribución**, que era la feature con más riesgo.

**Qué hacer:** que los cinco toleren ambos rótulos, sin bajar la exigencia.

```tsx
// Sirve antes y después. La aserción que importa —el payload— no se toca.
screen.getByRole('button', { name: /^Lanzar( corrida)?$/i })
```

Para el botón `helmet` y los de experimentos, el mismo criterio de rama defensiva
que ya usás en `completar()`: manejar las dos formas de manejar la UI, y dejar la
**aserción** incondicional.

### ✎ 2026-09-10 — un caso NO era de rótulos: era una regresión

Al adaptar los selectores apareció un test que no se arregla con selectores:
`impide lanzar y muestra el motivo cuando el preflight informa bloqueos`. Codex
paró y preguntó, que es lo que correspondía. Verificado:

```
VIEJO   missingReason gatea por `target` (media-plane) + formulario completo.
        Nunca lee preflight.blockers: los muestra en PlatformStatus, no bloquean.

NUEVO   agrega  if (preflight?.blockers.length) return preflight.blockers.join('; ')
```

Y `platform_preflight` arma los blockers **incondicionalmente**, incluido
`"el control-plane no responde"`. Consecuencia: **con el control-plane caído la
consola nueva no deja lanzar una corrida DBE de sólo medios.** Antes sí. El
camino DBE no necesita el control arriba —el media escribe `detections.jsonl` y
el control lo relee después— y las 420 corridas de evidencia del banco de
imágenes son exactamente eso.

**Es una regresión de capacidad, no una mejora.** El contrato hizo su trabajo:
atrapó un cambio de conducta que nadie decidió.

**Decisión (D-8): revertir a paridad.**

1. Sacar la línea `if (preflight?.blockers.length) …` de `missingReason` en
   `ComposePage.tsx`. Los bloqueos se siguen viendo en `PlatformStatus`, como
   siempre.
2. Reescribir ese caso del contrato para que afirme la **capacidad que se
   preserva**, que es lo que ambas versiones hacen: con bloqueos de preflight,
   formulario completo y `target` listo — el texto del bloqueo **se ve**, el
   botón de lanzar **sigue habilitado**, y pulsarlo **manda el `POST`**.
3. El gate por `target` ya lo cubre el segundo caso, que pasa en ambas.

**No se acepta** convertirlo en «prueba de regresión exclusiva del frontend
nuevo»: eso deja la regresión escrita como comportamiento deseado.

**Precisión al verificar D-8:** `PlatformStatus` no imprime los strings arbitrarios
de `blockers`; muestra la salud con etiquetas. El contrato usa una respuesta
coherente (`control.healthy=false`, `control.ready=false`) y exige el aviso
**«Motor de reglas sin respuesta»**, lanzamiento habilitado y POST efectivo.
Se verifica en ambos árboles sin modificar el código viejo ni la aserción del
payload del primer caso. Los dos tests nuevos de polling de preflight también
se alinearon con D-8; no pertenecían a los 387 tests de `50b666b`.


Si más adelante se quiere gatear por bloqueos, hay que acotarlo a los que
apliquen a la corrida que se está componiendo (medios para DBE; medios y control
para live/EBE). Eso es comportamiento **nuevo** y se decide aparte.

**Criterio de cierre, y es el punto entero:** el contrato tiene que dar **10/10
contra `50b666b` sin tocar** y **10/10 contra el árbol nuevo**. Verificalo así,
y pegá las dos salidas:

```bash
# Desde la raíz de e-ovrt_experimental-setup. Reutilizar el worktree existente.
if [ ! -d /tmp/paridad ]; then
  git worktree prune
  git worktree add /tmp/paridad 50b666b --detach
fi
cp -r webconsole/frontend/src/__tests__/contrato /tmp/paridad/webconsole/frontend/src/__tests__/
if [ ! -e /tmp/paridad/webconsole/frontend/node_modules ]; then
  ln -s "$PWD/webconsole/frontend/node_modules" /tmp/paridad/webconsole/frontend/node_modules
fi
git -C /tmp/paridad diff --exit-code 50b666b --
cd /tmp/paridad/webconsole/frontend && npx vitest run src/__tests__/contrato
# Conservar /tmp/paridad para los tramos 6 y 7.
```

---

## P-3 · El documento de cierre está desactualizado

`02-cierre-implementacion.md` (09-09 13:51) reporta **772** tests de backend. Hoy
son **784**: `tests/test_experiment_history.py` es del 10-09 01:25, o sea
posterior al "cierre".

Es la deuda de siempre —doc y código divergiendo—, en versión leve. **Qué
hacer:** actualizar el cierre al estado final, o marcarlo como parcial y agregar
lo que entró después.

---

## P-4 · Alcance ampliado — que lo decida el usuario, no el cierre

Dos capacidades que no estaban en ningún tramo, ambas con test y ambas
documentadas en el README:

1. **Compatibilidad del índice de artefactos** con un media-plane anterior al
   endpoint de inventario (`test_artifacts_legacy_service.py`, 404/307/308).
2. **Evidencia de un experimento navegable tras reiniciar la consola**
   (`test_experiment_history.py`).

Las dos son defendibles y la segunda es útil para la defensa. Pero son alcance
nuevo. **Qué hacer:** listarlas explícitamente como decisión pendiente en el
cierre, no darlas por aprobadas porque estén verdes.

---

## P-5 · Los reportes viven en un directorio ignorado

`tramo-2-reporte.md` y `tramos-3-5-reporte.md` están bajo
`webconsole/tools/captures/`, que el `.gitignore` ignora — correctamente, porque
ahí van los PNG. Pero eso deja los reportes fuera de git y se pierden.

**Qué hacer:** mover el texto de los reportes a `docs/rediseno-consola/`
(las imágenes se quedan donde están, ignoradas).

---

## Lo que NO hay que tocar

- El `soporte.tsx` del contrato: el `import.meta.glob` opcional que cae a `render`
  pelado cuando `test-utils.tsx` no existe está **bien resuelto** y es lo que
  permite correr el contrato de los dos lados. No lo simplifiques.
- El test de D-5 (`test_preflight_distribution_health.py`): los cuatro estados
  parametrizados y la verificación de que el cliente no se recrea son **más** de
  lo que pedía el spec. Queda como está.
- La igualdad exacta en `test_report_generator.py`.
