# Campaña de medición de `t_alert-notification` — diseño

Fecha: 2026-08-13  
Repo dueño de la campaña: `e-ovrt_experimental-setup`  
Repos participantes: `e-ovrt_control-plane`, `e-ovrt_alert-distribution`,
`e-ovrt_media-plane` y `e-ovrt_datasets`  
Normativa: spec 45, ADR-016, concreción 92b y relevamiento operativo 114.

## 1. Objetivo

Obtener una cifra citable y reproducible de `t_alert-notification` para el informe final. La
métrica se limita al tramo que comienza cuando el control-plane publica una alerta confirmada en
el bus y termina cuando el broker MQTT confirma la entrega QoS 1 mediante PUBACK:

```text
t_alert-notification = puback_wall_ms - ts_publish_ms
```

La campaña no vuelve a evaluar la calidad del detector ni la corrección temporal de las alertas.
Esos resultados ya tienen campañas propias. Aquí se mide la distribución de alertas y se verifica
que su resultado llegue al reporte consolidado.

## 2. Decisión metodológica

Se adopta una campaña híbrida con tres capas de evidencia:

1. replay DBE de todo el archivo elegible, como preflight funcional;
2. republicación live controlada del corpus histórico, como medición cuantitativa principal;
3. corridas integradas desde video y un smoke con cámara, como validación de que la medición
   controlada representa el acople real de la plataforma.

La alternativa de medir solo con cámara se descarta como fuente principal porque produciría pocas
alertas y agregaría variabilidad de captura e inferencia fuera del tramo medido. La alternativa de
usar solo replay se descarta porque no puede producir `latency_mode: live`.

## 3. Evidencia de entrada

La fuente canónica es `results/evidence-runs/resolved-runs.json`, validada junto con el archivo
curado mediante:

```bash
python3 tools/evidence_runs.py --check --archive-only
```

Estado auditado al diseñar la campaña:

| Grupo | Runs de control copiados | Runs con alertas | Alertas válidas |
|---|---:|---:|---:|
| Campañas DBE | 400 | 346 | 823 |
| EBE históricas no derivadas | 13 | 10 | 13 |
| Replays de decimado empírico | 544 | 440 | 574 |
| **Total copiado** | **957** | **796** | **1.410** |

Las 1.410 alertas validan contra el contrato actual consumido por
`NotificationEnvelope.from_alert`; sus 1.410 `alert_id` son únicos y no hay eventos idénticos
duplicados.

Quedan fuera como eventos crudos los 36 runs de control `archived_only`, incluidos los 34
controles de T1 y los dos controles históricos de paridad live, porque no conservan un
`alerts.jsonl` recuperable en el archivo curado.

Los 544 replays de decimado empírico son evidencia derivada. Se procesan como cobertura
suplementaria, pero no se cuentan como 544 nuevas observaciones EBE ni se incorporan al agregado
live principal.

## 4. Semántica de los relojes

El origen histórico de una alerta no determina el modo de su nueva entrega:

| Ejecución actual | Inicio temporal disponible | `latency_mode` | Uso |
|---|---|---|---|
| `replay` desde JSONL | inicio local del intento | `wall_clock_dbe` | diagnóstico funcional |
| consumo de `bus.envelope.v1` | `ts_publish_ms` nuevo | `live` | cifra operacional |

Los `alerts.jsonl` históricos no conservan el `ts_publish_ms` de su bus original. Por eso no se
intenta reconstruir una latencia pasada ni restar el timestamp del episodio al reloj actual.

Para la campaña live, el publisher vigente del control-plane envuelve nuevamente cada
`control.alert.v1` y asigna `ts_publish_ms` inmediatamente antes de publicarlo. El distribuidor
consume ese envelope sin modificarlo y el final se toma después del PUBACK real informado por
Paho MQTT.

Esta medición representa exactamente `alert bus -> PUBACK`. No representa la latencia completa
sensor -> notificación, que se compone por separado con las métricas de los tramos anteriores.

## 5. Topología de ejecución

La topología single-host será:

```text
publisher control-plane (:5558)
    -> eovrt-distribute live
    -> broker MQTT real (127.0.0.1:1883, QoS 1)
    -> suscriptor testigo
    -> PUBACK y DeliveryRecord
```

Se utilizará aMQTT, el broker real ya documentado y verificado para la topología host de la
plataforma. El plan fijará una versión exacta en un entorno aislado; esa versión y la configuración
quedan registradas en la procedencia. Cambiar a Mosquitto requeriría declarar y repetir la campaña,
no sustituir el broker en mitad de la medición. No se usa el broker mínimo de prueba del
relevamiento 114 para la cifra final.

El suscriptor testigo confirma readiness antes del primer publisher, observa `eovrt/alerts/#` y
persiste cada payload recibido. Su conjunto de `notification_id` es una evidencia independiente
del ledger del distribuidor. Como QoS 1 admite duplicados, también registra multiplicidad: se exige
que toda entrega esté presente al menos una vez y que no aparezcan IDs inesperados, no igualdad
ciega entre cantidades de líneas.

## 6. Fase A — preflight DBE funcional

Se procesan los 957 runs copiados, incluidos los 161 que no contienen alertas. Cada run se ejecuta
por separado con:

- entrada descomprimida de su `alerts.jsonl.gz` curado;
- configuración de política y canal congelada para la campaña;
- directorio de salida y ledger nuevos;
- primera pasada normal;
- segunda pasada sobre el mismo ledger para verificar idempotencia.

Esta fase verifica:

- lectura de 1.410 alertas válidas;
- cero alertas malformadas o inválidas;
- policy/cooldown sobre los timestamps de media originales;
- outcomes exhaustivos;
- segunda pasada sin reentrega de las notificaciones ya entregadas;
- manejo explícito de runs sin alertas.

Las latencias de esta fase se etiquetan `wall_clock_dbe` y quedan excluidas de toda cifra live.

## 7. Fase B — campaña live principal

### 7.1 Corpus principal

Se republican, run por run:

- 400 runs de campañas DBE, con 823 alertas;
- 13 runs EBE históricos no derivados, con 13 alertas.

El universo declarado es de 413 runs, 356 de ellos con alertas y 836 eventos candidatos. Los 57
runs vacíos también emiten el sentinel de cierre y validan el ciclo de vida, pero no aportan
muestras de latencia.

### 7.2 Aislamiento por run

Cada run usa:

- un proceso de distribución nuevo;
- un directorio `out_dir` nuevo;
- un ledger vacío;
- un publisher con secuencia propia;
- los valores originales de `control_run_id`, `experiment_id`, `source_id`, `condition_id`,
  `media_timestamp_ms` y `alert_id`;
- un `ts_publish_ms` generado en la republicación;
- un `run_finished` al terminar el archivo.

No se concatenan runs. Hacerlo compartiría el estado de cooldown entre experimentos que nunca
coexistieron y alteraría los outcomes.

El broker puede permanecer activo durante toda la campaña. El distribuidor sigue teniendo el
ciclo de vida real de un proceso por corrida y su cliente MQTT se conecta de forma perezosa en la
primera entrega permitida.

### 7.3 Corpus suplementario

Los 544 replays de decimado empírico se ejecutan en una serie separada con las mismas garantías.
Sus resultados sirven para ampliar la cobertura contractual y observar comportamiento bajo menor
densidad de evidencia. No se mezclan con el agregado principal ni se presentan como replicaciones
independientes del camino EBE.

## 8. Fase C — validación integrada desde video

Se repite tres veces una corrida completa:

```text
video local
  -> media-plane
  -> bus de detecciones :5557
  -> control-plane
  -> bus de alertas :5558
  -> distribución
  -> broker MQTT/PUBACK
  -> report.json
```

El clip inicial seleccionado es `a_p1_c08.mp4` del banco congelado. Dura 23,633 segundos y en la
campaña R4 (`subject`, `stride: 15`) produjo históricamente dos alertas. Esa densidad es compatible
con la caracterización del camino realtime y reduce el costo de inferencia sin crear una nueva
condición experimental.

Antes de las tres repeticiones se realiza una corrida de admisión. Si no produce al menos una
alerta válida con las versiones y configuraciones congeladas, no se fuerza el resultado: se
registra la causa y se selecciona, mediante una regla previa, el primer clip elegible de esta lista:

1. `a_p7_c02.mp4` — tres alertas históricas en R4;
2. `a_p6_c01.mp4` — tres alertas históricas en R4.

La selección final y cualquier desvío quedan en la procedencia. No se elige post hoc el clip con
la latencia más favorable.

Las tres corridas integradas no se fusionan silenciosamente con el corpus republicado. Se reportan
como contraste separado y deben demostrar que:

- el runner inicia distribución antes de que control publique alertas;
- el cierre ocurre por `run_finished`;
- `bus_dropped_events = 0`;
- el broker recibe las notificaciones;
- `distribution_summary.json` contiene latencia `live`;
- `report.json` publica `t_alert-notification` como `computed`.

## 9. Fase D — smoke con cámara

Se ejecuta una única prueba suplementaria con la cámara disponible. No se requieren casco ni
chaleco: una persona visible sin esos elementos genera justamente las condiciones CR-01/CR-02.

Protocolo:

1. ambiente controlado y una sola persona;
2. control y distribución suscriptos antes de iniciar media;
3. permanencia visible sin casco ni chaleco durante 15 a 20 segundos;
4. espera de al menos una alerta y su PUBACK;
5. cierre normal de la corrida y preservación de los artefactos textuales.

No se representa una obra ni se induce una actividad peligrosa. Esta prueba solo demuestra el
camino sensor -> notificación en el entorno disponible. Por su muestra pequeña y no controlada,
sus latencias no entran en el p95 principal ni sostienen una afirmación de rendimiento.

## 10. Agregación estadística

La unidad del agregado principal es un `DeliveryRecord` que satisfaga simultáneamente:

- pertenece al corpus principal de la fase B;
- `outcome == "delivered"`;
- `mode == "live"`;
- `latency_mode == "live"`;
- `talert_notification_ms` es finito y no negativo;
- su `notification_id` fue observado al menos una vez por el suscriptor testigo.

El p95 se calcula sobre todos los registros individuales elegibles mediante la misma convención
nearest-rank del distribuidor: `ceil(0.95 * n) - 1` sobre valores ordenados. No se promedian p95 de
runs individuales.

Se publican como mínimo:

- cantidad de runs totales, runs con alertas y entregas elegibles;
- `min`, media, p50, p95, p99 y máximo;
- conteos por outcome;
- alertas inválidas, mensajes malformados y drops del bus;
- distribución del tamaño de payload;
- p95 separado para origen histórico DBE y EBE, solo como análisis de sensibilidad;
- resultados de las tres corridas integradas y del smoke de cámara, por separado.

La cifra primaria incluye la primera conexión MQTT de cada run: ese costo pertenece al ciclo real
del distribuidor por experimento. Un análisis steady-state que excluya la primera entrega solo
puede aparecer como secundario si conserva una muestra suficiente y declara cuántos runs quedan
excluidos; nunca reemplaza al resultado primario.

No se fija un umbral de aprobación post hoc. La campaña produce una medición descriptiva y sus
condiciones de validez.

## 11. Gates de aceptación

### Preflight DBE

- 957 runs resueltos y procesados;
- 1.410 alertas leídas y válidas;
- cero `skipped_malformed` y cero `skipped_invalid_alerts`;
- ninguna latencia DBE incorporada al agregado live;
- segunda pasada sin reentrega de una clave ya entregada.

### Campaña live principal

- 413 runs ejecutados, incluidos 57 vacíos;
- 836 eventos publicados o contabilizados por una causa explícita;
- terminación de todos los runs por `run_finished`, no por timeout;
- cero `bus_dropped_events`;
- cero `dead_letter` para aceptar la cifra primaria;
- cada `failed` intermedio termina en `delivered`, se conserva y se informa; su retry forma parte
  de la latencia, por lo que no se elimina la muestra;
- toda entrega aparece en el suscriptor y no hay `notification_id` inesperados; los duplicados
  MQTT se cuentan aparte;
- toda entrega elegible con `latency_mode: live`.

Un `suppressed_cooldown` no es una falla: es un outcome esperado de política y no genera una
muestra de latencia. Un run vacío tampoco es una falla.

Si aparece un `dead_letter`, un `failed` sin entrega posterior, un drop, un timeout o una
discrepancia de IDs, la campaña queda inválida para citación hasta diagnosticar la causa y
repetirla completa. No se eliminan intentos ni muestras fallidas para mejorar el p95.

### Validación integrada

- tres repeticiones exitosas del mismo manifiesto aprobado;
- al menos una entrega con PUBACK por repetición;
- reporte consolidado con `t_alert-notification` `computed`;
- configuración efectiva y commits registrados.

### Cámara

- al menos una alerta entregada o un resultado negativo documentado con causa;
- sin drops ni cierre forzado si se usa como evidencia positiva;
- resultado siempre separado del agregado cuantitativo.

## 12. Artefactos y procedencia

Los directorios completos de ejecución permanecen fuera de versión bajo un área de trabajo
ignorada. La evidencia curada se publica en:

```text
results/realtime/t_alert_notification/
├── README.md
├── campaign.yaml
├── corpus.json
├── provenance.json
├── metrics.json
├── outcomes.csv
├── integrated-runs.json
└── camera-smoke.json
```

`provenance.json` registra como mínimo:

- commit y estado dirty de cada repo participante;
- hash de este diseño y del plan de ejecución;
- hash de `resolved-runs.json` y de la configuración de campaña;
- sistema operativo, Python, Paho MQTT, pyzmq y broker/versiones;
- CPU/GPU relevantes y política de energía disponible;
- reloj, zona horaria y orden de arranque;
- run IDs, selección de corpus y exclusiones con causa;
- comandos de verificación y códigos de salida.

Los artefactos curados no contienen video, imágenes, previews, pesos, presets de cámara,
credenciales ni el árbol completo de `runs/`.

## 13. Implementación necesaria antes de ejecutar

La campaña requiere tooling reproducible dentro de `e-ovrt_experimental-setup`, no cambios en la
semántica productiva de los servicios:

- selector determinista del corpus desde `resolved-runs.json`;
- staging temporal y descompresión segura de `alerts.jsonl.gz`;
- publisher live que reutilice `AlertBusPublisher` del control-plane;
- orquestador por run con readiness, sentinel y directorios aislados;
- suscriptor MQTT testigo;
- agregador con validación de invariantes y generación de evidencia curada;
- manifiesto integrado para el clip elegido y protocolo de cámara;
- tests unitarios con fixtures sintéticos y un smoke local antes de la campaña completa.

No se modifica el `AlertEvent`, `bus.envelope.v1`, `NotificationEnvelope`, `DeliveryRecord`, la
política de cooldown ni el cálculo de latencia del distribuidor.

## 14. Fuera de alcance

- volver a medir calidad de detección o F1 temporal;
- mezclar `wall_clock_dbe` con latencia operacional;
- atribuir a las republicaciones la latencia histórica de los runs originales;
- usar el smoke de cámara para afirmar generalización a obra real;
- desplegar un historial global, anti-drift, promoción asistida o una UI nueva;
- crear un servicio persistente de métricas o distribución;
- modificar campañas históricas o sus artefactos canónicos.

## 15. Criterio de cierre

La campaña se considera cerrada cuando existe una cifra principal reproducible con sus conteos,
condiciones y procedencia; las tres corridas integradas confirman el mismo tramo dentro de la
plataforma; el smoke de cámara está documentado; y el generador de reporte consume al menos una
corrida integrada sin reinterpretar una latencia DBE como live.

Si el gate live no se cumple, el resultado correcto es una campaña inválida con causa, no una
cifra parcial presentada como definitiva.
