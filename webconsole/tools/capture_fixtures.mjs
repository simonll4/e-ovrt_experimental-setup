// Datos HTTP sintéticos para comparar presentación. No son evidencia experimental
// ni sustituyen el seed de corridas ejecutadas por el media-plane: viven sólo en
// la memoria de cada escenario y nunca tocan el BFF real.
//
// `crearMundo(variante)` arma un estado propio por escenario. `responder()`
// resuelve cada petición por método, pathname, query y cuerpo; lo que no está
// declarado devuelve `null` y el capturador hace fallar el escenario. Las
// mutaciones (borrar, lanzar, guardar…) modifican sólo ese estado y quedan en
// `mundo.log`.

export const FECHA = '2026-09-09T12:00:00Z'
const hora = (h, m = 0) => `2026-09-09T${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:00Z`

// PNG 4×3 gris: alcanza para que una vista previa sea una imagen real.
export const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAQAAAADCAIAAAA7ljmRAAAAE0lEQVR4nGNoaGhgQAMMDAwMDAAoBgKBFeHVnwAAAABJRU5ErkJggg==',
  'base64',
)

const model = (ref = 'gdino-tiny-560') => ({
  ref, name: `${ref} [qa]`, adapter: 'grounding_dino', device: 'cuda:0',
  thresholds: { confidence: 0.3, iou: 0.5, box: 0.35, text: 0.25 }, runtime: {},
})
const plano = (url, extra = {}) => ({ service_url: url, healthy: true, ready: true, ...extra })

const evidencia = (ids, clase = 'resultado') => ({
  is_evidence: ids.length > 0, result_ids: ids, collections: ids.length ? ['clip_bench'] : [], clase,
})

/** Corridas: suficientes para paginar (25 por página), con todos los estados y
 *  nombres largos. */
function corridasBase() {
  const base = [
    {
      run_id: 'run_20260909_090000_obra', name: 'Inspección de obra — frente norte [qa]', status: 'succeeded',
      created_at: hora(9), model: 'gdino-tiny-560', source_type: 'image_folder', prompt_set_id: 'cr01_cr02_v2_short',
      fps_effective: 12.4, total_detections: 318, duration_seconds: 21.3, bench_split: 'bench_v3', evaluated: true,
      evidence: evidencia(['clip_bench/t1_gdinotiny560_v2short_scene', 'realtime/claqueta']),
    },
    {
      run_id: 'run_20260909_115500_vivo', name: 'Cámara del portón en vivo', status: 'running', live: true,
      created_at: hora(11, 55), model: 'gdino-tiny-560', source_type: 'rtsp', prompt_set_id: 'cr01_cr02_v2_short',
      fps_effective: 9.8, total_detections: 41, duration_seconds: null, evidence: evidencia([]),
    },
    {
      run_id: 'run_20260909_080000_video', name: 'Video del rodaje sin conjunto de evaluación', status: 'succeeded',
      created_at: hora(8), model: 'yoloe-v8s', source_type: 'video_file', prompt_set_id: 'eind_v1',
      fps_effective: 24.1, total_detections: 1203, duration_seconds: 63.5, bench_split: null, evaluated: false,
      evidence: evidencia([], 'sin_clasificar'),
    },
    {
      run_id: 'run_20260909_070000_falla', name: null, status: 'failed', created_at: hora(7), model: 'owlv2-base',
      source_type: 'oak_d', prompt_set_id: 'cr01_cr02_v2_short', fps_effective: null, total_detections: null,
      duration_seconds: 2.1, evidence: evidencia([], 'ensayo'),
    },
    {
      run_id: 'run_20260909_063000_detenida_con_un_identificador_muy_largo_para_probar_el_corte', name: null,
      status: 'stopped', created_at: hora(6, 30), model: 'gdino-tiny-560', source_type: 'rtsp',
      prompt_set_id: 'cr01_cr02_v2_short', fps_effective: 8.2, total_detections: 12, duration_seconds: 300,
      evidence: evidencia([], 'instrumento'),
    },
  ]
  const comparables = Array.from({ length: 9 }, (_, i) => ({
    run_id: `run_20260908_${String(10 + i).padStart(2, '0')}0000_bench`,
    name: i === 0 ? 'Barrido diurno con prompt corto y umbral de caja ajustado para el banco congelado' : `Banco ${i + 1}`,
    status: 'succeeded', created_at: `2026-09-08T${String(10 + i).padStart(2, '0')}:00:00Z`,
    model: i % 2 ? 'yoloe-v8s' : 'gdino-tiny-560', source_type: 'image_folder', prompt_set_id: 'cr01_cr02_bench_v2',
    fps_effective: 10 + i, total_detections: 200 + i * 7, duration_seconds: 30 + i,
    bench_split: i === 8 ? 'bench_v2_val' : 'bench_v3', evaluated: true, evidence: evidencia(['clip_bench/t1_gdinotiny560_v2short_scene']),
  }))
  const relleno = Array.from({ length: 20 }, (_, i) => ({
    run_id: `run_20260901_${String(i).padStart(2, '0')}0000_hist`, name: i % 3 ? null : `Histórico ${i}`,
    status: i % 7 === 3 ? 'failed' : 'succeeded', created_at: `2026-09-01T${String(i).padStart(2, '0')}:00:00Z`,
    model: 'gdino-tiny-560', source_type: 'image_folder', prompt_set_id: 'cr01_cr02_v2_short',
    fps_effective: 11.5, total_detections: 90 + i, duration_seconds: 18 + i, evidence: evidencia([], 'sin_clasificar'),
  }))
  return [...base, ...comparables, ...relleno]
}

const grupos = () => [
  {
    result_id: 'clip_bench/t1_gdinotiny560_v2short_scene', titulo: 'Línea de base del Nivel B', etiqueta: 't1 gdinotiny560 v2short scene',
    cifra: '0,789', cifra_label: 'F1 escena', cifra_origen: 'leida', fuente: null, paso: 3, clase: 'resultado', n_runs: 12, last_run_at: hora(9),
  },
  {
    result_id: 'bench_imagenes/zero_shot_gdino', titulo: 'Qué ve el detector sin entrenar sobre seis mil imágenes de tres fuentes', etiqueta: 'zero shot gdino',
    cifra: '0,551', cifra_label: 'mAP50, bench_v3 completo', cifra_origen: 'citada', fuente: 'results/bench_imagenes/index.md', paso: 1,
    clase: 'resultado', n_runs: 6, last_run_at: '2026-09-08T18:00:00Z',
  },
  {
    result_id: 'realtime/claqueta', titulo: 'La claqueta con reloj externo', etiqueta: 'claqueta', cifra: null, cifra_label: null,
    cifra_origen: null, fuente: null, paso: null, clase: 'instrumento', n_runs: 3, last_run_at: '2026-09-07T10:00:00Z',
  },
  {
    result_id: 'ensayos/ebe_1a1', titulo: null, etiqueta: 'ebe 1a1', cifra: null, cifra_label: null, cifra_origen: null,
    fuente: null, paso: null, clase: 'ensayo', n_runs: 2, last_run_at: '2026-09-06T10:00:00Z',
  },
  {
    result_id: null, titulo: null, etiqueta: null, cifra: null, cifra_label: null, cifra_origen: null, fuente: null,
    paso: null, clase: 'sin_clasificar', n_runs: 21, last_run_at: hora(8),
  },
]

const CLASES_CR = ['person', 'helmet', 'bare_head', 'vest', 'no_vest', 'gloves', 'boots', 'harness']

function framesDe(runId, n) {
  return Array.from({ length: n }, (_, i) => {
    const dets = i % 5 === 0 ? [] : [{ label: 'person', confidence: 0.82, bbox_norm_xyxy: [0.1, 0.12, 0.42, 0.9] },
      ...(i % 3 === 0 ? [{ label: 'bare_head', confidence: 0.61, bbox_norm_xyxy: [0.2, 0.12, 0.3, 0.25] }] : [])]
    const control = i % 47 === 13 ? 'dropped:queue_full' : i % 61 === 30 ? 'not_received' : 'received'
    return {
      frame_index: i, unit_id: `${runId.slice(-4)}_frame_${String(i).padStart(6, '0')}`, timestamp_ms: i * 100,
      detections: dets, control, control_state: control.startsWith('dropped') ? 'dropped' : control,
      progress: i % 40 > 30 ? [{ condition_id: 'CR-01', progress: Math.min(1, (i % 40 - 30) / 9) }] : [],
      alert: i % 40 === 39 ? [{ condition_id: 'CR-01', severity: 'high' }] : [],
      active_patterns: [],
    }
  })
}

const totales = (frames) => ({
  frames: frames.length, detections: frames.reduce((n, f) => n + f.detections.length, 0),
  dropped_by_reason: { queue_full: frames.filter((f) => f.control.startsWith('dropped')).length },
  alerts: frames.filter((f) => f.alert.length).length, received: frames.filter((f) => f.control === 'received').length,
  not_received: frames.filter((f) => f.control === 'not_received').length,
})

function resumen(r) {
  return {
    name: r.name ?? undefined, source_type: r.source_type, model_name: r.model, device: 'cuda:0',
    prompt_set_id: r.prompt_set_id, units_processed: 260, units_dropped: 6, total_detections: r.total_detections ?? undefined,
    duration_seconds: r.duration_seconds ?? undefined, fps_effective: r.fps_effective ?? undefined,
    p50_latency_ms: 74, p95_latency_ms: 131, gpu_memory_peak_mb: 3120,
    detections_by_label: { person: 210, bare_head: 96, helmet: 12 }, run_descriptor: { topology: 'single_host' },
  }
}

/** Métricas del reporte de un experimento: medidas, no medidas por varias
 *  causas, y una que esta consola no conoce. */
function metricas() {
  const medidas = ['ttfd', 'ttfa', 't_alert-notification', 'sdr', 'recall_cr01', 'recall_cr02', 'precision_cr01',
    'fp_por_hora', 'latencia_p95', 'cobertura', 'metrica_que_la_consola_no_conoce']
    .map((name, i) => ({ name, value: i === 2 ? 1.8 : 0.5 + i / 30, unit: i < 3 ? 's' : null, status: 'computed', cause: null }))
  const causas = [['not_applicable', 'no_ground_truth'], ['not_applicable', 'non_temporal_source'],
    ['applicable_not_computed', 'clock_skew'], ['not_interpretable', 'dbe_media_time']]
  const sin = Array.from({ length: 18 }, (_, i) => {
    const [status, cause] = causas[i % causas.length]
    return { name: `metrica_sin_dato_${i + 1}`, value: null, unit: null, status, cause }
  })
  return [...medidas, ...sin]
}

function documentacion() {
  const familias = ['Identificadores', 'Condiciones', 'Campañas', 'Limitaciones'].map((titulo, f) => ({
    id: `fam_${f}`, titulo, nota: f === 0 ? 'Los que viajan entre planos.' : null,
    terminos: Array.from({ length: f === 2 ? 30 : 15 }, (_, i) => ({
      id: f === 2 && i === 0 ? 'T1' : `${titulo.slice(0, 3).toLowerCase()}_${i}`,
      termino: f === 2 && i === 0 ? 'T1' : `${titulo} ${i + 1}`,
      definicion: `Definición sintética de ${titulo.toLowerCase()} ${i + 1}, lo bastante larga como para envolver en dos líneas en un teléfono.`,
      mono: f === 0, nivel: f === 2 ? 'B' : null,
      result_ids: f === 2 && i < 3 ? ['clip_bench/t1_gdinotiny560_v2short_scene'] : [],
    })),
  }))
  const terminos = Object.fromEntries(familias.flatMap((fam) => fam.terminos.map((t) => [t.id, { ...t, familia: fam.id, familia_titulo: fam.titulo }])))
  return {
    available: true, message: null, titulo: 'Cómo leer esta consola',
    bajada: 'Qué se hizo, por qué, y qué significa cada nombre que aparece en el resto de la consola.',
    metodo: Array.from({ length: 5 }, (_, i) => ({
      n: i + 1, titulo: ['De dónde salen los datos', 'Cómo se eligió el modelo', 'Qué agrega la plataforma', 'Cómo se midió en vivo', 'Qué quedó afuera'][i],
      hizo: 'Se juntaron y congelaron los datos de la etapa.', porque: 'Sin congelarlos, cada medición contaba otra cosa.',
      quedo: 'Un banco reproducible.', evidencia_href: i < 4 ? `/evidencia/paso?n=${i + 1}` : null,
      evidencia_label: i < 4 ? `Paso ${i + 1} del recorrido` : null, terminos: i === 0 ? ['T1', 'ide_0'] : [],
    })),
    aportes: ['corrida', 'experimento', 'campana', 'evidencia', 'resultado'].map((id, i) => ({
      id, termino: id, identificador: i < 2 ? ['run_id', 'experiment_id'][i] : null, que_es: `Qué es ${id}.`,
      que_suma: `Qué suma ${id} que los otros no.`, donde: ['Corridas', 'Experimentos', 'Evidencia', 'Evidencia', 'Evidencia'][i],
      href: ['/', '/experiments', '/evidencia', '/evidencia', '/evidencia'][i], conteo: i === 0 ? 1436 : null,
    })),
    colisiones: [
      { simbolo: 'R1–R6', sentidos: [{ de: 'R1 a R6', es: 'Las campañas de densidad.' }, { de: 'R-01 a R-26', es: 'Los redlines del informe.' }], en_la_consola: 'Acá R1 a R6 son siempre campañas.' },
      { simbolo: 'T1', sentidos: [{ de: 'T1', es: 'La campaña de línea de base.' }, { de: 't1', es: 'El tiempo uno de un protocolo.' }], en_la_consola: 'Acá T1 es la campaña.' },
      { simbolo: 'CR', sentidos: [{ de: 'CR-01', es: 'Condición de riesgo.' }, { de: 'CR', es: 'Control de calidad.' }], en_la_consola: 'Acá CR es condición de riesgo.' },
    ],
    vocabulario: familias, terminos,
  }
}

function evidenciaArchivo() {
  const rid = 'clip_bench/t1_gdinotiny560_v2short_scene'
  const resultado = (id, titulo, metricasOn) => ({
    result_id: id, index: id.split('/')[0], etiqueta: id.split('/')[1].replaceAll('_', ' '), titulo,
    reclamo: 'Primera campaña sobre GT temporal humano: la referencia contra la que se lee cada campaña.',
    n_runs: 30, n_rows: 30, roles: { campaign_media: 18, campaign_control: 11, rol_nuevo_sin_nombre: 1 },
    documents: ['docs/medicion.md', 'docs/informe/capitulo-5.md'], source_refs: ['results/clip_bench/t1/eval.json', 'results/clip_bench/t1/metrics.json'],
    metricas: metricasOn ? {
      esquema: 'clip_campaign_metrics.v1',
      cabecera: [{ label: 'F1 escena', valor: 0.789 }, { label: 'Episodios', valor: 34, entero: true }],
      desgloses: [
        { id: 'escenario', titulo: 'Por escenario', nota: null, columnas: ['Escenario', 'Clips', 'Episodios', 'recall', 'FP', 'SDR'],
          filas: [
            { nombre: 'P1', clips: 4, episodios: 4, recall: 0.75, fp: 0, sdr: 0.5, no_aplica: null },
            { nombre: 'P3', clips: 2, episodios: 0, recall: null, fp: 0, sdr: null, no_aplica: 'sin episodios evaluables' },
          ] },
        { id: 'clip', titulo: 'Por clip', nota: 'Se pliega con muchas filas.', columnas: ['Clip', 'Escenario', 'Esperados', 'Detectados', 'recall', 't_alert'],
          filas: Array.from({ length: 34 }, (_, i) => ({ nombre: `c${i}`, escenario: `P${(i % 9) + 1}`, esperados: 1, detectados: i % 4 ? 1 : 0,
            recall: i % 4 ? 1 : 0, t_alert_ms: i % 4 ? 1200 + i : null, no_aplica: i % 9 === 4 ? 'negative_clip_no_episodes' : null })) },
      ],
    } : null,
  })
  const pasos = [
    { n: 1, titulo: 'Qué ve el detector sin entrenar', claim: 'El campeón zero-shot sobre 6.477 imágenes de tres fuentes.', cifra: '0,551', cifra_label: 'mAP50, bench_v3 completo', cifra_nota: 'gdino-tiny-560 · 560 / 0,30', cifra_origen: 'citada', fuente: 'results/bench_imagenes/index.md', n_resultados: 5, indices: ['bench_imagenes'] },
    { n: 2, titulo: 'Qué sostiene el estado por persona', claim: 'El veto de E-DIR rescata cuadros perdidos.', cifra: '0,146', cifra_label: 'precision de E-DIR (veto < 0,5)', cifra_nota: null, cifra_origen: 'leida', fuente: null, n_resultados: 4, indices: ['bench_nivel_a'] },
    { n: 3, titulo: 'Qué agrega la plataforma sobre la detección cruda', claim: 'La histéresis rescata percepción intermitente.', cifra: '0,789 → 0,930', cifra_label: 'F1, escena → sujeto', cifra_nota: 'mismas detecciones', cifra_origen: 'leida', fuente: null, n_resultados: 20, indices: ['clip_bench', 'realtime'] },
    { n: 4, titulo: 'Qué cuesta en tiempo real', claim: 'La entrega por MQTT agrega decenas de milisegundos.', cifra: '64,5 ms', cifra_label: 'p95 control→MQTT', cifra_nota: null, cifra_origen: 'citada', fuente: 'docs/operacion/126.md', n_resultados: 1, indices: ['realtime'] },
  ]
  const r1 = resultado(rid, 'Línea de base del Nivel B', true)
  const r2 = resultado('clip_bench/g1_gdinotiny560_v2short_subject', null, false)
  const respaldo = resultado('realtime/claqueta_reloj_externo', 'Claqueta con reloj externo', false)
  const runs = Array.from({ length: 30 }, (_, i) => ({
    result_id: rid, run_id: i < 18 ? `m${i + 1}` : `c${i - 17}`, plane: i < 18 ? 'media-plane' : 'control-plane',
    role: i < 18 ? 'campaign_media' : i < 29 ? 'campaign_control' : 'rol_nuevo_sin_nombre',
    status: i < 18 ? 'copied' : 'archived_only', source_ref: `results/clip_bench/t1/run_${i}.json`, artifact_path: `artifacts/${i}`,
    tiene_detalle_vivo: i < 18, reason: i >= 18 ? 'Las corridas de control se conservan sólo como archivo: vivían en un scratchpad ausente.' : null,
  }))
  return { rid, pasos, resultados: { [rid]: r1, [r2.result_id]: r2, [respaldo.result_id]: respaldo }, porPaso: { 3: [r1, r2], 1: [r2] }, respaldo, runs }
}

function base() {
  const corridas = corridasBase()
  const frames = Object.fromEntries(corridas.slice(0, 4).map((r) => [r.run_id, framesDe(r.run_id, r.run_id.endsWith('_obra') ? 260 : 60)]))
  const promptSets = [
    { id: 'cr01_cr02_v2_short', description: 'Núcleo CR-01/CR-02', status: 'frozen', track: 'core', derives_from: null, n_classes: 8, n_phrases: 21 },
    { id: 'cr01_cr02_bench_v2', description: 'BENCH', status: 'frozen', track: 'bench', derives_from: null, n_classes: 4, n_phrases: 4 },
    { id: 'eind_v1', description: 'Estado por persona', status: 'frozen_pending_review', track: 'core', derives_from: 'cr01_cr02_v2_short', n_classes: 3, n_phrases: 9 },
    { id: 'exploracion_clases_largas_con_un_identificador_que_no_entra_en_el_riel', description: 'Exploración', status: 'exploratory', track: 'lab', derives_from: null, n_classes: 8, n_phrases: 24 },
    { id: 'ocho_clases', description: 'Ocho clases', status: 'exploratory', track: 'lab', derives_from: null, n_classes: 8, n_phrases: 16 },
    { id: 'ensayo_ebe', description: 'Ensayo', status: 'exploratory', track: null, derives_from: null, n_classes: 2, n_phrases: 4 },
    { id: 'estado_desconocido', description: 'Estado nuevo del backend', status: 'archived_v3', track: null, derives_from: null, n_classes: 1, n_phrases: 1 },
  ]
  const detalle = (s) => ({
    id: s.id, description: s.description, status: s.status, track: s.track, derives_from: s.derives_from,
    autor: { nombre: 'equipo qa', notas: ['metadato que la consola no conoce'] },
    frozen_sha256: s.status === 'frozen' ? '9f2c…e01b' : null,
    diff: s.derives_from ? { from: s.derives_from, classes_added: ['helmet', 'vest'], classes_removed: [], phrases_added: { helmet: ['un casco'] }, phrases_removed: {} } : null,
    classes: Array.from({ length: s.n_classes }, (_, i) => ({
      id: i === 7 ? 'persona_con_arnes_de_seguridad_en_altura_y_casco_mal_abrochado' : CLASES_CR[i % CLASES_CR.length],
      strategy: i % 3 === 0 ? 'canonical_positive' : i % 3 === 1 ? 'observable_state' : null,
      phrasings: i % 2 ? { default: [`frase ${i} a`, `frase ${i} b`], owlv2: [`owl ${i}`] } : { default: [`frase ${i}`] },
      peso: i / 10,
    })),
  })
  return {
    corridas,
    frames,
    promptSets,
    promptDetalles: Object.fromEntries(promptSets.map((s) => [s.id, detalle(s)])),
    camaras: [
      { id: 'porton_norte', name: 'Portón norte', plugin: 'rtsp', config: { url: 'rtsp://usuario:***@192.168.1.50:554/stream1', transport: 'tcp' } },
      { id: 'oak_d_lab', name: 'OAK-D laboratorio', plugin: 'oak_d', config: { url: '192.168.1.60', extra: { anidado: [1, { profundo: true }] } } },
      { id: 'fuente_futura', name: 'Fuente con un plugin que esta consola no conoce todavía', plugin: 'mi_plugin_nuevo', config: {} },
    ],
    masters: [
      { name: 'P1-a-take1.mp4', scenario: 'P1', size_bytes: 82_000_000, duration_ms: 34_500, readable: true, clips: ['a_p1_c01'] },
      { name: 'P6-a-take2.mp4', scenario: 'P6', size_bytes: 91_000_000, duration_ms: 41_000, readable: true, clips: [] },
      { name: 'material_sin_escenario_heredado.mp4', scenario: null, size_bytes: 10_000_000, duration_ms: null, readable: true, clips: [] },
      { name: 'roto.mp4', scenario: 'P2', size_bytes: 0, duration_ms: null, readable: false, clips: [] },
    ],
    clips: [
      { clip_id: 'a_p1_c01', fps: 30, duration_ms: 20_500, n_frames: 615, resolution: '1920x1080', has_yaml: true, master: 'P1-a-take1.mp4', warnings: [] },
      { clip_id: 'a_p3_c02', fps: 30, duration_ms: 12_000, n_frames: 360, resolution: '1280x720', has_yaml: false, master: 'P3-a-take1.mp4', warnings: ['solo 2.0 s de cola después del evento', 'el guion pide ~20 s'] },
    ],
    manifiestos: [
      ...['base_obra', 'derivado_noche', 'perimetro_lluvia', 'claqueta_reloj', 'ensayo_ebe'].map((slug, i) => ({
        slug, group: ['campaña', 'campaña', 'perímetro', 'instrumento', 'ensayo'][i], description: `Manifiesto ${slug} [qa]`,
        experiment_id: i === 0 ? 'exp_20260909_100000_base' : null, last_experiment_id: i === 0 ? 'exp_20260909_100000_base' : null,
        last_status: i === 0 ? 'succeeded' : i === 2 ? 'failed' : null, last_run_at: i === 0 ? hora(10) : null, n_runs: i === 0 ? 2 : 0,
        evidence: i === 3 ? { ...evidencia(['realtime/claqueta'], 'instrumento'), executions: ['exp_20260901_claqueta', '${EOVRT_EXPERIMENT_ID}'] } : evidencia(i === 0 ? ['clip_bench/t1_gdinotiny560_v2short_scene'] : [], i === 0 ? 'resultado' : 'sin_clasificar'),
      })),
      ...Array.from({ length: 6 }, (_, i) => ({ slug: `talert_${i}`, group: 'talert', description: 'Plantilla talert', last_experiment_id: '${EOVRT_EXPERIMENT_ID}', last_status: 'succeeded', n_runs: 1, evidence: evidencia([], 'plataforma') })),
    ],
    experimentos: {
      exp_20260909_100000_base: { experiment_id: 'exp_20260909_100000_base', slug: 'base_obra', status: 'succeeded', ok: true, media_run_id: 'run_20260909_090000_obra', control_run_id: 'ctl_20260909_100000' },
      exp_20260909_115000_vivo: { experiment_id: 'exp_20260909_115000_vivo', slug: 'perimetro_lluvia', status: 'running', media_run_id: 'run_20260909_115500_vivo', control_run_id: 'ctl_vivo' },
    },
    experimentoActual: null,
    instancias: [
      { name: 'mp-gdino-tiny', model_ref: 'gdino-tiny-560', state: 'running', ready: true, is_target: true },
      { name: 'mp-yoloe', model_ref: 'yoloe-v8s-con-un-nombre-de-modelo-bastante-largo', state: 'exited', ready: false, is_target: false },
      { name: 'mp-owlv2', model_ref: 'owlv2-base', state: 'absent', ready: false, is_target: false },
    ],
    grabacion: { state: 'idle' },
    preview: { status: 'idle', preview_id: null, mode: null, error: null },
    evidencia: evidenciaArchivo(),
  }
}

const jsonRes = (body, status = 200, headers = {}) => ({ status, body, headers })

/**
 * Crea el estado de un escenario.
 *
 * `variante`:
 * - target: 'ok' | 'cargando' | 'caido' | 'error'
 * - preflight: 'ok' | 'bloqueado'
 * - instancias: 'lista' | '501'
 * - evidencia: 'ok' | 'ausente'
 * - camaras: 'varias' | 'vacio' | 'error'
 * - corridas: 'varias' | 'vacio'
 * - experimentoActual: null | id de un experimento corriendo
 * - grabacion: estado de grabación inicial
 * - preview: estado de preview inicial
 * - pendientes: [regex] — peticiones que nunca responden (estado de carga)
 * - fallar: [{ re, status }] — peticiones que fallan
 * - sinPreviews: true — las imágenes de cuadro dan 404
 */
export function crearMundo(variante = {}) {
  const v = {
    target: 'ok', preflight: 'ok', instancias: 'lista', evidencia: 'ok', camaras: 'varias', corridas: 'varias',
    experimentoActual: null, pendientes: [], fallar: [], sinPreviews: false, ...variante,
  }
  const s = base()
  if (v.corridas === 'vacio') s.corridas = []
  if (v.camaras === 'vacio') s.camaras = []
  if (v.experimentoActual) s.experimentoActual = s.experimentos[v.experimentoActual]
  if (v.grabacion) s.grabacion = v.grabacion
  if (v.preview) s.preview = v.preview
  const log = []

  const target = () => {
    if (v.target === 'caido') return { service_url: 'http://media.qa:8080', healthy: false, ready: false, model: null }
    if (v.target === 'cargando') return { service_url: 'http://media.qa:8080', healthy: true, ready: false, model: null }
    return { ...plano('http://media.qa:8080'), model: model() }
  }
  const preflight = () => ({
    ready: v.preflight === 'ok',
    blockers: v.preflight === 'ok' ? [] : ['el control-plane no responde', 'falta el pattern set en el motor de reglas'],
    media: target(),
    control: v.preflight === 'ok' ? plano('http://control.qa:8081') : { service_url: 'http://control.qa:8081', healthy: false, ready: false },
    distribution: plano('http://distribution.qa:8082'),
  })

  const runHeaders = (total) => ({
    'X-Total-Count': String(total), 'X-Evidence-Available': 'true', 'X-Clasificacion-Available': 'true', 'X-Clasificacion-Roles': '2/21',
  })

  function listarCorridas(q) {
    let rows = [...s.corridas]
    const estado = q.get('estado')
    if (estado) rows = rows.filter((r) => r.status === estado)
    const texto = (q.get('q') ?? '').toLowerCase()
    if (texto) rows = rows.filter((r) => `${r.name ?? ''} ${r.run_id}`.toLowerCase().includes(texto))
    const clase = q.get('clase')
    if (clase) rows = rows.filter((r) => (r.evidence?.clase ?? 'sin_clasificar') === clase)
    const rid = q.get('result_id')
    if (rid) rows = rows.filter((r) => r.evidence?.result_ids.includes(rid) || (rid && r.run_id.endsWith('bench')))
    const orden = q.get('orden') ?? 'created_at'
    const dir = q.get('direccion') === 'asc' ? 1 : -1
    rows.sort((a, b) => ((a[orden] ?? '') > (b[orden] ?? '') ? 1 : (a[orden] ?? '') < (b[orden] ?? '') ? -1 : 0) * dir)
    const size = Number(q.get('page_size') ?? 25)
    const pagina = Number(q.get('pagina') ?? 1)
    return jsonRes(rows.slice((pagina - 1) * size, pagina * size), 200, runHeaders(rows.length))
  }

  function traza(id, q) {
    const frames = s.frames[id] ?? []
    const solo = q.get('solo')
    const filtrados = solo === 'alertas' ? frames.filter((f) => f.alert.length)
      : solo === 'actividad' ? frames.filter((f) => f.detections.length || f.control !== 'received' || f.alert.length || f.progress.length)
      : frames
    const size = Number(q.get('page_size') ?? 50)
    const page = Number(q.get('page') ?? 1)
    return jsonRes({
      media_run_id: id, control_run_id: `ctl_${id.slice(-4)}`, topology: 'single_host', control_error: null,
      totals: totales(frames), page, page_size: size, total: filtrados.length, frames: filtrados.slice((page - 1) * size, page * size),
    })
  }

  function indice(id) {
    const frames = s.frames[id] ?? []
    return jsonRes({
      media_run_id: id, control_run_id: `ctl_${id.slice(-4)}`, topology: 'single_host', control_error: null,
      totals: totales(frames), total: frames.length, unit_id: frames.map((f) => f.unit_id), frame_index: frames.map((f) => f.frame_index),
      timestamp_ms: frames.map((f) => f.timestamp_ms), detections: frames.map((f) => f.detections.length),
      control_state: frames.map((f) => f.control_state), alert: frames.map((f) => f.alert.length),
    })
  }

  const comparar = (ids) => {
    const runs = ids.map((id) => s.corridas.find((r) => r.run_id === id)).filter(Boolean)
    const clases = ['person', 'helmet', 'bare_head', 'vest']
    return jsonRes({
      runs: runs.map((r, i) => ({ run_id: r.run_id, label: r.name ?? r.run_id, model: r.model, bench_split: r.bench_split, mAP50: i === 1 ? 0.47 : 0.47 + i / 100, cr01_detection_recall: i === 2 ? null : 0.6 + i / 50 })),
      classes: clases,
      ap_by_class: Object.fromEntries(clases.map((c, ci) => [c, runs.map((_, i) => (ci === 1 && i === 0 ? null : 0.4 + ((ci + i) % 5) / 10))])),
      skipped: ids.length > 3 ? ['run_sin_metricas'] : [],
    })
  }

  /** Resuelve una petición. `null` = no declarada (el escenario falla). */
  function responder({ method, pathname, query, body }) {
    const q = query
    log.push({ method, pathname, query: q.toString(), body })
    const clave = `${method} ${pathname}${q.toString() ? `?${q}` : ''}`
    if (v.pendientes.some((re) => re.test(clave))) return { pendiente: true }
    const falla = v.fallar.find((f) => f.re.test(clave))
    if (falla) return jsonRes({ detail: `Falla sintética [qa] (${falla.status})` }, falla.status)

    let m
    // ── Salud ────────────────────────────────────────────────────────────
    if (method === 'GET' && pathname === '/api/target') {
      if (v.target === 'error') return jsonRes({ detail: 'BFF inaccesible [qa]' }, 503)
      return jsonRes(target())
    }
    if (method === 'GET' && pathname === '/api/preflight') return jsonRes(preflight())

    // ── Catálogo ─────────────────────────────────────────────────────────
    if (method === 'GET' && pathname === '/api/catalog/ingest-plugins') return jsonRes([
      { id: 'image_folder', kind: 'bounded', available: true, enabled: true, description: 'Carpeta de imágenes montada en el motor.' },
      { id: 'video_file', kind: 'bounded', available: true, enabled: true, description: 'Archivo de video local del motor.' },
      { id: 'rtsp', kind: 'live', available: true, enabled: true, description: 'Cámara IP por RTSP.' },
      { id: 'oak_d', kind: 'live', available: false, enabled: false, description: 'OAK-D Pro por IP.', disabled_reason: 'El motor de detección no tiene instalado el SDK DepthAI.' },
    ])
    if (method === 'GET' && pathname === '/api/catalog/datasets') return jsonRes([
      { id: 'bench_v3', description: 'Banco congelado de 6.477 imágenes de tres fuentes independientes.', path: '/data/bench_v3', available: true },
      { id: 'bench_v2_val', description: 'Validación', path: '/data/bench_v2_val', available: true },
      { id: 'rodaje_ebe', description: 'Rodaje del día EBE', path: '/data/rodaje', available: false },
    ])
    if (method === 'GET' && pathname === '/api/catalog/prompt-sets') return jsonRes([
      { id: 'cr01_cr02_v2_short', description: 'Núcleo', language: 'es', frozen: true, classes: CLASES_CR.map((id) => ({ id, enabled_by_default: id !== 'gloves', phrasings: { default: [id] } })) },
      { id: 'vocabulario_amplio_80', description: '80 clases', language: 'es', frozen: false, classes: Array.from({ length: 80 }, (_, i) => ({ id: `clase_${String(i + 1).padStart(2, '0')}`, phrasings: { default: [`c${i}`] } })) },
      { id: 'eind_v1', description: 'Estado', language: 'es', frozen: false, classes: ['person', 'helmet', 'bare_head'].map((id) => ({ id, phrasings: { default: [id] } })) },
    ])
    if (method === 'GET' && pathname === '/api/catalog/experiments') return jsonRes([
      { id: 'base_obra', group: 'campaña', manifest: { source: { ref: 'bench_v3' }, prompts: { ref: 'cr01_cr02_v2_short', active_ids: ['person', 'bare_head'] }, run: { name: 'Base' }, model: { ref: 'yoloe-v8s' } } },
      { id: 'perimetro_lluvia', group: 'perímetro', manifest: { source: { type: 'rtsp', url: 'rtsp://u:***@cam/stream' }, prompts: { ref: 'eind_v1' } } },
    ])
    if (method === 'GET' && pathname === '/api/catalog/conditions') return jsonRes([])

    // ── Corridas ─────────────────────────────────────────────────────────
    if (method === 'GET' && pathname === '/api/runs') return listarCorridas(q)
    if (method === 'GET' && pathname === '/api/runs/grupos') {
      const clase = q.get('clase')
      const items = (v.corridas === 'vacio' ? [] : grupos()).filter((g) => !clase || g.clase === clase)
      return jsonRes(items, 200, {
        'X-Class-Counts': v.corridas === 'vacio' ? '' : 'resultado=19,instrumento=3,ensayo=2,sin_clasificar=21',
        'X-Evidence-Available': 'true', 'X-Clasificacion-Available': 'true', 'X-Clasificacion-Roles': '2/21',
      })
    }
    if (method === 'POST' && pathname === '/api/runs') {
      const id = 'run_20260909_120000_lanzada'
      s.corridas.unshift({ run_id: id, name: body?.run?.name ?? null, status: 'running', live: true, created_at: FECHA, source_type: body?.ingest?.plugin, evidence: evidencia([]) })
      s.frames[id] = []
      return jsonRes({ run_id: id }, 201)
    }
    if ((m = pathname.match(/^\/api\/runs\/([^/]+)$/))) {
      const id = decodeURIComponent(m[1])
      const r = s.corridas.find((x) => x.run_id === id)
      if (method === 'DELETE') {
        if (!r) return jsonRes({ detail: 'no existe' }, 404)
        s.corridas = s.corridas.filter((x) => x.run_id !== id)
        return jsonRes({ deleted: id })
      }
      if (method === 'GET') return r ? jsonRes({ ...r, summary: resumen(r) }) : jsonRes({ detail: 'Corrida inexistente [qa]' }, 404)
    }
    if ((m = pathname.match(/^\/api\/runs\/([^/]+)\/(trace|trace\/index|artifacts|comparison|evaluate|stop)$/))) {
      const id = decodeURIComponent(m[1])
      const r = s.corridas.find((x) => x.run_id === id)
      if (!r) return jsonRes({ detail: 'no existe' }, 404)
      if (m[2] === 'trace' && method === 'GET') return traza(id, q)
      if (m[2] === 'trace/index' && method === 'GET') return indice(id)
      if (m[2] === 'artifacts' && method === 'GET') return jsonRes({ run_id: id, complete: true, items: [
        { path: 'summary.json', name: 'summary.json', size_bytes: 4_210, n_files: null, description: 'Resumen de la corrida.' },
        { path: 'detections.jsonl', name: 'detections.jsonl', size_bytes: 1_240_000, n_files: null, description: 'Una línea por detección.' },
        { path: 'previews', name: 'previews/', size_bytes: 31_000_000, n_files: 260, description: 'Vistas previas por cuadro.' },
        { path: 'annotated.mp4', name: 'annotated.mp4', size_bytes: 48_000_000, n_files: null, description: 'Video con detecciones dibujadas.' },
        { path: 'errors.jsonl', name: 'errors.jsonl', size_bytes: 0, n_files: null, description: null },
      ] })
      if (m[2] === 'comparison' && method === 'GET') return jsonRes({ run_id: id, previous_run_id: 'run_20260901_000000_hist', matched_on: ['model', 'prompt_set_id'], deltas: {
        fps_effective: { current: 12.4, previous: 11.5, delta: 0.9, better: 'mas' },
        p50_latency_ms: { current: 74, previous: 81, delta: -7, better: 'menos' },
        total_detections: { current: 318, previous: 290, delta: 28, better: null },
      } })
      if (m[2] === 'evaluate' && method === 'GET') {
        if (!r.evaluated) return jsonRes({ detail: 'sin evaluar' }, 404)
        return jsonRes({ type: 'perception', run_id: id, benchmark: 'bench_v3', iou_threshold: 0.5, evaluated_at: hora(9, 30),
          per_class: CLASES_CR.slice(0, 4).map((c, i) => ({ class_name: c, AP50: i === 3 ? null : 0.4 + i / 10, n_gt: 80 + i, n_det: 70 + i })),
          cr01_detection_recall: 0.64, mAP50: 0.47, model: r.model, bench_split: r.bench_split })
      }
      if (m[2] === 'evaluate' && method === 'POST') { r.evaluated = true; return responder({ method: 'GET', pathname, query: q, body: null }) }
      if (m[2] === 'stop' && method === 'POST') { r.status = 'stopped'; r.live = false; return jsonRes({ run_id: id, stopping: true }) }
    }
    if ((m = pathname.match(/^\/api\/runs\/([^/]+)\/artifacts\/(.+)$/)) && method === 'GET') {
      if (m[2].startsWith('previews/') && m[2].endsWith('.jpg')) {
        const n = Number(m[2].match(/(\d+)\.preview/)?.[1] ?? 0)
        if (v.sinPreviews || n % 7 === 3) return jsonRes({ detail: 'preview ausente [qa]' }, 404)
        return { status: 200, binary: PNG, contentType: 'image/png' }
      }
      return jsonRes({ detail: 'Medios no servidos en QA' }, 404)
    }
    if (method === 'GET' && pathname === '/api/compare') return comparar((q.get('runs') ?? '').split(',').filter(Boolean))
    if (method === 'POST' && pathname === '/api/manifests') return jsonRes({ path: `${body?.name ?? 'manifiesto'}.yaml` }, 201)

    // ── Experimentos ─────────────────────────────────────────────────────
    if (method === 'GET' && pathname === '/api/experiments/manifests') return jsonRes(s.manifiestos, 200, {
      'X-Evidence-Available': 'true', 'X-Clasificacion-Available': 'true', 'X-Platform-Test-Count': '212',
      'X-Platform-Test-Slugs': 'orq_1=120,orq_alerts=60,gate_orq=32', 'X-Total-Executions-Count': '340',
    })
    if (method === 'GET' && pathname === '/api/experiments/current') return s.experimentoActual ? jsonRes(s.experimentoActual) : jsonRes({ detail: 'ninguno' }, 404)
    if (method === 'POST' && pathname === '/api/experiments/run') {
      if (v.preflight !== 'ok') return jsonRes({ detail: 'Plataforma no lista: el control-plane no responde' }, 503)
      s.experimentoActual = { experiment_id: 'exp_20260909_120000_nuevo', slug: body?.slug, status: 'running' }
      s.experimentos[s.experimentoActual.experiment_id] = s.experimentoActual
      return jsonRes({ experiment_id: s.experimentoActual.experiment_id }, 201)
    }
    if ((m = pathname.match(/^\/api\/experiments\/manifests\/([^/]+)\/(derive-defaults|derive)$/))) {
      const slug = decodeURIComponent(m[1])
      if (m[2] === 'derive-defaults') return jsonRes({ warmup_frames: 20, fps: null, camera_id: 'oak_d_lab', prompt_set_id: 'cr01_cr02_v2_short', stride: 2, max_units: null, pattern_set_file: '/opt/control/patterns/v2.yaml', pattern_active_ids: ['CR-01', 'CR-02'] })
      if (method === 'POST') {
        s.manifiestos.push({ slug: body.new_slug, group: 'derivado', description: `Derivado de ${slug}`, evidence: evidencia([], 'sin_clasificar') })
        return jsonRes({ slug: body.new_slug }, 201)
      }
    }
    if ((m = pathname.match(/^\/api\/experiments\/([^/]+)(\/alerts|\/report)?$/)) && method === 'GET') {
      const id = decodeURIComponent(m[1])
      const e = s.experimentos[id]
      if (!e) return jsonRes({ detail: 'no existe' }, 404)
      if (!m[2]) return jsonRes(e)
      if (e.status === 'running') return jsonRes({ detail: 'consolidándose' }, 404)
      if (m[2] === '/alerts') return jsonRes([
        { alert_id: 'al_0001', condition_id: 'CR-01', severity: 'high', timestamp_ms: 4_100 },
        { alert_id: 'al_0002', condition_id: 'CR-02', severity: 'medium', timestamp_ms: 12_300 },
        { alert_id: 'al_0003', condition_id: 'CR-99', severity: 'nueva', timestamp_ms: null },
      ])
      return jsonRes({ non_temporal: false, resultados: metricas(),
        distribucion: { counts: { delivered: 2, failed: 1, suppressed_cooldown: 0 }, skipped_invalid_alerts: 1 },
        distribucion_por_alerta: { al_0001: { outcome: 'delivered' }, al_0002: { outcome: 'failed' } } })
    }
    if (method === 'GET' && pathname === '/api/control/current') {
      const vivo = s.experimentoActual?.status === 'running'
      return vivo ? jsonRes({ control_run_id: 'ctl_vivo', status: 'running', patterns: [
        { pattern_id: 'p1', condition_id: 'CR-01', severity: 'high', state: 'confirmed', subject_key: 's1', active_ms: 12_000 },
      ] }) : jsonRes({ detail: 'sin corrida' }, 404)
    }

    // ── Conjuntos de prompts ─────────────────────────────────────────────
    if (method === 'GET' && pathname === '/api/prompt-sets') return jsonRes(s.promptSets)
    if (method === 'POST' && pathname === '/api/prompt-sets') {
      s.promptSets.push({ id: body.id, description: body.description, status: 'exploratory', track: null, derives_from: null, n_classes: body.classes.length, n_phrases: 0 })
      s.promptDetalles[body.id] = { ...body, status: 'exploratory' }
      return jsonRes(s.promptDetalles[body.id], 201)
    }
    if ((m = pathname.match(/^\/api\/prompt-sets\/([^/]+)(\/freeze-request|\/freeze|\/derive)?$/))) {
      const id = decodeURIComponent(m[1])
      const d = s.promptDetalles[id]
      if (!d) return jsonRes({ detail: 'no existe' }, 404)
      if (!m[2] && method === 'GET') return jsonRes(d)
      if (!m[2] && method === 'PUT') { s.promptDetalles[id] = { ...body }; return jsonRes(body) }
      if (!m[2] && method === 'DELETE') { s.promptSets = s.promptSets.filter((x) => x.id !== id); return { status: 204, body: null } }
      if (m[2] === '/freeze-request' && method === 'POST') { d.status = 'frozen_pending_review'; return jsonRes(d) }
      if (m[2] === '/freeze' && method === 'POST') { d.status = 'frozen'; return jsonRes(d) }
      if (m[2] === '/derive' && method === 'POST') return jsonRes({ ...d, id: body.new_id, status: 'exploratory' }, 201)
    }

    // ── Cámaras, preview, grabación ──────────────────────────────────────
    if (pathname === '/api/cameras') {
      if (method === 'GET') return v.camaras === 'error' ? jsonRes({ detail: 'Almacén de cámaras ilegible [qa]' }, 500) : jsonRes(s.camaras)
      if (method === 'POST') { s.camaras.push(body); return jsonRes(body, 201) }
    }
    if ((m = pathname.match(/^\/api\/cameras\/([^/]+)$/))) {
      const id = decodeURIComponent(m[1])
      if (method === 'PUT') { s.camaras = s.camaras.map((c) => (c.id === id ? body : c)); return jsonRes(body) }
      if (method === 'DELETE') { s.camaras = s.camaras.filter((c) => c.id !== id); return { status: 204, body: null } }
    }
    if (pathname === '/api/preview') {
      if (method === 'GET') return jsonRes(s.preview)
      if (method === 'DELETE') { s.preview = { status: 'idle', preview_id: null, mode: null, error: null }; return jsonRes({}) }
      if (method === 'POST') {
        if (s.corridas.some((r) => r.status === 'running' && r.live) && v.previewBloqueada) return jsonRes({ detail: 'corrida', reason: 'run_active', active_run_id: 'run_20260909_115500_vivo' }, 409)
        s.preview = { status: 'streaming', preview_id: 'pv1', mode: body.mode, error: null }
        return jsonRes({ preview_id: 'pv1' }, 201)
      }
    }
    if (method === 'GET' && pathname === '/api/recordings/next') return jsonRes({ basename: `${q.get('scenario')}-${q.get('variant')}-take3` })
    if (pathname === '/api/recordings') {
      if (method === 'GET') return jsonRes(s.grabacion)
      if (method === 'POST') { s.grabacion = { state: 'recording', basename: 'P1-a-take3', elapsed_ms: 12_000, size_bytes: 2_400_000 }; return jsonRes(s.grabacion) }
      if (method === 'DELETE') { const fin = { state: 'finished', basename: 'P1-a-take3', duration_ms: 31_000, fps: 59.94, resolution: '1920x1080' }; s.grabacion = { state: 'idle' }; return jsonRes(fin) }
    }

    // ── Clips ────────────────────────────────────────────────────────────
    if (method === 'GET' && pathname === '/api/clips/masters') return jsonRes({ masters: s.masters })
    if (method === 'GET' && pathname === '/api/clips') return jsonRes({ clips: s.clips })
    if (method === 'POST' && pathname === '/api/clips') {
      const id = body.clip_id ?? 'a_p1_c02'
      return jsonRes({ clip_id: id, info: { fps: 30, duration_ms: 20_500, n_frames: 615, resolution: '1920x1080' }, warnings: ['el guion pide ~20 s'], regenerated: Boolean(body.clip_id), invalidated: body.clip_id ? [`${id}.yaml`] : [] }, 201)
    }
    if (method === 'GET' && pathname.startsWith('/api/clips/media/')) return jsonRes({ detail: 'Medios no servidos en QA' }, 404)

    // ── Plataforma ───────────────────────────────────────────────────────
    if (method === 'GET' && pathname === '/api/platform/instances') {
      if (v.instancias === '501') return jsonRes({ detail: 'Instancia fija [qa]' }, 501)
      return jsonRes(s.instancias)
    }
    if ((m = pathname.match(/^\/api\/platform\/instances\/([^/]+)\/activate$/)) && method === 'POST') {
      const nombre = decodeURIComponent(m[1])
      s.instancias = s.instancias.map((i) => ({ ...i, is_target: i.name === nombre, ready: i.name === nombre }))
      return jsonRes({ target: nombre })
    }
    if (method === 'POST' && pathname === '/api/platform/stop') { s.instancias = s.instancias.map((i) => ({ ...i, is_target: false, ready: false })); return jsonRes({ target: null }) }

    // ── Documentación y evidencia (lectura del disco) ────────────────────
    if (method === 'GET' && pathname === '/api/documentacion') return jsonRes(documentacion())
    const ev = s.evidencia
    const ausente = { available: false, message: 'Falta results/evidence-runs/. Restaurar desde docs/operacion/126 (backup de evidencia).' }
    if (method === 'GET' && pathname === '/api/evidencia') {
      if (v.evidencia === 'ausente') return jsonRes({ ...ausente, pasos: [], respaldo: null, indices: [] })
      return jsonRes({ available: true, message: null, pasos: ev.pasos,
        respaldo: { titulo: 'Respaldo instrumental', claim: 'Lo que valida el aparato de medición, no el fenómeno.', n_resultados: 1, resultados: [ev.respaldo] },
        indices: [{ id: 'bench_imagenes', n_results: 5 }, { id: 'bench_nivel_a', n_results: 4 }, { id: 'clip_bench', n_results: 20 }, { id: 'realtime', n_results: 6 }] })
    }
    if (method === 'GET' && pathname === '/api/evidencia/paso') {
      if (v.evidencia === 'ausente') return jsonRes({ ...ausente, paso: null, resultados: [] })
      const n = Number(q.get('n'))
      const paso = ev.pasos.find((p) => p.n === n)
      if (!paso) return jsonRes({ detail: 'Ese paso del recorrido no existe' }, 404)
      return jsonRes({ available: true, message: null, paso, n_pasos: ev.pasos.length, resultados: ev.porPaso[n] ?? [] })
    }
    if (method === 'GET' && pathname === '/api/evidencia/resultado') {
      if (v.evidencia === 'ausente') return jsonRes({ ...ausente, result: null, items: [], total: 0, page: 1, page_size: 25 })
      const r = ev.resultados[q.get('id')]
      const page = Number(q.get('page') ?? 1)
      const size = Number(q.get('page_size') ?? 25)
      if (!r) return jsonRes({ available: true, message: null, result: null, items: [], total: 0, page, page_size: size })
      return jsonRes({ available: true, message: null, result: r, items: ev.runs.slice((page - 1) * size, page * size), total: ev.runs.length, page, page_size: size })
    }
    if (method === 'GET' && pathname === '/api/evidencia/run') {
      if (v.evidencia === 'ausente') return jsonRes({ ...ausente, run: null, summary: null, substitutes: [], notice: null })
      const run = ev.runs.find((x) => x.run_id === q.get('run_id') && x.plane === q.get('plane'))
      if (!run) return jsonRes({ available: true, message: null, run: null, summary: null, substitutes: [], notice: null })
      const archivada = run.status === 'archived_only'
      return jsonRes({ available: true, message: null, run, relations: [run],
        summary: archivada ? null : { run_id: run.run_id, units_processed: 17, fps_effective: 11.2, model_name: 'gdino-tiny-560', detections_by_label: { person: 12 } },
        summary_source: archivada ? null : 'results/evidence-runs/media/m1/summary.json',
        substitutes: archivada ? [{ name: 'eval.json', data: { precision: 0.75, episodios: [{ id: 1, ok: true }] } }] : [],
        notice: archivada ? 'Sin summary individual; se conserva el artefacto sustituto.' : null })
    }
    return null
  }

  return { estado: s, log, responder }
}

// Compatibilidad con el capturador anterior (una sola respuesta por ruta).
export const runId = 'run_20260909_090000_obra'
export const experimentId = 'exp_20260909_100000_base'
export function fixture(url, method = 'GET') {
  const u = new URL(url)
  const r = crearMundo().responder({ method, pathname: u.pathname, query: u.searchParams, body: null })
  return r && !r.pendiente ? r : null
}
