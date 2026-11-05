# Evidencia de la generación 2 — catálogo de pruebas

Cada carpeta `<ID>/prueba.yaml` es el **pre-registro** de una prueba (doc 134 del repo `docs`):
qué mide, contra qué tabla del informe, con qué insumo y configuración (con sus huellas), qué
se espera y qué veredicto puede salir. **Se commitea antes de correr y no se toca después**: el
driver copia el pre-registro a su carpeta de resultados y, si cambia, se niega a seguir sobre
la misma carpeta (`--forzar` archiva la anterior y deja constancia).

Los resultados quedan en `results/gen2/<ID>/` (`resultado.json`, `corridas.json`,
`entorno.json`, `comandos.txt`, `logs/`). Esa carpeta se versiona; lo pesado (detecciones,
previews) queda en los `runs/` de cada servicio.

## Cómo se corre (en la Victus)

Todo pasa por el runner de la consola (`POST /api/experiments/run`). El driver corre dentro
del contenedor de la consola, con estos envoltorios desde `e-ovrt_experimental-setup/infra/platform/`:

```powershell
.\evidencia.ps1 lista                 # el catálogo y en qué estado está cada prueba
.\evidencia.ps1 verificar F1 F3       # sin correr nada: huellas de prompts y patrones, insumos en disco
.\evidencia.ps1 correr F1             # integridad + plataforma (sin GPU)
.\evidencia.ps1 -Fondo correr F3      # noche 1 (sigue aunque se cierre la terminal)
.\evidencia.ps1 estado                # progreso
```

En Git Bash o WSL: `infra/platform/evidencia.sh` con los mismos argumentos (`--fondo` en vez
de `-Fondo`). Si se corta, se vuelve a lanzar el mismo comando: retoma donde quedó (clip por
clip, estrato por estrato).

## Fases

| Fase | Pruebas | GPU | Duración estimada en la Victus |
|---|---|---|---|
| F1 | `INT-01`, `INT-02`, `INT-03`, `PLAT-01`, `GT-01` | no | ~10 min (hashea 6.477 imágenes y 47 videos) |
| F3 | `ALR-01`, `ALR-03`, `ALR-04`, `ALR-06`, `ALR-07`, `ALR-09` | sí | ~9 h (`ALR-09` a 800 px, ~1,8 h; `ALR-03` y `ALR-06` con base-560, que tarda ~2× tiny por cuadro) |
| F4 | `IMG-01`, `IMG-02`, `IMG-03`, `IMG-04`, `EXT-01`, `PER-01`, `PER-02`, `DEN-01`, `DEN-03`, `DEN-05` | sí | ~4 h (`IMG-04` a 800 px, ~0,4 h; `IMG-02` y `PER-02` con base-560) |
| F5 | `ALR-02`, `ALR-05`, `ALR-08`, `ALR-10`, `DEN-02`, `DEN-04`, `DEN-06`, `DEN-07`, `PER-03`, `GT-02`, `ERR-01`, `ERR-02`, `SEG-01`, `VIS-01` | casi no (PER-03 infiere 4 clips cortos) | ~1,5 h (GT-02 es lo largo; `VIS-01` extrae ~50 cuadros con ffmpeg) |
| F6 | `RT-01`, `RT-02`, `DIST-01` | sí | ~30 min |
| F7 | `RT-04` (la obra simulada en vivo, toma por toma por `/demo`), `RT-05` (el compromiso entre familias de modelo y cadencias, con la misma escena), `RT-03` (latencia), `RT-06` (el subset del guion con la cámara IP por RTSP; enmienda del 2026-11-01), `RT-07` y `RT-08` (el chaleco amarillo no reflectivo, una persona, con la OAK-D y con la cámara IP; enmiendas del 2026-11-01; corridas el 2026-11-01), `RT-09` (la prenda bajo el chaleco; enmienda del 2026-11-04, va antes de RT-04) — con el equipo, OAK-D y cámara IP (de a una), dos cascos y los dos chalecos reflectantes de julio (RT-07: el amarillo) | sí | una jornada (~14 escenas, ensayos de la demo, la matriz de RT-05, 7 tomas con la cámara IP en sus dos streams (✎ 11-05; antes 13), y ~15 con el chaleco amarillo) |

F3 y F4 llevan **dos noches**, una por fase (~9 h + ~4 h de GPU, estimadas desde la enmienda del 2026-10-30, que
regenera los contrastes: `.\evidencia.ps1 -Fondo correr F3` y, la noche siguiente, `correr F4`; el driver retoma
donde quedó). Si el código del media-plane cambió desde el build, repetir el paso 3 de «Antes de empezar» (build con
el log) y `correr PLAT-01` antes de F3, para que toda la evidencia salga de una sola imagen. El driver cambia solo la instancia del modelo cuando
una prueba pide otra (`mp-gdino-tiny` para ALR-09 e IMG-04; `mp-mock` para EXT-01;
`mp-gdino-base-560` para ALR-03, ALR-06, IMG-02 y PER-02; `mp-yoloe-26x` para IMG-03): usa el mismo
mecanismo que el botón de la consola. **`mp-gdino-tiny`, `mp-gdino-base-560` y `mp-yoloe-26x` se crean antes de la noche** (paso 5 de
«Antes de empezar»): crear un contenedor durante la campaña puede tirar la red de WSL.

## Enmienda del 2026-10-29: errores, resolución y seguimiento (doc 137)

Siete pruebas nuevas, pre-registradas **antes** de correr nada en la Victus, para explicar, con
cifras y con los cuadros, por qué el sistema se equivoca en obra real:

| Id | Qué hace | GPU |
|---|---|---|
| `ALR-09` | obra real con `gdino-tiny` a 800 px, caja 0,35, escena + variante por sujeto | ~1,8 h |
| `ALR-10` | las detecciones de `ALR-07` re-umbraladas a 0,35 (560 px), escena + sujeto: la otra punta del contraste de resolución | no |
| `IMG-04` | `bench_v3` a 800 px con caja 0,35, contra `IMG-01` re-umbralada a 0,35 (`comparador`) | ~0,4 h |
| `ERR-01` | anatomía de las falsas alarmas por sujeto de obra real: causa por causa, fragmentación de identidad, tamaño de la persona, iluminación; muestra para revisión humana ciega | no |
| `ERR-02` | la misma anatomía a 560 contra 800 px, con el mismo umbral | no |
| `SEG-01` | fragmentación de identidad contra las trayectorias de la referencia, en los 47 clips (sin MOTA/HOTA) | no |
| `VIS-01` | cuadros y recortes anotados de aciertos y fallos; la versión ciega de la muestra de `ERR-01` | no |

`ERR-01` y `SEG-01` traen la cifra de la generación 1 (piloto con este mismo código,
`docs/operacion/datos/137-…/piloto_gen1.py`): si `ALR-07/08` y `ALR-01` reproducen la
generación 1, tienen que dar **idéntico**. El re-umbral es exacto para GDINO (el umbral se aplica
antes del NMS); las cajas con puntaje exactamente igual al umbral se cuentan aparte.

**Revisión humana de la muestra de `ERR-01` (después de `VIS-01`).** Los cuadros quedan en
`defensa/figuras/VIS-01/` (fuera de git: incluyen clips de internet, que **nunca** se publican).
Una persona del equipo abre solo `revision_ciega/`, completa `revision_ciega.csv` (¿la caja roja
es una persona? ¿se ve el casco o el chaleco?), lo copia a `results/gen2/ERR-01/revision_humana.csv`
y vuelve a correr `.\evidencia.ps1 correr ERR-01`: la concordancia queda en el resultado. Sin
abrir `completas/` ni `muestra.json` antes de terminar. Para el informe se usan los `recortes/`,
con las caras difuminadas a mano si hiciera falta.

✎ 2026-10-31: **revisión asistida por IA, validada por una persona.** Claude Code mira solo los
cuadros ciegos y propone una respuesta por cuadro (`propuestas_ia.json`), con una razón breve.
`evidencia.sh revision-ciega pagina` arma `revision.html`, donde una persona del equipo confirma o
cambia cada respuesta y descarga el CSV. Después, `evidencia.sh revision-ciega cerrar` lo valida y lo
deja en `results/gen2/ERR-01/revision_humana.csv`, con la propuesta de Claude al lado de la respuesta
final. ERR-01 informa `asistida_por_ia` y `cambios_de_la_persona`.

## Las pruebas de contraste se regeneran (doc 134 §13.10)

`ALR-03`, `ALR-04`, `ALR-05`, `ALR-06`, `IMG-02`, `IMG-03` y `PER-02` comparan **otra configuración contra el
campeón**: otro modelo, otra formulación u otra evidencia. Hasta el 2026-10-29 no se regeneraban (doc 134 §13.6).
Desde la enmienda del 2026-10-30 **se corren en la Victus como todas**, dentro de sus fases. El bloque `gen1` de su
pre-registro queda solo como referencia del veredicto. `GT-02` evalúa las 12 conclusiones, C2–C5 incluidas, sobre
las alertas de la generación 2.

## Sesión en vivo con el equipo (F7): la obra simulada repetida en la Victus

**No se graba ni se anota** (el banco temporal del rodaje de julio sigue siendo la referencia de
las pruebas ALR/DEN): se repiten las escenas **en vivo**, por la plataforma en contenedores, para
medir y para validar la plataforma. Y como cada toma corre por la pantalla `/demo`, **cada toma es
además un ensayo de la demo**.

**Armado:** el mismo de la demo (`infra/demo/README.md`): OAK-D en trípode a 960×540 y 5 fps,
cinta en el piso, fondo liso, cargador enchufado, `/demo` abierta en el proyector o en otra
ventana. Roles del doc 69: un OPERADOR (nunca en cuadro) y uno o dos actores.

```powershell
cd e-ovrt_experimental-setup\infra\platform
.\rodaje.ps1 -Lista                       # las 15 escenas, su guion y qué se espera de cada una
.\rodaje.ps1 -Escena P1 -Chaleco julio    # una toma: espera el chequeo previo, la lanza, dice el guion
                                          # por los parlantes, la cierra y deja marcas.json
```

**`-Chaleco` es obligatorio en cada toma** (enmienda del 2026-11-01, doc 134 §13.14): CR-02 depende del
chaleco, así que cada pre-registro fija uno. RT-04, RT-05 y RT-06 cuentan solo `-Chaleco julio` (los dos
chalecos reflectantes del rodaje); RT-07, solo `-Chaleco amarillo`. Una toma con otro chaleco o sin
declararlo queda como no evaluable, con el motivo.

Orden sugerido (de menos a más cambio de vestuario, doc 69 §6): `P1` ×3, `P1b` ×2 (lejos de la cámara,
con una segunda marca de cinta), `P1c`, `P3` ×2, `P4`,
`P9b` (y `P9a` si hay gorra) → `P2` ×3, `P6` → `P8` → `P5`, `P7a`, `P7b`, `P7c` (dos cascos y dos
chalecos) → `DEMO` ×5 o más (los ensayos de la demo: 5 aprobados seguidos es la etapa G3). Una escena sin
ninguna toma no desaparece: el resultado la nombra (`escenas_sin_tomas`) y RT-04 queda `parcial`. Las
alertas que llegan antes de la acción se cuentan aparte (es lo que busca `P1b`). Después:

```powershell
.\evidencia.ps1 correr RT-04     # importa las sesiones, las compara con su guion y relee por sujeto
.\evidencia.ps1 descartar RT-04 demo_20261102T...Z_P5 --motivo "pasó alguien por el fondo" --quien "Nombre"
```

- **Una toma mala no se borra:** se descarta con motivo y firma, y queda listada.
- Entre toma y toma la consola **reinicia el motor sola** (F-101.5) y `rodaje.ps1` espera a que el
  chequeo previo vuelva a estar en verde (~20–30 s). Nunca `docker compose up -d`.
- **Remera lisa y oscura**; lo que se saca se deja **fuera de cuadro**; no salir de cuadro con una
  alerta activa salvo en P8, que justamente mide eso (F-101.9).
- La marca de cada acción es el tono del director: el tiempo de reacción del actor queda dentro de
  «acción → alerta» y se declara así.
- Si no hay voz en español instalada en Windows, habla la voz por defecto; `-SinVoz` deja el guion
  solo en pantalla (el OPERADOR lo canta).
- Las sesiones tienen caras del equipo: quedan en `defensa/sesiones/` (fuera de git) y **nunca** van
  a la carpeta compartida ni a un canal nuevo. A `results/gen2/RT-04/` van solo números.

**RT-05 (compromiso en vivo entre familias de modelo y cadencias).** La misma escena `DEMO`
con otro motor u otra cadencia de cámara, de la lista cerrada de
`experiments/demo_defensa/exploracion.yaml`: Grounding DINO tiny y base, YOLOE-26 s y x, a
960×540 a 5 y a 15 fps, con 3 tomas por celda. `rodaje.ps1` activa la instancia si hace falta, deja el motor
fresco y marca la sesión como exploración: su id termina en `_exp`, RT-04 no la cuenta, y la
demo de la defensa sigue siendo la congelada. Conviene agrupar por motor.

```powershell
.\rodaje.ps1 -Escena DEMO -Chaleco julio -Motor mp-yoloe-26s -Camara 960x540@15
.\evidencia.ps1 correr RT-05     # importa las sesiones de exploración por celda
..\demo\demo.ps1 up              # al terminar: de vuelta al campeón
```

Requisito: las cuatro instancias creadas con la imagen actual **antes** de la jornada. Crear o
recrear un contenedor puede tirar la red de WSL. El protocolo de la jornada está en el doc 136
del repo `docs`.

**RT-06 (la cámara IP del guion, enmienda del 2026-11-01, doc 134 §13.13).** El guion de julio filmó un
subset de escenas con la cámara IP por RTSP como segunda fuente. RT-06 lo repite en vivo, con el mismo guion de voz
que RT-04, la cámara **sola, directo a la Ethernet** (la OAK-D desconectada) y sus **dos streams**, que se agregan por
separado:

| Stream | Ruta | Preset sugerido | Tomas mínimas |
|---|---|---|---|
| secundario, 768×432 a 10 fps | `/Streaming/Channels/2` | `rtsp_dvr_sub` | P1 ×2, P2 ×2, P5 ×1 |
| principal, 1920×1080 a 15 fps | `/Streaming/Channels/1` | `rtsp_dvr_1` | P1 ×1, P2 ×1 |

✎ Enmienda del 2026-11-05 (doc 134 §13.20), antes de correr: 7 tomas mínimas en lugar de 13 (antes, secundario P1 ×3,
P2 ×3, P5 ×2 y principal P1 ×2, P2 ×2, P5 ×1). La OAK-D cubre las 15 escenas en RT-04; la cámara IP muestra que el
sistema no depende del sensor. La cámara IP también se calibra antes de su primera toma (doc 134 §13.19).

Antes, crear en Cámaras los dos presets con sus URL y credenciales (`cameras/` no viaja por git), comprobar la cámara en
`/demo` y encuadrar sobre la misma cinta. Conviene agrupar las tomas por stream. Con esta fuente se mide G2A; «vidrio →
resultado» no existe (el RTSP no trae la hora de captura del dispositivo). Si falta alguna toma mínima, RT-06 queda
`parcial` y dice qué falta en cada stream.

```powershell
.\rodaje.ps1 -Escena P1 -Chaleco julio -Fuente rtsp_dvr_sub    # secundario; comprueba la cámara y, si no se ve, no lanza
.\rodaje.ps1 -Escena P1 -Chaleco julio -Fuente rtsp_dvr_1      # principal
.\evidencia.ps1 correr RT-06                                    # solo las tomas con la cámara IP, por stream
```

**RT-07 (el chaleco amarillo no reflectivo, enmienda del 2026-11-01, doc 134 §13.14).** En la jornada hubo un
solo chaleco, amarillo y sin bandas reflectantes, distinto de los de julio. No se mezcla con RT-04/05/06: se mide
aparte, con una persona y la OAK-D, en `P1` ×2 (el chaleco puesto todo el clip: ¿lo reconoce o dispara CR-02 en
falso?), `P2` ×3 (CR-02 sola), `P6` ×1 (las dos) y `DEMO` ×3 (el guion de la demo; se evalúa con el criterio de
ensayo, pero NO cuenta para G3, que se mide con el chaleco de la defensa).

```powershell
.\rodaje.ps1 -Escena P2 -Chaleco amarillo
.\evidencia.ps1 correr RT-07                    # solo las tomas que declararon el chaleco amarillo
```

**RT-08 (el chaleco amarillo con la cámara IP, enmienda del 2026-11-01, doc 134 §13.15).** La misma pregunta que RT-07,
pero con la cámara IP y en sus dos streams, agregados por separado: secundario `P1` ×2 y `P2` ×2, principal `P1` ×1 y
`P2` ×1. Va después de RT-07, sin cambiar el vestuario: se desconecta la OAK-D, se conecta la cámara IP directo a la
Ethernet, se crean los dos presets y se comprueba. Es además el primer uso del camino de RT-06 en la Victus. Si CR-02
difiere de RT-07, la diferencia no se atribuye al sensor (doc 69 §6.0.1).

```powershell
.\rodaje.ps1 -Escena P2 -Chaleco amarillo -Fuente rtsp_dvr_sub    # secundario (rtsp_dvr_1: principal)
.\evidencia.ps1 correr RT-08                                       # RT-06 y RT-07 no las cuentan
```

**RT-09 (la prenda bajo el chaleco, enmienda del 2026-11-04, doc 134 §13.18; ✎ 2026-11-05, §13.19: más la frase y
el encuadre).** Va al arrancar la segunda jornada, ANTES de RT-04, con los chalecos de julio, el campeón y una
persona: `P2` ×2 por remera candidata (✎ 2026-11-05: la remera se decide al inicio de la jornada, clara contra
"negra lisa", la de referencia; regla en doc 144 §5.1), más el modo
exploratorio `reflective` (el campeón con «reflective vest» en vez de «vest»: P2 ×2 con la negra y P1 ×1) y,
opcional, GDINO base por la exploración de RT-05. `correr RT-09` mide el `vest` en el torso con la regla de CR-02
(fracción y rachas), agrupa por modo × motor × encuadre × escena × remera y propone la remera de RT-04/05/06 solo
con el campeón calibrado; el equipo la firma en la bitácora. Desde esta jornada, **toda toma declara `-Remera`**, y
`-Proposito prendas|ensayo` saca la toma de RT-04…RT-08. (La clase distractora «t-shirt» se pensó como segunda parte
y salió antes de correr: su piloto en datasets duplicó el `vest` falso; doc 141 §4.)

**La calibración de encuadre (✎ 2026-11-05, doc 134 §13.19; doc 143).** Antes de la primera toma de cada cámara, con
la cámara ya ubicada (alta, mirando hacia abajo): `rodaje.ps1 -Calibrar -Altura <m> -Cerca <m> -Lejos <m>` (una
persona en regla se para en la marca cercana, camina a la lejana y vuelve; escena `CAL`, 30 s) y `evidencia.ps1
calibrar`, que compara la geometría de la persona con los criterios de `experiments/demo_defensa/calibracion.json`
y deja la constancia en `results/gen2/_calibraciones/` y la vigente por cámara. **Sin una vigente que haya pasado
(o aceptada con motivo: `calibrar --aceptar`), `rodaje.ps1` no lanza tomas.** Cada toma lleva la calibración en
`marcas.json`, y RT-04…RT-09 cuentan las tomas por encuadre.

```powershell
.\rodaje.ps1 -Calibrar -Altura 1.9 -Cerca 3 -Lejos 6 ; .\evidencia.ps1 calibrar       # primero, hasta que pase
.\rodaje.ps1 -Escena P2 -Chaleco julio -Remera 'negra lisa' -Proposito prendas
.\rodaje.ps1 -Escena P2 -Chaleco julio -Remera 'gris clara lisa' -Proposito prendas
.\rodaje.ps1 -Escena P2 -Chaleco julio -Remera 'negra lisa' -Proposito prendas -Modo reflective   # ×2
.\evidencia.ps1 correr RT-09                                       # propone la remera; RT-04 no las cuenta
.\rodaje.ps1 -Escena P1 -Chaleco julio -Remera '<la propuesta>' -Proposito prendas -Modo reflective
.\rodaje.ps1 -Escena P1 -Chaleco julio -Remera '<la firmada>'    # después, RT-04 con la remera firmada
```

Una prueba que queda **`parcial`** porque algo pre-registrado no se va a correr (p. ej. RT-03 a 1080p@30) se
firma con `veredicto … --parcial` y el motivo (ver «Veredictos»).

**RT-03 (latencia por cuadro en dos configs)** sigue por el driver, sin guion: una persona
moviéndose en cuadro, 2–3 tomas por config. ✎ 2026-11-04: la config 1080p@30 se retira sin correr (doc 134
§13.17): RT-03 se cierra con las tres tomas a 960x540@5 y `veredicto --parcial`.

```powershell
.\evidencia.ps1 vivo RT-03 --toma lat_960_a --config 960x540@5
.\evidencia.ps1 vivo RT-03 --toma lat_1080_a --config 1080p@30
```

Una toma de RT-03 con huecos de cámara o captura → host > 2 s queda marcada **contaminada** (guard
del doc 101 §5.3) y no entra al agregado: apagar y prender la OAK-D y repetir.

## Veredictos

El driver **propone** un veredicto contra la generación 1 (`identico`,
`equivalente_con_diferencia`, `otra_combinacion`, o `a_revisar` si difiere sin causa
declarada). Lo confirma una persona:

```powershell
.\evidencia.ps1 veredicto ALR-01 identico --motivo "los 12 campos iguales a la gen 1 re-evaluada" --quien "equipo E-OVRT-VDP"
```

Para el banco temporal, la referencia de la generación 1 es la **re-evaluada con el GT
corregido** (revisión dirigida del 2026-10-26), no la publicada en el v0.1.

Una prueba **`parcial`** (una escena, una configuración o una toma mínima pre-registrada sin
correr) no se firma, salvo a propósito: `veredicto … --parcial`, con un motivo que diga por qué
lo que falta no se va a correr. La firma deja `confirmado.parcial: true` y `confirmado.faltante`;
el estado sigue siendo `parcial`. Una relectura por sujeto fallida no se firma nunca: se corrige y
se vuelve a correr (doc 134 §13.17; el caso fue RT-03 sin 1080p@30 en F7).

## Antes de empezar (una vez)

1. Repos en `main` actualizados y el paquete privado `traspaso-victus-gen2.zip` descomprimido en
   la raíz del workspace (`docs/contexto/LEEME-PRIMERO.md`).
2. Imágenes de los bancos bajadas de su fuente y verificadas por huella: CHV, SHEL5K, obra
   (`construction_site_safety` v27) y MOCS. La receta está en
   `e-ovrt_datasets/datasets/scripts/download/README.md`; las dos de Roboflow piden una clave
   personal gratuita. Los pesos se bajan con `make download-models` (versiones fijadas) y se
   verifican con `INT-03/modelos.sha256`.
3. `docker compose build` y la plataforma arriba (`infra/platform/README.md`). **Guardar la salida del build**
   para PLAT-01, que registra su huella junto con la de la infraestructura declarada (el build corre acá, fuera
   del driver), desde `infra/platform/`:
   ```powershell
   New-Item -ItemType Directory -Force ..\..\results\gen2\PLAT-01\logs | Out-Null
   .\compose.ps1 build 2>&1 | Tee-Object -FilePath ..\..\results\gen2\PLAT-01\logs\compose_build.log
   ```
   Antes de commitearlo, correr `limpiar-rutas` (doc 134 §13.12).
4. `.\evidencia.ps1 verificar todas` sin fallas bloqueantes.
5. Crear una vez las instancias de la campaña, con la imagen actual, igual que las de RT-05
   (doc 136 §2), desde `infra/platform/`. Son `mp-gdino-tiny` (ALR-09, IMG-04), `mp-gdino-base-560`
   (ALR-03, ALR-06, IMG-02, PER-02) y `mp-yoloe-26x` (IMG-03), estas dos desde el 2026-10-30:
   `.\compose.ps1 --profile models up --dry-run -d --no-build mp-gdino-tiny mp-gdino-base-560 mp-yoloe-26x`
   (dice qué haría) y `.\compose.ps1 --profile models create mp-gdino-tiny mp-gdino-base-560 mp-yoloe-26x`.
   Si ya se crearon con el paso de doc 136 §2, no hace falta repetirlo. Si después ningún puerto responde:
   Inicio → Reiniciar. Verificarla activándola desde Plataforma: tiene que decir *listo*.

**Finales de línea.** Los repos no fijan finales de línea: un clon con Git para Windows
(`core.autocrlf=true`) deja los JSON/YAML con CRLF. Las huellas los aceptan y lo declaran
aparte (`ok_salvo_finales_de_linea`), pero lo prolijo es clonar con `git config --global
core.autocrlf input`.

## Decisiones que eran abiertas (doc 134 §11), resueltas el 2026-10-29

- `IMG-04` entró como 800 px contra 560 px **con el mismo umbral (0,35)**: no hace falta un
  perfil de modelo nuevo, porque el brazo de 560 px sale de re-umbralar `IMG-01`.
- `SEG-01` entró en forma reducida: fragmentación de identidad sobre las personas anotadas, sin
  MOTA/IDF1/HOTA (la referencia no garantiza que estén todas las personas anotadas).
