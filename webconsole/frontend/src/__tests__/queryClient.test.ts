import { describe, expect, it } from 'vitest'
import { reintentar } from '../api/queryClient'
import { ApiError } from '../api'

/**
 * Política de reintentos.
 *
 * Los tests de pantalla usan un QueryClient con `retry: false` (ver
 * `test-utils.tsx`), así que ninguno de ellos ejercita esto: hay que probarlo
 * acá o no se prueba en ningún lado. De hecho el 501 se escapó justamente por
 * eso — el test de Plataforma pasaba y la pantalla real quedaba en «Cargando…».
 */
describe('reintentar', () => {
  it('no reintenta un 4xx: es una respuesta sobre la petición, no un fallo pasajero', () => {
    expect(reintentar(0, new ApiError(404, null))).toBe(false)
    expect(reintentar(0, new ApiError(409, null))).toBe(false)
    expect(reintentar(0, new ApiError(422, null))).toBe(false)
  })

  // Regresión: 501 es 5xx, así que caía en la rama de reintentos. El BFF lo usa
  // como estado de interfaz permanente ("orquestación no habilitada"), y mientras
  // se reintentaba la pantalla no llegaba nunca a mostrarlo.
  it('no reintenta un 501: la orquestación deshabilitada no se arregla insistiendo', () => {
    expect(reintentar(0, new ApiError(501, null))).toBe(false)
  })

  it('reintenta los demás 5xx, que sí pueden mejorar solos', () => {
    expect(reintentar(0, new ApiError(500, null))).toBe(true)
    expect(reintentar(0, new ApiError(502, null))).toBe(true)
    expect(reintentar(0, new ApiError(503, null))).toBe(true)
  })

  it('reintenta la red caída, pero se rinde a las dos veces', () => {
    const caida = new TypeError('Failed to fetch')
    expect(reintentar(0, caida)).toBe(true)
    expect(reintentar(1, caida)).toBe(true)
    expect(reintentar(2, caida)).toBe(false)
  })
})
