# Inventario y archivo versionable de runs de evidencia — diseño

Fecha: 2026-08-13
Repo: `e-ovrt_experimental-setup`
Repos fuente hermanos: `e-ovrt_media-plane`, `e-ovrt_control-plane`, `docs`

## 1. Objetivo y definición de evidencia

Crear una única respuesta durable a la pregunta “¿qué runs sostienen los resultados del
proyecto?”. El inventario cubre los cuatro índices de `results/`: `bench_imagenes`,
`bench_nivel_a`, `clip_bench` y `realtime`. Incluye resultados principales, contrastes,
resultados negativos y validaciones; una corrida no deja de ser evidencia porque su configuración
haya rendido peor o haya refutado una hipótesis.

Un run pertenece al conjunto canónico únicamente si cumple al menos una de estas condiciones:

1. está referenciado por la procedencia de una campaña citable de `results/`;
2. aparece en un artefacto estructurado que sustenta una tabla o afirmación vigente de uno de los
   cuatro índices;
3. integra un par media/control EBE declarado explícitamente para una medición vigente;
4. sustenta un resultado negativo citado, siempre que el documento identifique el run y la causa.

La mera existencia de un directorio bajo cualquier `runs/` no implica inclusión. Quedan fuera los
smokes sin uso en resultados, intentos abortados sin hallazgo citado, diagnósticos exploratorios,
corridas supersedidas, fixtures y experimentos paraguas que no aporten un artefacto citado. No se
borra ningún original: “fuera del inventario” no significa “descartable”.

## 2. Alcance por familia

El manifiesto declara colecciones lógicas, aunque cada run se archive físicamente una sola vez:

- `dbe_datasets`: selección y comparación sobre imágenes, `bench_v2`, `bench_v3`, Nivel A y
  extensibilidad de clase nueva;
- `dbe_video`: las 14 campañas de `clip_bench`, incluidas T1, T2, D1, H1, B1, G1, R1–R6 e I1/I2;
- `ebe_realtime`: matriz modelo × fuente, integridad del bus, L0, rodaje, mediciones de throughput,
  descarte irregular, regresión/G1 live y claqueta con reloj externo;
- `shared`: runs que sostienen más de una colección, sin duplicar sus archivos.

Las campañas se descubren por contrato: todo directorio de `results/clip_bench/` o
`results/bench_nivel_a/` que tenga `metrics.json` debe estar declarado. Esto conserva la cobertura
16/16 actual y hace fallar la verificación si aparece una campaña nueva sin procedencia.

Para `bench_imagenes` y `realtime`, que hoy no tienen una campaña uniforme, el manifiesto enumera
las fuentes estructuradas vigentes y los grupos manuales estrictamente necesarios. El registro
inicial obligatorio es el siguiente; agregar o quitar una fuente requiere cambiar el YAML y deja
un diff revisable:

| Cobertura | Fuente de IDs o comprobación | Tratamiento |
|---|---|---|
| 14 campañas DBE de video | `results/clip_bench/*/provenance*.json` y `evals/*.json` | unión de todos los campos de media run soportados por el schema y de cada control run identificado por `alerts_path` |
| 2 campañas Nivel A | `results/bench_nivel_a/*/provenance*.json` | unión de runs por clip o por corrida |
| DBE de imágenes histórico | `docs/operacion/datos/31-benchmark-modelos-host-local.datos.json`, `s1_matrix_results_2026-07-23.jsonl`, `b5_rescore_partial_2026-07-23.jsonl` y `bench_v2_gdino560_eval_2026-07-23.json` | selectors estructurados independientes, con deduplicación por ID |
| Nivel A y clase nueva | `docs/operacion/datos/83-fase-d-nivel-a/runs.json`, `84-fase-d-nivel-a-base560/runs.json` y `94-piloto-clase-nueva/resultados.json` | selectors estructurados; `84` incorpora la réplica base-560 que no queda cubierta por el conjunto inicial de provenance |
| Matriz realtime y descarte live | `docs/operacion/datos/bench_realtime_person_2026-07-23.jsonl` y `101-descarte-live-distribucion.json` | selectors estructurados exactos |
| Controles del decimado empírico EBE | los 16 directorios `docs/operacion/datos/101-rt-*` declarados en el manifiesto | cada `eval_*.json` aporta el control run mediante `alerts_path`; la línea de base comprobada es 544 IDs únicos |
| EBE y mediciones realtime puntuales | documentos operativos `37`, `39`, `61`, `65`, `71`, `73`, `91` y `101` | listas manuales de IDs completos o selector estructurado cuando el artefacto lo permita; los pares se declaran juntos |
| Sustitutos de originales ausentes | el JSON crudo de `31`, los artefactos `37-*` / `39-*` y los 34 `evals/` de T1 | solo mediante `archived_only`, con razón explícita; cualquier imagen presente dentro de una fuente se excluye igualmente |

Los nombres relativos de la tabla se resuelven bajo el repo hermano `docs/operacion/`. El YAML
registra además cada fuente citada por las secciones “Dónde está cada número” de los cuatro índices,
con una disposición entre `run_selector`, `manual_runs`, `archived_artifact`,
`duplicate_crosscheck` o `methodology_only`. Las dos últimas no agregan runs y exigen una
justificación. De este modo, por ejemplo, un protocolo metodológico citado no genera corridas de
más, pero tampoco queda una fuente de resultados sin auditar.

Un grupo manual debe declarar cada ID completo, su documento de procedencia y el resultado que
sustenta; no se aceptan globs por fecha ni prefijos ambiguos. Los documentos pueden mencionar
intentos diagnósticos que no sostienen una cifra: excluirlos requiere una disposición explícita y
una razón, en lugar de omitirlos silenciosamente.

Los pares EBE se modelan con dos entradas relacionadas: `media_run_id` y `control_run_id`. Una
medición realtime solo de percepción o rendimiento puede tener únicamente media-plane; una
afirmación de integridad, alertas o política temporal exige ambos planos.

Las 14 campañas temporales DBE también exigen sus runs de control: actualmente los 434 archivos
`eval_*.json` identifican 434 `control_run_id` distintos mediante el directorio padre de
`alerts_path`. De ellos, 400 conservan su directorio completo bajo `docs/operacion/datos/*/`
`control_runs/`; los 34 de T1 apuntan a un scratchpad ya ausente y se registran como
`archived_only`, usando cada eval versionado como sustituto declarado. Estos conteos son una línea
de base comprobada por el generador, no constantes usadas para ocultar campañas futuras.

La prueba EBE de decimado empírico agrega 544 controles reales, resueltos desde 16 variantes
de `101-rt-*` y 34 clips por variante. Son una fuente estructurada distinta de los 434 controles
de las campañas temporales y se incluyen porque sostienen los resultados realtime citados. Tras
deduplicar todas las campañas, fuentes estructuradas y listas manuales, la línea de base del
2026-08-13 es de 1.430 runs únicos: 437 de media-plane y 993 de control-plane; 1.386 están
`copied` y 44 están `archived_only`.

## 3. Artefactos canónicos y layout

El punto de entrada vive junto a los índices de resultados:

```text
results/
├── evidence-runs.yaml               manifiesto humano y fuente de verdad
├── evidence-runs.md                 inventario legible generado
└── evidence-runs/
    ├── README.md                     uso, restauración y política de exclusión
    ├── collections/
    │   ├── dbe-datasets.csv          relaciones resultado ↔ run
    │   ├── dbe-video.csv
    │   ├── ebe-realtime.csv
    │   └── shared.csv
    ├── artifacts/
    │   ├── media-plane/<run_id>/
    │   ├── control-plane/<control_run_id>/
    │   └── archived-only/<evidence_id>/
    ├── resolved-runs.json             catálogo completo generado de IDs y relaciones
    ├── archive-files.json            hashes, tamaños y transformaciones por archivo
    └── files.sha256                  integridad del árbol versionable
```

`evidence-runs.yaml` declara colecciones, grupos, rol de evidencia, fuentes, selectors y pares EBE.
No contiene una segunda copia manual de los 273 IDs que actualmente se resuelven desde las 16
campañas: el generador los obtiene de `provenance*.json`. Ese valor es una línea de base, no el
total global; el total final también incorpora los IDs exclusivos de `bench_imagenes` y `realtime`.
Sí conserva listas explícitas cuando no existe procedencia estructurada.

`evidence-runs.md` presenta totales por colección y plano, campañas, grupos realtime, runs
compartidos, originales ausentes y exclusiones. Cada ID enlaza a su copia local y a la campaña o
documento que lo justifica. Los CSV permiten filtrar sin interpretar Markdown.

`resolved-runs.json` es el lock generado y exhaustivo: contiene todos los IDs resueltos, estado,
plano, relaciones y procedencias, ordenados de forma estable. Permite verificar una copia clonada
sin convertir los CSV o el Markdown en una segunda fuente manual.

## 4. Archivo de los runs

Cada run único se copia una sola vez bajo `artifacts/<plane>/<run_id>/`. Se conservan los
artefactos textuales que permiten auditar o recalcular resultados:

- `detections.jsonl`, `metrics.jsonl`, `dropped_units.jsonl` y `errors.jsonl`;
- `summary.json`, `run_manifest.json` y `run_provenance.json`;
- `alerts.jsonl`/`.csv`, `pattern_events.jsonl`, `pattern_progress.jsonl` y métricas de control;
- configuraciones efectivas seguras o su versión redactada;
- cualquier otro archivo de texto solo si su ruta o extensión está admitida explícitamente en el
  YAML.

La política por defecto admite solamente `.json`, `.jsonl`, `.csv`, `.yaml`, `.yml`, `.txt`,
`.log` y `.md`; una extensión desconocida falla salvo excepción nominal en el YAML. Todos los JSONL,
sin importar su tamaño, se guardan como `*.jsonl.gz` con gzip determinista (`compresslevel=9`,
`mtime=0` y nombre original vacío en el header). Los demás archivos admitidos quedan sin
comprimir. `archive-files.json` registra para cada archivo la ruta fuente, SHA-256 y tamaño
originales, ruta archivada, SHA-256 y tamaño archivados, además de `compression` y `redaction`. Así
se puede demostrar identidad aun cuando la representación versionada esté comprimida.

La sincronización nunca sobrescribe silenciosamente evidencia divergente. Si el mismo `run_id`
aparece en dos raíces con contenidos diferentes, falla y exige resolver la procedencia. Si los
contenidos son idénticos, se archiva una sola copia y se registran todas sus relaciones.

## 5. Exclusión de imágenes, video y secretos

No se copia ningún medio procesado. La exclusión combina nombre de directorio, extensión y
validación de contenido:

- directorios `previews/`, `frames/`, `images/`, `annotated/` y equivalentes declarados;
- imágenes `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.gif`, `.tif`, `.tiff`;
- video `.mp4`, `.avi`, `.mkv`, `.mov`, `.webm`, `.m4v`;
- payloads binarios o imágenes embebidas en base64, aunque tengan otra extensión.

El subdirectorio `results/evidence-runs/` lleva además un `.gitignore` defensivo para esas
extensiones y directorios. El guard principal sigue siendo el generador: `--check` inspecciona los
archivos realmente presentes y falla ante cualquier medio, incluso si Git lo ignora.

Antes de copiar texto se ejecuta un escaneo que no imprime valores sensibles. Se rechazan claves
de password/token/secret, URI con userinfo, claves privadas y credenciales conocidas. Una
`effective_config.yaml` con campos operativos sensibles se transforma en
`effective_config.redacted.yaml`: conserva modelo, prompts, thresholds y topología, reemplaza
únicamente valores sensibles por `[REDACTED]`, y registra el hash del original. Nunca se versionan
presets de cámara ni credenciales.

Los nombres de directorio prohibidos se mantienen como una lista cerrada en el YAML y en pruebas;
los “equivalentes declarados” no se infieren mediante coincidencias difusas. El scanner de
contenido es obligatorio aunque una ruta no coincida con esa lista. El límite de 95 MiB se aplica
a cada archivo en su representación versionada; si un original admitido no queda por debajo del
límite después de la transformación prevista, `sync` falla en lugar de omitirlo.

## 6. Estados de disponibilidad

Cada entrada resuelta termina en uno de estos estados:

- `copied`: original completo encontrado y copia verificada;
- `archived_only`: el directorio original ya no existe, pero hay evidencia derivada versionada en
  `docs/operacion/datos/`; se copia esa evidencia, se declara la ausencia y no se afirma disponer
  del run completo;
- `missing`: no existe ni original ni evidencia archivada suficiente; es un error bloqueante;
- `conflict`: hay más de un original no idéntico para el mismo ID; es un error bloqueante.

`archived_only` requiere una excepción explícita en el YAML, con el artefacto sustituto y su
justificación. Una excepción puede cubrir una campaña completa únicamente cuando los IDs se
resuelven de sus `evals/` versionados y cada eval es el sustituto de su propio control run, como en
T1. Las 44 excepciones actuales son exactamente los 34 controles T1, los seis runs históricos del
benchmark del documento 31 y cuatro runs históricos de los documentos 37/39. El generador no
degrada automáticamente `missing` a `archived_only`.

## 7. Generador y flujo de datos

`tools/evidence_runs.py` ofrece dos operaciones:

```bash
python3 tools/evidence_runs.py sync
python3 tools/evidence_runs.py --check
python3 tools/evidence_runs.py --check --archive-only
```

`sync` realiza, en orden:

1. carga y valida el YAML;
2. descubre las 16 campañas y verifica igualdad exacta con las declaradas;
3. extrae IDs desde todos los selectors estructurados y agrega los grupos manuales;
4. normaliza relaciones muchos-a-muchos entre resultado, colección, documento, plano y run;
5. resuelve los directorios fuente autorizados, detecta ausencias y conflictos;
6. escanea secretos y medios prohibidos;
7. construye el archivo en un directorio temporal dentro de `results/`;
8. genera Markdown, CSV, `archive-files.json` y `files.sha256`;
9. reemplaza el árbol de destino solo después de pasar todas las validaciones.

`--check` no escribe. Reconstruye el catálogo y los hashes esperados, y compara conjunto, contenido
y documentación con lo versionado. Informa IDs faltantes/sobrantes y rutas afectadas, pero nunca
valores secretos. Un directorio adicional bajo `artifacts/` es un fallo, incluso si existe como run
original: el archivo versionable debe ser exactamente el conjunto canónico.

El modo normal requiere las fuentes originales y es el guard usado para cerrar esta tarea.
`--archive-only` existe para un clon que ya no disponga de los `runs/` no versionados: valida el
lock, documentos generados, hashes, exclusiones y secretos del archivo, pero informa explícitamente
que no comparó contra originales y no sustituye al guard completo durante una sincronización.

`files.sha256` cubre todos los archivos generados dentro de `results/evidence-runs/`, salvo el
propio `files.sha256`. El orden de filas, claves serializadas y recorridos de archivos es estable,
de modo que dos ejecuciones sobre las mismas fuentes producen bytes idénticos.

El script descubre la raíz del workspace desde su propia ubicación; no fija
`/home/simonll4/projects` en el código. Las rutas almacenadas son relativas a repos hermanos, para
que el archivo pueda clonarse en otra ubicación.

Las raíces iniciales autorizadas quedan enumeradas exactamente en el YAML:
`e-ovrt_media-plane/runs`,
`e-ovrt_media-plane/.claude/worktrees/pil-roundtrip/runs` para la medición F-RT5 que hoy vive en
ese worktree, `e-ovrt_control-plane/runs` y los directorios `control_runs/` exactos resueltos desde
los `alerts_path` de las campañas bajo `docs/operacion/datos/`. En este último caso no se hace una
búsqueda global: cada ruta debe ser la normalización portable de una referencia de un eval. El
generador no recorre otros worktrees ni directorios por descubrimiento implícito. Una raíz futura
requiere una entrada explícita y revisable.

## 8. Pruebas y guards

Las pruebas unitarias usan árboles temporales pequeños y cubren:

- extracción de todos los campos de procedencia usados por T1–I2 y Nivel A;
- extracción de control runs desde `alerts_path`, normalización portable de rutas bajo `docs/` y
  los 34 sustitutos T1;
- inclusión de resultados negativos y relación compartida sin duplicar archivos;
- campaña nueva no declarada y campaña declarada inexistente;
- ID faltante, ID extra, duplicado idéntico y conflicto no idéntico;
- par EBE completo y falta de uno de sus planos;
- gzip determinista y restauración byte a byte;
- exclusión por directorio, extensión, MIME y base64 embebido;
- rechazo de credenciales y redacción de configuración;
- detección de Markdown/CSV/copia desactualizados;
- estado `archived_only` solo mediante excepción explícita;
- rutas relativas y ejecución desde otro directorio de trabajo.

La verificación de integración sobre el workspace exige además:

1. cobertura exacta de los cuatro índices de resultados;
2. cobertura 16/16 de las campañas con `metrics.json`;
3. igualdad entre todos los IDs resueltos, el catálogo y los directorios archivados;
4. cero imágenes, videos, presets o secretos en el árbol versionable;
5. todos los hashes válidos y ningún archivo individual fuera del límite configurado de 95 MiB;
6. `git diff --check` limpio en los archivos modificados.

`results/index.md` enlaza al inventario y explica que este reemplaza cualquier listado informal.
`results/clip_bench/README.md` conserva su explicación de provenance y enlaza al archivo común.

## 9. Versionado y operación futura

Los `runs/` originales continúan gitignorados en sus repos. Solo el archivo curado bajo
`results/evidence-runs/` es versionable. Agregar un resultado exige actualizar su procedencia o el
grupo correspondiente, ejecutar `sync`, revisar el diff y ejecutar `--check`; copiar un directorio
a mano no lo vuelve evidencia.

El `README.md` raíz se actualiza para documentar esta excepción deliberada a su regla histórica de
no versionar salidas de `runs/`: no se versiona ningún directorio original, sino solo el subconjunto
textual curado, escaneado y reproducible de este diseño.

No se crea ningún commit como parte de esta tarea. Los archivos quedarán preparados para que el
usuario decida cuándo y cómo versionarlos. El tamaño se controla mediante gzip determinista y el
límite por archivo; no se introduce Git LFS.

## 10. Criterio de terminado

El trabajo termina cuando una persona puede abrir `results/evidence-runs.md`, identificar todos los
runs que sostienen cualquier resultado DBE o EBE, navegar a sus copias sin encontrar medios
procesados, y reproducir el inventario con un único comando. La ejecución de `--check` debe probar
simultáneamente que no falta ningún run declarado, que no hay ninguno de más, que las copias no
derivaron y que el archivo no contiene imágenes, video ni secretos.
