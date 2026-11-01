import { describe, expect, it } from 'vitest'
import { POLL } from '../api/queryClient'
import { reintentoSiFalla } from '../api/queries/runs'

/** El listado de corridas lo contesta el motor activo; mientras se reinicia (~30 s después de cada
 *  sesión de la demo) da 502. Es un fallo que se arregla solo: la pantalla tiene que volver a
 *  pedirlo sin que nadie apriete «Reintentar», y dejar de insistir cuando ya funciona. */
describe('reintentoSiFalla', () => {
  it('en error vuelve a pedir cada POLL.plataforma', () => {
    expect(reintentoSiFalla({ state: { status: 'error' } })).toBe(POLL.plataforma)
  })
  it('con la consulta sana o cargando no sondea (el listado es historial)', () => {
    expect(reintentoSiFalla({ state: { status: 'success' } })).toBe(false)
    expect(reintentoSiFalla({ state: { status: 'pending' } })).toBe(false)
  })
})
