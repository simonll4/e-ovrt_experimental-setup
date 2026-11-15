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
  'E-IND': 'Por ausencia del EPP',
  'E-DIR': 'Por detección directa',
  'E-HYB': 'Por disyunción',
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
  'ALR-04': 'Alerta por episodio por detección directa',
  'ALR-05': 'Alerta por episodio por disyunción',
  'ALR-06': 'Alerta por episodio con el vocabulario nativo de cabeza descubierta',
  'ALR-07': 'Obra real, por escena',
  'ALR-08': 'Obra real, por sujeto',
  'ALR-09': 'Obra real a mayor resolución',
  'ALR-10': 'Obra real con el perfil operativo y otro umbral de caja',
  'ALR-11': 'Alerta por episodio con YOLOE-26s',
  'ALR-12': 'Obra real con YOLOE-26s',
  'ALR-13': 'La regla con umbrales de EPP más exigentes, en el rodaje',
  'ALR-14': 'La regla con umbrales de EPP más exigentes, en obra real',
  // Errores y seguimiento (§17.5.4, §18.3)
  'ERR-01': 'Por qué se equivoca en obra real',
  'ERR-02': 'Las falsas alarmas de obra real según la resolución',
  'SEG-01': 'Fragmentación de identidad del rastreador',
  'VIS-01': 'Cuadros anotados: aciertos y fallos',
  // Tiempo real (Tabla 54)
  'DEN-01': 'Densidad: techo en vivo, por escena',
  'DEN-02': 'Densidad: techo en vivo, por sujeto',
  'DEN-03': 'Densidad: intermedia, por escena',
  'DEN-04': 'Densidad: intermedia, por sujeto',
  'DEN-05': 'Densidad: peor caso, por escena',
  'DEN-06': 'Densidad: peor caso, por sujeto',
  'DEN-07': 'Ganancia por identidad en las cuatro densidades',
  'RT-01': 'Sobrecarga de la plataforma con detector simulado',
  'RT-02': 'Relectura frente a transmisión',
  'RT-03': 'Latencia en vivo con la OAK-D',
  'RT-04': 'Obra simulada en vivo',
  'RT-05': 'Modelos y cadencias de cámara en vivo',
  'RT-06': 'Obra simulada en vivo con la cámara IP',
  'RT-07': 'Obra simulada en vivo con otro chaleco',
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
export function nombreLlano(codigo: string): string | undefined {
  return NOMBRE_DE_CODIGO[codigo] ?? NOMBRE_DE_PRUEBA[codigo]
}

/** «Nombre llano CÓDIGO» como texto plano, para un `title`, un `aria-label` o una miga. Sin
 *  nombre conocido queda el código solo: nunca una cadena vacía. */
export function nombreConCodigo(codigo: string): string {
  const nombre = nombreLlano(codigo)
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
