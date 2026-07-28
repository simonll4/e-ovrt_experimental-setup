# Rediseño visual de la consola web — diseño

## Contexto

El equipo de diseño produjo un prototipo navegable (`rediseno-consola-eovrt/prototipo.html`,
fuera de este repo) con las once pantallas de la webconsole rediseñadas: paleta oscura de
cinco superficies, separación violeta=acción / azul=en-curso, seis colores de estado
recalibrados a contraste ≥4,5:1, densidad de consola (filas de 32px), tipografía monoespaciada
para identificadores y un glosario que unifica terminología (español/inglés/código) en toda
la interfaz.

El README del prototipo también lista diez cambios de backend que el equipo de diseño asumió
como necesarios (índice de actividad completo para la traza, vocabulario cerrado de motivos
`control`, nombres legibles de condición, "corrida anterior comparable", filtro/orden/paginación
server-side, motivo de deshabilitado en plugins, fecha de creación de corrida, más campos en el
listado de experimentos, esquema fijo de reporte, diff de derivación de conjuntos de prompts).
**Decisión explícita del usuario: ese listado no es la fuente de verdad.** No se toca el
backend; el diseño se adapta a los datos que la API ya expone hoy. Un agente de exploración
auditó `webconsole/frontend/src` y `types.ts`/`api.ts` contra esa lista; los resultados de esa
auditoría son la base de la sección 4 (huecos y resoluciones).

El prototipo se usa como **referencia visual**, no como código: es HTML/CSS/JS autónomo con
templating de strings, no componentes React. Los componentes se escriben desde cero siguiendo
los patrones ya existentes del frontend actual.

**Propósito**: esta consola es la evidencia que se muestra al jurado de la defensa de tesis
(fin de septiembre 2026). El objetivo del rediseño es que esa evidencia —corridas, alertas,
comparaciones entre modelos— se lea de forma ordenada y sea fácil de seguir en vivo durante
la defensa.

## Alcance

Rediseño visual completo de `e-ovrt_experimental-setup/webconsole/frontend`. Sin cambios de
backend. Se construye una base de una sola vez (tokens, primitivas, glosario, shell) y luego
se re-viste cada pantalla en el orden de prioridad confirmado por el usuario, de mayor a menor
visibilidad ante el jurado:

1. Corridas
2. Detalle de corrida
3. Comparar
4. Experimentos
5. Detalle de experimento
6. Conjuntos de prompts, Catálogos, Plataforma, Cámaras, Clips (resto, menor prioridad)

Cada pantalla queda entera y funcional al terminar su fase — si el tiempo se acaba antes de
llegar al final de la lista, lo ya hecho es un subconjunto coherente y terminado, no once
pantallas a medio hacer.

## 1. Arquitectura

Sin cambios estructurales: misma SPA Vite/React, mismos `pages/` + `components/` +
`api.ts`/`types.ts` como cliente del BFF. El rediseño es aditivo: tokens nuevos, primitivas
nuevas, un módulo de glosario nuevo, y pantallas revestidas in-place, una fase a la vez. El
único cambio en el flujo de datos son las adaptaciones puntuales de la sección 4 (todas del
lado del cliente).

## 2. Tokens de diseño y primitivas (base, se construye una sola vez)

- Reescribir `styles/tokens.css` al sistema de cinco superficies del prototipo: lienzo
  (`#121211`) más oscuro que tarjeta (`#1a1a19`) —invertido respecto del esquema actual de
  tres superficies— más los niveles elevado, emergente y hundido.
- Separar el acento: violeta `#7d6ef2` = acción/selección/foco/navegación activa; azul
  `#4b95e8` reservado solo para el estado "en curso". Hoy ambos comparten un azul —ese es el
  bug visual concreto que corrige el rediseño (un botón primario y una corrida activa se ven
  iguales).
- Recalibrar los seis colores de estado (en curso / completada / degradada / alerta / fallida
  / sin dato) según la tabla del README del prototipo, cada uno con variante de relleno 15% y
  borde 40% para chips y bandas de fila. Texto `#f2f1ed`, nunca blanco puro. Nunca color solo:
  todo estado lleva icono + texto.
- Densidad de consola: filas de 32px con borde inferior (no tarjeta por fila), monoespaciada +
  cifras tabulares para identificadores y columnas numéricas.
- Primitivas nuevas en `components/ui/`: `Button`, `Select` (propio, con soporte de opción
  deshabilitada + motivo), helpers de fila/encabezado de `Table`. Estas no existen hoy, son
  archivos nuevos, no ediciones. `Badge`/`Card`/`StatTile`/`DetChip` se extienden al nuevo
  sistema de color de estado.

## 3. Módulo de glosario (base)

Módulo de etiquetas nuevo (extendiendo `runview.ts`/`traceview.ts`, que ya son la capa de
presentación correcta) con:

- Diccionario de términos de interfaz (run→corrida, media-plane→motor de detección,
  control-plane→motor de reglas, frame→cuadro, trace→traza, received/dropped:rate_gate/
  dropped:overload/not_received→etiqueta traducida, etc.) según la tabla de glosario del
  prototipo.
- Un formateador **resiliente** para motivos de `control`: como no hay un enum cerrado real del
  backend, un código no reconocido cae a mostrar el código crudo en monoespaciada —nunca en
  blanco silencioso, nunca una cadena en inglés filtrada como prosa.
- Un mapa de nombres legibles de condición CR-01/CR-02 propio del frontend (`CR-01 —
  Presencia de persona sin casco`, `CR-02 — Presencia de persona sin chaleco`), porque el
  backend no lo manda. Códigos/ids/nombres de archivo/clases nunca se traducen y van siempre
  en monoespaciada, según las dos excepciones del glosario original.

## 4. Huecos frente al prototipo y su resolución (sin tocar backend)

| Asunción del prototipo | Estado real (auditado) | Resolución |
|---|---|---|
| Índice completo de actividad para la traza | Solo hay páginas (`getTrace`/`getDetections` paginados, `TraceTotals` agregado pero sin timeline) | Al abrir el detalle de corrida, se piden todas las páginas de `/trace` en secuencia y se arma el índice completo en el cliente (elegido por el usuario; válido para duraciones de minutos como las de esta tesis) |
| Vocabulario cerrado de `control` | Strings libres, sin enum garantizado | Formateador con fallback a código crudo monoespaciado para valores no reconocidos |
| Nombres legibles de condición | Solo códigos `CR-01`/`CR-02` crudos, ningún mapeo existente | Mapa de nombres propio del frontend (sección 3) |
| "Corrida anterior comparable" | No existe en ningún lado de la API (`ExperimentRunState` no tiene baseline, no hay `previous_run_id`) | No se implementa; Comparar sigue siendo el mecanismo manual y deliberado, sin cambios funcionales |
| Filtro/orden/paginación server-side de corridas | `listRuns()` trae todo, filtro/orden actual es client-side | Se mantiene client-side (la escala de datos de esta tesis lo permite) |
| Motivo de deshabilitado en plugins de ingesta | `IngestPlugin.enabled` es booleano, con `description` libre | El motivo se deriva del campo `description` existente cuando `enabled === false`; si no hay descripción, mensaje genérico "no soportado" |
| Fecha de creación de corrida | **Ya existe** (`RunRow.started_at`) | Sin hueco, se usa directamente |
| Más campos en listado de experimentos (grupo, último estado, cantidad de corridas, fecha) | `ExperimentManifestSummary` solo trae `slug`/`experiment_id`/`description`/`group` | Se muestra solo `group` (lo único que existe); no se agregan columnas de estado/cantidad/fecha inventadas — esos datos siguen disponibles por experimento individual en el detalle |
| Diff de derivación de conjuntos de prompts | `derives_from` es solo el id del padre; `changes` es texto libre, no hay diff estructural | Se muestra el `changes` existente como texto; sin vista de diff en este ciclo |
| Esquema fijo de reporte de experimento | Lectura tolerante `row.name ?? row.metrica ?? row.metric` sigue siendo necesaria (no hay contrato fijo) | Se mantiene la lectura tolerante; se limpia la presentación vía glosario (nombres de métrica en español + AP@0.5 entre paréntesis) |

## 5. Shell / navegación (base)

`components/Shell.tsx`: barra lateral colapsable + barra superior para pantallas chicas. Los
8 ítems de navegación actuales ya cubren 10/11 pantallas como rutas (los detalles de corrida y
experimento son derivados de las migas, no ítems propios) — no hacen falta rutas nuevas.

## 6. Pantallas, en el orden de prioridad confirmado

1. **Corridas** (`RunsPage.tsx`): filas densas de 32px, chips de estado (icono+texto+color),
   monoespaciada para `run_id`/timestamps, `Select` nuevo para filtros. Filtro/orden/paginación
   se mantienen client-side.
2. **Detalle de corrida** (`RunDetailPage.tsx`, `TraceSection.tsx`): revestimiento completo;
   línea de tiempo armada trayendo todas las páginas de `/trace` al abrir (sección 4); banner
   de condición vía el mapa de nombres CR-01/CR-02; motivos de descarte vía el formateador
   resiliente.
3. **Comparar** (`ComparePage.tsx`): aviso de `bench_split` distinto (el dato ya se carga hoy,
   sin hueco), nombres de condición vía glosario, barras/sparklines revestidas a los tokens
   nuevos.
4. **Experimentos + Detalle de experimento** (`ExperimentsPage.tsx`,
   `ExperimentDetailPage.tsx`): el listado muestra solo los campos que el endpoint de
   manifiestos realmente trae (sección 4); el detalle mantiene su lectura tolerante de reporte
   pero con nombres de métrica limpios.
5. **Resto** (Conjuntos de prompts, Catálogos, Plataforma, Cámaras, Clips): revestimiento
   visual —tokens/glosario/densidad— sin cambios funcionales, ya que funcionan bien con los
   datos actuales. Diff de conjuntos de prompts y motivo de deshabilitado de plugins,
   simplificados según sección 4.

## 7. Manejo de errores

`ErrorBanner`/`EmptyState` se extienden a los tokens nuevos, no se reemplazan en su lógica. La
adaptación de "traer todas las páginas de traza" introduce un modo de falla nuevo: si falla
una página a mitad de camino, se muestra un banner ("línea de tiempo incompleta: no se
pudieron cargar todos los cuadros") pero se sigue renderizando lo que sí cargó, en vez de
bloquear toda la pantalla.

## 8. Testing

Mismo arnés (Vitest + Testing Library, `src/__tests__/*`). Tests nuevos para las primitivas
(`Button`/`Select`/`Table`) y para el módulo de glosario (mapa de términos + fallback de
código no reconocido, como funciones puras). Los archivos de test existentes de cada pantalla
se actualizan in-place a medida que se hace cada fase (no se reescriben desde cero); las
aserciones sobre texto visible van a necesitar ajustes donde el glosario traduce strings (p.
ej. `"CR-01"` solo → `"CR-01 — Presencia de persona sin casco"`).

## Qué no está en este ciclo

- Ningún cambio de backend/BFF.
- Filtro/orden/paginación server-side.
- Diff estructural de derivación de conjuntos de prompts.
- Columnas de estado/cantidad de corridas/fecha en el listado de experimentos (no hay datos
  agregados para eso).
- "Corrida anterior comparable" automática (Comparar sigue siendo manual).
