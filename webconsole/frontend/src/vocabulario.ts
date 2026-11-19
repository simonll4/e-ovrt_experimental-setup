/** El vocabulario de la consola (plan de la consola de evidencia, §4). Manda el del informe:
 *  - el nombre llano va primero y el código al lado, más chico (`NombreCodigo`);
 *  - en la interfaz no aparecen «generación 1» ni «generación 2»: lo final son «los resultados»
 *    y lo anterior, la «etapa de desarrollo»;
 *  - «campeón» es «perfil operativo».
 *
 *  Acá va TEXTO, nunca una cifra de un resultado: las cifras se leen de los resultados.
 *  `__tests__/vocabulario.test.ts` comprueba que cada prueba del catálogo tenga su nombre y que
 *  ningún nombre use un término que el plan saca de la interfaz. */

/** Lo final y lo anterior, dichos como los dice la consola. */
export const ETAPA_DE_DESARROLLO = 'etapa de desarrollo'
export const PERFIL_OPERATIVO = 'perfil operativo'

/** Los códigos del informe con su nombre llano (§4.2). */
export const NOMBRE_DE_CODIGO: Record<string, string> = {
  'CR-01': 'Sin casco',
  'CR-02': 'Sin chaleco',
  // Los nombres de las estrategias, como el informe (estrategia indirecta, directa e híbrida).
  'E-IND': 'Estrategia indirecta',
  'E-DIR': 'Estrategia directa',
  'E-HYB': 'Estrategia híbrida',
  G2A: 'Latencia por cuadro',
}

/** El nombre llano de cada prueba de la campaña. Sale de las filas y del texto del informe
 *  (Tablas 51 a 55, §17.5) donde la prueba tiene fila; las demás se nombran con las mismas
 *  palabras. El código (`ALR-01`) no se repite acá: lo pone `NombreCodigo` al lado. */
export const NOMBRE_DE_PRUEBA: Record<string, string> = {
  // Percepción en imágenes (Tabla 51)
  'IMG-01': 'Percepción del perfil operativo',
  'IMG-02': 'Percepción del contraste base-560',
  'IMG-03': 'Percepción de YOLOE-26x',
  'IMG-04': 'Percepción a mayor resolución, con el mismo umbral de caja',
  'EXT-01': 'Una clase nueva sin entrenar',
  // Estado por persona (Tabla 52)
  'PER-01': 'Estado por persona en imágenes',
  'PER-02': 'Estado por persona en imágenes, con el contraste base-560',
  'PER-03': 'Estado por persona en video de obra real',
  // Alerta por episodio (Tabla 53 y obra real)
  'ALR-01': 'Alerta por episodio, por escena',
  'ALR-02': 'Alerta por episodio, por sujeto',
  'ALR-03': 'Alerta por episodio con el contraste base-560',
  'ALR-04': 'Alerta por episodio con la estrategia directa',
  'ALR-05': 'Alerta por episodio con la estrategia híbrida',
  'ALR-06': 'Alerta por episodio con el vocabulario nativo de cabeza descubierta',
  'ALR-07': 'Obra real, por escena',
  'ALR-08': 'Obra real, por sujeto',
  'ALR-09': 'Obra real a mayor resolución, con caja 0,35',
  'ALR-10': 'Obra real con el perfil operativo y caja 0,35',
  'ALR-11': 'Alerta por episodio con YOLOE-26s',
  'ALR-12': 'Obra real con YOLOE-26s',
  'ALR-13': 'Los patrones con umbrales de EPP más exigentes, en el rodaje',
  'ALR-14': 'Los patrones con umbrales de EPP más exigentes, en obra real',
  // Errores y seguimiento (§17.5.4, §18.3)
  'ERR-01': 'Por qué da falsas alarmas por sujeto en obra real',
  'ERR-02': 'Las falsas alarmas de obra real según la resolución, con caja 0,35',
  'SEG-01': 'Fragmentación de identidad del seguidor',
  'VIS-01': 'Cuadros anotados: aciertos y fallos',
  // Tiempo real (Tabla 54)
  // Las densidades se nombran por el paso entre cuadros, no por el anclaje de la etapa de desarrollo
  // («techo en vivo», «peor caso»), que salió de la medición de cuadros por segundo corregida (doc 134 §13.22).
  'DEN-01': 'Densidad: uno de cada 7 cuadros, por escena',
  'DEN-02': 'Densidad: uno de cada 7 cuadros, por sujeto',
  'DEN-03': 'Densidad: uno de cada 15 cuadros, por escena',
  'DEN-04': 'Densidad: uno de cada 15 cuadros, por sujeto',
  'DEN-05': 'Densidad: uno de cada 26 cuadros, por escena',
  'DEN-06': 'Densidad: uno de cada 26 cuadros, por sujeto',
  'DEN-07': 'Ganancia por identidad y pérdida por densidad, en las cuatro densidades',
  'RT-01': 'Sobrecarga de la plataforma con detector simulado',
  'RT-02': 'Relectura frente a transmisión',
  'RT-03': 'Latencia en vivo con la OAK-D',
  'RT-04': 'Rodaje guionado en vivo',
  'RT-05': 'Modelos y cadencias de cámara en vivo',
  'RT-06': 'Rodaje guionado en vivo con la cámara IP',
  'RT-07': 'Rodaje guionado en vivo con otro chaleco',
  'RT-08': 'Otro chaleco, con la cámara IP',
  'RT-09': 'La prenda bajo el chaleco',
  'DIST-01': 'Del bus de alertas a la confirmación del canal',
  // Referencia (§17.5.7)
  'GT-01': 'Concordancia entre la marca del operador y la referencia',
  'GT-02': 'Sensibilidad de cada conclusión a los bordes de la referencia',
  // Integridad y plataforma (Anexo E, Tablas B.1 y B.3)
  'INT-01': 'Integridad del banco de imágenes',
  'INT-02': 'Integridad del banco temporal',
  'INT-03': 'Pesos de los modelos y configuración congelada',
  'PLAT-01': 'Qué corrió y dónde',
}

/** El nombre llano de un código o de una prueba; `undefined` si no tiene. */
/** Códigos que el informe nombra con el código delante y el nombre llano entre paréntesis: «G2A (latencia por
 *  cuadro)» (decisión del 2026-11-19, igual en la consola y en el informe). */
export const CODIGO_PRIMERO = new Set(['G2A'])

export function nombreLlano(codigo: string): string | undefined {
  return NOMBRE_DE_CODIGO[codigo] ?? NOMBRE_DE_PRUEBA[codigo]
}

/** «Nombre llano CÓDIGO» como texto plano, para un `title`, un `aria-label` o una miga. Sin
 *  nombre conocido queda el código solo: nunca una cadena vacía. */
export function nombreConCodigo(codigo: string): string {
  const nombre = nombreLlano(codigo)
  if (nombre && CODIGO_PRIMERO.has(codigo)) return `${codigo} (${nombre.toLowerCase()})`
  return nombre ? `${nombre} ${codigo}` : codigo
}

/** Los modos de prompts de la demo (`experiments/demo_defensa/modos.yaml`, que lee el programa de
 *  la campaña y no se toca): el id no cambia (lo registran las sesiones), el nombre visible sí. */
export const NOMBRE_DE_MODO: Record<string, string> = {
  campeon: 'Perfil operativo',
}

/** El nombre visible de un modo como texto plano: el del vocabulario, o el de `modos.yaml` con su
 *  nombre llano si es un código del informe («Por detección directa E-DIR»). */
export function nombreDeModo(modo: { id: string; nombre: string }): string {
  return NOMBRE_DE_MODO[modo.id] ?? (nombreLlano(modo.nombre) ? nombreConCodigo(modo.nombre) : modo.nombre)
}

/** El nombre de una lectura secundaria de una prueba (`variantes` del resultado), dicho en llano. */
const LECTURA: Record<string, string> = { sujeto: 'por sujeto', casco: 'solo casco', chaleco: 'solo chaleco', combinada: 'combinada' }
/** Lecturas que no se arman por partes: el nombre entero dicho en llano (ALR-06 relee las mismas detecciones
 *  con las reglas de ausencia del EPP). */
const LECTURA_ENTERA: Record<string, string> = { eind_mismo_caption: 'estrategia indirecta, mismas detecciones' }
export const nombreLectura = (nombre: string): string =>
  LECTURA_ENTERA[nombre] ?? nombre.split('_').map((t) => LECTURA[t] ?? t).join(', ')

/** Las causas de una falsa alarma por sujeto en obra real (ERR-01, `tools/evidencia/familias/errores.py`): el
 *  nombre de la figura 7 y qué quiere decir, en una línea. */
export const CAUSA_FALSA_ALARMA: Record<string, { nombre: string; que: string }> = {
  'P-no-detectado': { nombre: 'EPP no detectado', que: 'la referencia dice que el EPP estaba y el detector no lo vio sobre la persona' },
  'P-intermitente': { nombre: 'EPP visto de a ratos', que: 'el EPP se vio, pero no lo bastante seguido para dar la falta por resuelta' },
  'F-sin-persona': { nombre: 'Sin persona en la referencia', que: 'la persona seguida no coincide con ninguna persona de la referencia' },
  U: { nombre: 'Atributo que no se puede ver', que: 'la referencia marca ese elemento como no observable' },
  'F-parcial': { nombre: 'Persona parcial', que: 'la caja cubre solo parte de una persona de la referencia' },
  'P-disputado': { nombre: 'EPP disputado entre personas', que: 'el EPP estaba en la región de esta persona y también en la de otra' },
  'P-fuera-region': { nombre: 'EPP fuera de la región de evaluación', que: 'el EPP se detectó sobre la persona, pero fuera de la región que evalúa la regla' },
  V: { nombre: 'Falta real, breve o fuera de episodio', que: 'la referencia marca la falta, pero breve o fuera de un episodio' },
}

/** Qué fue una alerta de un clip, como lo cuenta el evaluador. */
export const TIPO_DE_ALERTA: Record<string, string> = {
  acierto: 'Acierto', falsa_alarma: 'Falsa alarma', re_alerta: 'Re-alerta (no cuenta como falsa alarma)',
}
