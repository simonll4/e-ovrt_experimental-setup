import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render } from '../test-utils'
import NombreCodigo, { ConCodigos } from '../components/ui/NombreCodigo'
import { NOMBRE_DE_CODIGO, NOMBRE_DE_PRUEBA, nombreConCodigo } from '../vocabulario'

afterEach(() => cleanup())

/** Las pruebas del catálogo de la campaña: una carpeta por prueba en experiments/evidencia. */
const CATALOGO = Object.keys(import.meta.glob('../../../../experiments/evidencia/*/prueba.yaml'))
  .map((ruta) => ruta.split('/').slice(-2)[0])

/** Lo que el plan saca de la interfaz (§4): ni la jerga de la campaña ni el público. */
const FUERA = /generaci[oó]n|campe[oó]n|tribunal|observaci[oó]n|pre-?registr|veredicto/i

describe('vocabulario (plan §4)', () => {
  it('lee el catálogo real de la campaña', () => {
    expect(CATALOGO.length).toBeGreaterThan(40)
    expect(CATALOGO).toContain('ALR-01')
  })

  it('cada prueba del catálogo tiene su nombre llano, y no sobra ninguno', () => {
    expect(CATALOGO.filter((id) => !NOMBRE_DE_PRUEBA[id])).toEqual([])
    expect(Object.keys(NOMBRE_DE_PRUEBA).filter((id) => !CATALOGO.includes(id))).toEqual([])
  })

  it('ningún nombre usa un término que el plan saca de la interfaz ni repite su código', () => {
    for (const [codigo, nombre] of Object.entries({ ...NOMBRE_DE_CODIGO, ...NOMBRE_DE_PRUEBA })) {
      expect(nombre, codigo).not.toMatch(FUERA)
      expect(nombre, codigo).not.toContain(codigo)
    }
  })

  it('los códigos del §4.2 del plan, con su nombre', () => {
    expect(nombreConCodigo('CR-01')).toBe('Sin casco CR-01')
    expect(nombreConCodigo('CR-02')).toBe('Sin chaleco CR-02')
    expect(nombreConCodigo('E-IND')).toBe('Por ausencia del EPP E-IND')
    expect(nombreConCodigo('E-DIR')).toBe('Por detección directa E-DIR')
    expect(nombreConCodigo('ALR-01')).toBe('Alerta por episodio, por escena ALR-01')
    expect(nombreConCodigo('G2A')).toBe('Latencia por cuadro G2A')
  })

  it('en pantalla, el nombre va primero y el código al lado, en su propia marca', () => {
    const { container } = render(<NombreCodigo codigo="CR-01" />)
    expect(container.textContent).toBe('Sin casco CR-01')
    expect(container.querySelector('code.eo-codigo')?.textContent).toBe('CR-01')
  })

  it('un código sin nombre queda solo, nunca vacío', () => {
    const { container } = render(<NombreCodigo codigo="CR-99" />)
    expect(container.textContent).toBe('CR-99')
    expect(nombreConCodigo('CR-99')).toBe('CR-99')
  })

  it('dentro de un texto, cada código lleva su nombre llano delante, sin repetirlo si ya está', () => {
    const texto = (t: string) => render(<ConCodigos texto={t} />).container.textContent
    expect(texto('CR-02 como el guion')).toBe('Sin chaleco CR-02 como el guion')
    expect(texto('Imágenes, CR-01: F1')).toBe('Imágenes, sin casco CR-01: F1')
    expect(texto('Latencia por cuadro G2A, p95')).toBe('Latencia por cuadro G2A, p95')
    expect(texto('Sin códigos')).toBe('Sin códigos')
  })
})
