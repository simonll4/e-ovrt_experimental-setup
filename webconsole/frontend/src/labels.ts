// Glosario de interfaz — nombres legibles para códigos que hoy solo existen como
// identificadores crudos en la API. Ver docs/superpowers/specs/2026-07-26-rediseno-consola-design.md §3.
// Los códigos (CR-01, CR-02) nunca se traducen ni se ocultan: se acompañan con su
// nombre, nunca se reemplazan por él.

export const CONDITION_NAMES: Record<string, string> = {
  'CR-01': 'Presencia de persona sin casco',
  'CR-02': 'Presencia de persona sin chaleco',
}

export function conditionLabel(code: string): string {
  const name = CONDITION_NAMES[code]
  return name ? `${code} — ${name}` : code
}

// Vocabulario real y cerrado de motivos de descarte del media-plane, declarado en
// e-ovrt_media-plane/src/eovrt_media/contracts/dropped_unit.py:
//   DropReason = Literal["rate_gate", "queue_full", "staleness_timeout", "channel_closed"]
// `rate_gate` es el descarte intencional (compuerta de tasa); los otros tres son por
// sobrecarga/corte del transporte. Un código fuera de este set cae a mostrarse crudo y
// en monoespaciada (ver traceview.ts#controlLabel / #controlLabelIsRaw) — nunca en
// blanco, nunca una cadena en inglés suelta.
export const CONTROL_DROP_REASONS: Record<string, string> = {
  rate_gate: 'límite de tasa',
  queue_full: 'cola llena',
  staleness_timeout: 'cuadro vencido',
  channel_closed: 'canal cerrado',
}

// Estados/causas de aplicabilidad de metricas del reporte (ADR-006), ver
// webconsole/backend/src/eovrt_webconsole/experiment/applicability.py
// (estados) y experiment/report.py (causas — vocabulario cerrado ahi mismo,
// aunque algunas metricas copian su causa verbatim de otro sumario y pueden
// no pertenecer a este set; applicabilityLabel cae al codigo crudo en ese caso).
export const APPLICABILITY_STATUS: Record<string, string> = {
  not_applicable: 'no aplicable',
  not_interpretable: 'no interpretable',
  applicable_not_computed: 'aplicable, no calculada',
  computed: 'calculada',
}

export const APPLICABILITY_CAUSE: Record<string, string> = {
  non_temporal_source: 'fuente no temporal',
  dbe_media_time: 'reloj de medios DBE',
  clock_skew: 'desfasaje de reloj',
  missing_join_key: 'falta clave de cruce',
  no_ground_truth: 'sin ground truth',
  no_distribution: 'sin distribución',
  no_notifications_delivered: 'sin entregas',
  distribution_wall_clock_dbe_only: 'latencia con reloj de prueba',
}

export const DISTRIBUTION_OUTCOME: Record<string, string> = {
  delivered: 'entregada',
  suppressed_cooldown: 'suprimida (cooldown)',
  skipped_duplicate: 'duplicada (ya entregada)',
  failed: 'falló, reintentando',
  dead_letter: 'agotada (dead letter)',
}

export function applicabilityLabel(code: string, dict: Record<string, string>): string {
  return dict[code] ?? code
}

// El BFF redacta algunos mensajes de operador nombrando los planos por su nombre de
// código: los `blockers` del preflight
// (webconsole/backend/src/eovrt_webconsole/preflight.py) y el `detail` del 503 al
// lanzar, que concatena esos mismos blockers. Se traducen acá, en la capa de
// presentación, porque el rediseño no toca el backend.
//
// Es reemplazo de término y no un mapa de frases exactas a propósito: el 503 llega
// como "Plataforma no lista: el control-plane no responde" —frase compuesta, no una
// clave— y así cualquier redacción nueva del backend queda cubierta sin tocar esto.
// Un texto sin nombres de plano vuelve intacto.
//
// Es el único texto de interfaz que puede decir "media-plane"/"control-plane", y
// aparece justo cuando algo se cayó: el peor momento para mostrarle jerga al operador.
export function applyPlaneGlossary(text: string): string {
  return text
    .replace(/media-plane/g, 'motor de detección')
    .replace(/control-plane/g, 'motor de reglas')
}
