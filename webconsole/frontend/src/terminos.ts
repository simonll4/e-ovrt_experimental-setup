/** Los términos que la consola marca fuera de `/documentacion`.
 *
 *  Esta lista es un CONTRATO con `results/evidence-vista/documentacion.yaml`:
 *  el test `test_terminos_marcados_en_el_codigo_estan_definidos` (backend) falla
 *  si alguno de estos ids no tiene definición en el YAML. Es el mismo patrón
 *  anti-envejecimiento que `clasificacion.yaml`: preferimos romper el build
 *  antes que mostrar algo mudo.
 *
 *  La regla de runtime es la otra mitad, y no depende de esta lista: `Termino`
 *  renderiza TEXTO PLANO cuando el id no está en el vocabulario cargado. Un
 *  término sin definición nunca se ofrece como clickeable.
 */

/** Identificadores que viajan entre los planos. */
export const TERMINOS_IDENTIFICADORES = [
  'run_id', 'experiment_id', 'clip_id', 'track_id',
] as const

/** Las dos condiciones de riesgo del núcleo validable. */
export const TERMINOS_CONDICIONES = ['CR-01', 'CR-02'] as const

/** Las cinco clases de la taxonomía de corridas. El id lleva prefijo `clase_`
 *  para no colisionar con la clase canónica del detector (`person`, `vest`…). */
export const TERMINOS_CLASES = [
  'clase_resultado', 'clase_instrumento', 'clase_ensayo',
  'clase_plataforma', 'clase_sin_clasificar',
] as const

/** Las campañas con artefacto que la consola nombra por su id corto. */
export const TERMINOS_CAMPANAS = [
  'T1', 'T2', 'D1', 'H1', 'G1', 'B1',
  'R1', 'R2', 'R3', 'R4', 'R5', 'R6',
  'I1', 'I2', 'NA1',
] as const

/** Las ocho limitaciones declaradas. */
export const TERMINOS_LIMITACIONES = [
  'L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8',
] as const

/** Los dos escenarios de despliegue. */
export const TERMINOS_ESCENARIOS = ['DBE', 'EBE'] as const

/** El alcance completo, que es lo que verifica el test. */
export const TERMINOS_MARCADOS: readonly string[] = [
  ...TERMINOS_IDENTIFICADORES,
  ...TERMINOS_CONDICIONES,
  ...TERMINOS_CLASES,
  ...TERMINOS_CAMPANAS,
  ...TERMINOS_LIMITACIONES,
  ...TERMINOS_ESCENARIOS,
]

/** La clase de corrida -> el id de su término. La tabla de `ClaseChips` traduce
 *  el código a etiqueta; ésta lo traduce a su definición. */
export const TERMINO_DE_CLASE: Record<string, string> = {
  resultado: 'clase_resultado',
  instrumento: 'clase_instrumento',
  ensayo: 'clase_ensayo',
  plataforma: 'clase_plataforma',
  sin_clasificar: 'clase_sin_clasificar',
}
