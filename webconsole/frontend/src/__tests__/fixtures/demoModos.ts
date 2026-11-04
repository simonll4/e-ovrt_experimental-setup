import type { DemoModoSesion, DemoModos } from '../../types'

/** Los modos de prompts de la demo como los sirve `GET /api/demo/modos` (forma de
 *  `demo/modos.describir`, contenido recortado de `experiments/demo_defensa/modos.yaml`). */
export const MODOS: DemoModos = {
  default: 'campeon',
  modos: [
    {
      id: 'campeon', nombre: 'Campeón', evidencia: 'congelada', por_defecto: true,
      resumen: 'La configuración del informe: el modelo marca persona, casco y chaleco.',
      nota: 'CR-01 es la condición confiable.',
      prompt_set: 'cr01_cr02_v2_short', pattern_set: 'cr01_cr02_v2', medido_en: null,
      clases: [
        { id: 'person', frases: ['person'], fuente: 'prompts/cr01_cr02_v2_short.yaml' },
        { id: 'helmet', frases: ['helmet'], fuente: 'prompts/cr01_cr02_v2_short.yaml' },
        { id: 'vest', frases: ['vest'], fuente: 'prompts/cr01_cr02_v2_short.yaml' },
      ],
      cifras: [{
        prueba: 'ALR-01', clave: 'f1', que_es: 'F1 de alertas por episodio en el rodaje guionado',
        valor: 0.84058, unidad: null, pendiente: false, texto: null, fuente: 'results/gen2/ALR-01/resultado.json',
      }],
      error: null,
    },
    {
      id: 'edir', nombre: 'E-DIR', evidencia: 'descartada', por_defecto: false,
      resumen: 'Pedirle al modelo la infracción con una frase.',
      nota: 'Es la evidencia detrás de ADR-001 (E-IND).',
      prompt_set: 'edir_v1_pair_nivel_b', pattern_set: 'cr01_cr02_edir_v1', medido_en: 'ALR-04',
      clases: [
        { id: 'person', frases: ['person'], fuente: 'prompts/eind_v1.yaml' },
        { id: 'cr01_spec', frases: ['construction worker without safety helmet'], fuente: 'prompts/edir_v1.yaml' },
        { id: 'cr02_obs', frases: ['person without bright colored safety clothing'], fuente: 'prompts/edir_v1.yaml' },
      ],
      cifras: [
        { prueba: 'ALR-04', clave: 'f1', que_es: 'F1 de alertas por episodio, mismas reglas temporales',
          valor: 0.4615, unidad: null, pendiente: false, texto: null, fuente: 'results/gen2/ALR-04/resultado.json' },
        { prueba: 'PER-01', clave: 'bench_obra/CR-02/f1_edir', que_es: 'CR-02, F1 por persona con la frase E-DIR sola',
          valor: null, unidad: null, pendiente: true, texto: 'cifra pendiente (generación 2)' },
      ],
      error: null,
    },
    {
      id: 'clase_nueva', nombre: 'Clase nueva', evidencia: 'extension', por_defecto: false,
      resumen: 'Vocabulario abierto.', nota: null,
      prompt_set: 'clase_nueva_v1', pattern_set: 'cr01_cr02_v2', medido_en: 'EXT-01',
      clases: [], cifras: [],
      error: 'prompts/clase_nueva_v1.yaml: la clase \'machinery\' no está o no tiene phrasings.default',
    },
  ],
}

/** El `modo_prompts` de una sesión con E-DIR (forma de `demo/modos.resolver` + verificación). */
export const MODO_EDIR_SESION: DemoModoSesion = {
  id: 'edir', nombre: 'E-DIR', evidencia: 'descartada', prompt_set: 'edir_v1_pair_nivel_b',
  clases: MODOS.modos[1].clases,
  payload_sha256: 'd8c4593caae0d119e7f9cd4bc7d219c11c97c15dc134a71a73fc24fa84b22572',
  medido_en: 'ALR-04',
  pattern_set: {
    id: 'cr01_cr02_edir_v1', archivo: 'e-ovrt_control-plane/configs/patterns/cr01_cr02_edir_v1.yaml',
    sha256_archivo: '7200f0874502d0717b0a867eabad566babcef3daffef80e2fb6e0988ccb43141',
  },
  verificacion: { ok: true, items: [] },
}
