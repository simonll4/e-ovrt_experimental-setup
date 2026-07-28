# Consola como evidencia de tesis — diseño

Fecha: 2026-07-28
Repo: `e-ovrt_experimental-setup` · alcance: `webconsole/frontend/`
Supersede parcialmente: `2026-07-26-rediseno-consola-design.md` (ver §1)

## 1. Contexto y diagnóstico

El intento anterior (`feature/webconsole-rediseno-fundacion`, 80 archivos, +3558
líneas) fue rechazado por el usuario: *"no cumple con el diseño ni con la elegancia
y profesionalidad que tiene el mockup"*. El diagnóstico se hizo con evidencia
visual: se levantaron los tres servicios con datos reales (136 corridas) y se
capturaron las mismas pantallas en el prototipo, en la consola actual y en la rama
abandonada.

**La causa no fue descuido, fue el spec.** `2026-07-26-rediseno-consola-design.md`
§1 decidió *"sin cambios estructurales… pantallas revestidas in-place"*. Eso es un
reskin. Pero lo que hace elegante al prototipo no es la paleta: es la
**composición**. Pintar de violeta un volcado vertical de 1468 cuadros produce un
volcado vertical de 1468 cuadros en violeta.

Consecuencia medida en las capturas: el reskin invirtió las superficies (lienzo
`#121211` más oscuro que tarjeta `#1a1a19`) sobre marcado que no usa tarjetas, así
que los contenedores desaparecieron y el contenido quedó flotando. **Detalle de
corrida en la rama se ve peor que el original.**

Estado real de las tres pantallas críticas hoy:

| Pantalla | Hoy | Prototipo |
|---|---|---|
| Corridas | 136 filas sin paginar, filas de ~59 px, encabezados `RUN`/`DETS`/`DUR (S)`, `stopped`/`grounding_dino` crudos, botón **Borrar** en cada fila | filas de 32 px, buscador + segmentado + contador, chips de estado con icono+texto, identificadores en monoespaciada |
| Detalle de corrida | scroll infinito de 1468 cuadros, cada uno un rectángulo "sin preview"; 4 tiles sin gráfico; encabezados `SUMMARY`, `QUEUE_FULL` | 6 tiles KPI con sparkline, línea de tiempo con carriles, pestañas, maestro-detalle con visor |
| Comparar | lista de checkboxes con `run_id`s crudos y guiones | dos paneles, tabla de métricas con mejor valor por fila, barras agrupadas |

**Lo que sí sirve de la rama** (auditado archivo por archivo): `tokens.css` v2 —
transcripción exacta del prototipo—, `icons.tsx`, `labels.ts` (glosario verificado
contra los enums reales del backend, con fallback a código crudo), y las primitivas
`Button`/`Select`/`Table`/`Banner`/`SearchInput`/`SegmentedControl`/`PageHeader`/
`InlineDeleteConfirm`. `Select.tsx` es un desplegable propio accesible correcto.
Además los cuatro `proto-ref-*.md` (3690 líneas) son una transcripción fiel del
prototipo a nivel componente: son un activo, no se rehacen.

**Lo que no existe**: gráficos. `Sparkline.tsx` tiene 14 líneas.

## 2. Decisiones tomadas

1. **Rescatar la base, rehacer las pantallas.** Se conserva la capa de tokens,
   iconos, glosario y primitivas; se reconstruye la composición de cada pantalla
   desde el prototipo, no revistiendo el marcado viejo.
2. **Gráficos en SVG propio**, componentes chicos que consumen los tokens. Sin
   dependencias nuevas.
3. **Alcance: las 4 pantallas de la defensa** — Corridas, Detalle de corrida,
   Comparar, Detalle de experimento. Quedan enteras y terminadas. Las otras 7
   siguen funcionando con su aspecto actual.
4. **No se toca el backend.** Los 10 cambios de API que pedía el README del
   prototipo se resuelven en el cliente (§5). Verificado contra la API viva.

El armazón (`Shell.tsx` con barra lateral, contadores y estado de motores) ya está
hecho en la rama rescatada y viene incluido, con una corrección de legibilidad: en
la captura, los ítems de navegación quedaron en `--tx3` sobre `--s1` y el label
"Conjuntos de prom…" se trunca.

## 3. Arquitectura

Misma SPA Vite/React, mismo `api.ts`/`types.ts`. Tres capas:

```
capa 0 — rescatada tal cual desde feature/webconsole-rediseno-fundacion
  styles/tokens.css · components/ui/icons.tsx · labels.ts
  components/ui/{Button,Select,Table,Banner,SearchInput,SegmentedControl,
                 PageHeader,InlineDeleteConfirm,Badge,Card,EmptyState}

capa 1 — NUEVA: primitivas de gráfico (§4)
  components/charts/{Sparkline,ActivityTimeline,Meter}.tsx
  components/charts/GroupedBars.tsx   (movido y extendido)
  components/charts/layout.ts         (funciones puras de layout, testeables)

capa 2 — REESCRITA: composición de las 4 pantallas (§6)
  pages/{RunsPage,RunDetailPage,ComparePage,ExperimentDetailPage}.tsx
  components/{RunTimeline,FrameInspector,ConditionProgress}.tsx
```

Distinción deliberada entre las capas 1 y 2: `charts/ActivityTimeline` es la
primitiva —recibe series ya calculadas y dibuja—, y `RunTimeline` es la tarjeta que
la compone con su leyenda, su eje, el estado vacío y el enganche con la selección de
cuadro. La primitiva no sabe qué es una corrida; la tarjeta sí. Lo mismo vale para
`Meter` frente a `ConditionProgress`.

La regla que faltaba en el intento anterior, y que es la que hace que el prototipo
se lea como un instrumento: **todo bloque de contenido vive dentro de una `.card`**
(`--s1` + borde) sobre el lienzo `--bg`. Sin esa contención, la inversión de
superficies destruye la jerarquía en vez de crearla.

## 4. Set de gráficos

Cuatro primitivas. Cada una separa **layout puro** (función testeable, sin React)
de **render** (SVG), siguiendo el patrón que `GroupedBars.tsx` ya usa bien.

| Primitiva | Trabajo de los datos | Forma | Dónde |
|---|---|---|---|
| `Sparkline` | cambio en el tiempo, sin escala precisa | área + línea, sin ejes, sin leyenda (1 serie) | tiles KPI de Detalle de corrida |
| `ActivityTimeline` | cambio en el tiempo + eventos discretos | área de detecciones por cuadro + carriles de entrega y alertas + cursor | Detalle de corrida |
| `GroupedBars` | magnitud comparable entre entidades | barras agrupadas, dominio fijo [0,1] | Comparar |
| `Meter` | una proporción contra un límite | barra segmentada horizontal | tiles de experimento, progreso de condiciones |

### 4.1 Color — con la validación corrida, no a ojo

**Series categóricas (Comparar): la paleta actual de `GroupedBars` pasa las seis
verificaciones sobre la superficie oscura `#1a1a19`** — banda de luminosidad,
piso de croma, separación CVD (peor par ΔE 8.4 protan), piso de visión normal
(19.3), contraste ≥3:1. Se conserva **sin reordenar**: el orden es el mecanismo de
seguridad CVD, no cosmética.

**Estados (chips, bandas, carriles): hallazgo que corrige al prototipo.** Los seis
colores de estado del prototipo superan el umbral de contraste de marca que el
validador verifica (3:1 sobre `#1a1a19`, los seis) y son correctos **como estado**,
porque siempre van con icono + texto. La afirmación de ≥4,5:1 del README del
prototipo no fue ni confirmada ni refutada acá: el validador reporta contra 3:1, y
para texto de estado habría que medir WCAG aparte. Pero el prototipo también
los usa como **identidad de serie** en la leyenda de la línea de tiempo
(Detecciones / Descartado / No recibido / Alerta, como cuadraditos de color sin
icono). En ese rol se les aplican las verificaciones categóricas, y fallan:

- `#e0a217` ↔ `#35b45a` — ΔE 4.4 (protan). Un daltónico no distingue "degradado"
  de "completado".
- `#f0625f` ↔ `#ee8a5c` — ΔE 8.8 en **visión normal**, por debajo del piso de 15:
  cuesta distinguirlos incluso con visión de color completa. Son justo "fallida" y
  "alerta confirmada".

**Resolución**: los carriles ya están separados espacialmente (filas distintas),
que es codificación secundaria válida. Se agrega la que falta: **la leyenda de la
línea de tiempo lleva la forma del carril, no un cuadradito de color**, y cada
carril lleva su etiqueta al margen izquierdo. Ningún significado queda cifrado solo
en el matiz. Es exactamente la regla que el README del prototipo declara ("nunca se
usa el color solo") y que su propia leyenda incumple.

### 4.2 Marcas

Líneas de 2 px; extremos de dato redondeados 4 px anclados a la línea base; 2 px de
separación de superficie entre segmentos apilados y entre barras adyacentes;
grilla y ejes recesivos (`--bd`); cifras tabulares. Etiquetas directas selectivas
—nunca un número sobre cada punto—: en `GroupedBars`, el valor sobre cada barra
(son 2–4 grupos); en `Sparkline`, ninguna, el número grande del tile es la
etiqueta.

### 4.3 Interacción

`ActivityTimeline` y `GroupedBars` llevan capa de hover por defecto: cursor +
tooltip en la línea de tiempo (y clic para seleccionar el cuadro, que es cómo se
navega la traza), tooltip por marca en las barras. `Sparkline` y `Meter` no —van
dentro de un tile que ya muestra el número.

Texto siempre con tokens de texto, nunca con el color de la serie.

## 5. Datos: qué existe y qué se deriva

Verificado contra la API viva (`GET /api/runs/{id}`, `/trace`, `/detections`).

`/trace` devuelve por cuadro: `frame_index`, `unit_id`, `timestamp_ms`,
`detections[]`, `control`, `progress[]`, `alert[]`, `active_patterns[]`, más
`totals` con `dropped_by_reason` y `alerts`. **Eso es exactamente lo que necesita la
línea de tiempo.** `summary` trae `fps_effective`, `p50/p95/p99_latency_ms`,
`gpu_memory_peak_mb`, `units_dropped`, `detections_by_label`, `duration_seconds`.

| Lo que pide el prototipo | Resolución en el cliente |
|---|---|
| Índice de actividad de la corrida completa | Se piden todas las páginas de `/trace` al abrir el detalle y se arma el índice en memoria. Escala válida: la corrida más larga del banco es de minutos |
| Series para los sparklines | Se derivan de `timestamp_ms`: fps instantáneo del delta entre cuadros consecutivos, detecciones por cuadro, descartes acumulados. No hace falta serie del backend |
| "Variación comparada con los últimos 30 s" | Solo en corridas **en curso**, comparando la ventana de 30 s contra la anterior, sobre la serie derivada. En corridas terminadas el delta **se omite**, no se inventa |
| "Corrida anterior comparable" | No existe en la API. No se implementa. Comparar sigue siendo el mecanismo manual |
| Nombres legibles de condición | `labels.ts` (capa rescatada), acompañando al código, nunca reemplazándolo |
| Motivos de descarte | `CONTROL_DROP_REASONS` con fallback a código crudo en monoespaciada |
| Filtro/orden/paginación server-side | Cliente. **Pero se agrega paginación**: 136 filas en una página es un defecto real, no una preferencia |

**Riesgo de contenido, no de código**: ninguna corrida del banco tiene `frames/` y
solo algunas tienen `previews/`. El visor con cajas —la imagen que más se mira en
una defensa— va a estar vacío salvo que la corrida de la demostración se grabe con
previews activadas. Es una nota operativa para el guion de la defensa, y el visor
debe degradar con un estado vacío explicativo, no con un rectángulo negro.

## 6. Las cuatro pantallas

Cada una queda entera y terminada antes de pasar a la siguiente. La composición de
referencia está en los `proto-ref-*.md` a nivel componente; acá va la estructura.

### 6.1 Corridas

Encabezado (título + "N en total · N en curso" + acción primaria) → banner de
corrida en vivo con acceso directo → barra de herramientas (buscador + segmentado
Todas/En curso/Completadas/Detenidas/Fallidas + contador "N de N") → tabla densa de
32 px: Corrida (nombre + `run_id` monoespaciado en segunda línea), Estado (chip con
icono+texto), Modelo, Fuente, Conjunto de prompts, Cuadros/s, Detecciones,
Duración, antigüedad.

Cambios sobre el prototipo, justificados: **paginación** (136 corridas reales) y el
borrado por confirmación en línea en vez de un botón permanente por fila.

### 6.2 Detalle de corrida

Migas → encabezado con chips de estado y topología, `run_id`, fuente y duración →
**tira de 6 tiles KPI con sparkline** (cuadros por segundo, latencia mediana,
memoria de GPU, detecciones, descartes de entrega, alertas confirmadas) →
**tarjeta de línea de tiempo** (área de detecciones + carril de entrega al motor de
reglas + carril de alertas + cursor + eje temporal) → pestañas Traza / Resumen /
Evaluación / Archivos.

El panel de Traza es **maestro-detalle**, y esto es lo que reemplaza el volcado
vertical: lista de cuadros virtualizada a la izquierda (con filtros "solo con
actividad" / "solo alertas"), y a la derecha el cuadro seleccionado — banner de
alerta si la hay, visor con cajas, tabla de detecciones, y progreso de las
condiciones con `Meter`. La lista se sincroniza con el cursor de la línea de
tiempo en ambas direcciones.

### 6.3 Comparar

Dos paneles: a la izquierda las corridas evaluadas seleccionables (nombre, modelo,
escenario, antigüedad — no `run_id` crudo); a la derecha la tarjeta de Métricas
(tabla con el mejor valor por fila resaltado, encabezado con la marca de color de
cada corrida) y la tarjeta de Precisión por clase con `GroupedBars`.

Se agrega el aviso de conjunto de evaluación distinto: `bench_split` ya se carga
hoy y comparar dos corridas evaluadas contra conjuntos distintos es una conclusión
inválida que la consola no debe dejar pasar en silencio delante de un jurado.

Nombres de métrica en español con el técnico entre paréntesis una sola vez
(`Precisión media (mAP@0.5)`), para que los números sigan siendo comparables con la
literatura.

### 6.4 Detalle de experimento

Encabezado con el veredicto como chip ("1 criterio sin cumplir") → tres tiles con
`Meter` (criterios cumplidos, alertas emitidas por severidad, sin poder medir) →
tarjeta de Criterios: **Criterio · Medido · Límite · Resultado · Por qué**. La
columna "Por qué" es la que convierte la tabla en evidencia defendible: un criterio
que no se cumple explica su causa, y uno que no se pudo medir explica por qué no
(vía `APPLICABILITY_CAUSE`, ya en el glosario). → tarjeta de Alertas emitidas →
tarjeta de Trazabilidad (corrida de video, corrida de reglas, manifiesto).

Se mantiene la lectura tolerante del reporte (`row.name ?? row.metrica ??
row.metric`): no hay contrato fijo y no se toca el backend.

## 7. Trampas conocidas

- **Contención antes que color.** Cada bloque dentro de una `.card`. Es el error
  que hundió el intento anterior; si una pantalla nueva no tiene tarjetas, la
  inversión de superficies la va a romper igual que la vez pasada.
- **La leyenda de la línea de tiempo no puede ser color solo** (§4.1), con ΔE 8.8
  entre "alerta" y "fallida" en visión normal.
- **No reordenar la paleta de `GroupedBars`** sin volver a correr el validador.
- **El delta de 30 s no se inventa en corridas terminadas.**
- **El visor degrada explícitamente** cuando no hay preview.
- La navegación es `HashRouter`: las rutas son `#/runs/:id`. Relevante para
  capturas y para cualquier enlace externo del guion de defensa.

## 8. Testing

Mismo arnés (Vitest + Testing Library). TDD por tarea, según la convención del
repo. Tests nuevos para las funciones puras de layout de cada gráfico (`layout.ts`)
y para la derivación de series desde `/trace` — son funciones puras y es donde vive
la lógica que puede estar sutilmente mal. Los tests de las 4 pantallas reescritas
se actualizan in-place; van a romper por diseño y esa rotura es la señal de que la
composición cambió.

Verificación visual obligatoria antes de dar por terminada cada pantalla: captura
con Chrome headless contra los servicios reales y comparación contra la pantalla
equivalente del prototipo. El validador chequea color, no layout.

## 9. Fuera de alcance

Las otras 7 pantallas (Nueva corrida, Experimentos, Conjuntos de prompts,
Catálogos, Plataforma, Cámaras, Clips), el tema claro (decisión del prototipo: no
existe y no se va a agregar), cualquier cambio de backend, y el desglose de frases
por backend en el editor de conjuntos de prompts (pregunta abierta del README del
prototipo, sin consumidor real hoy).
