import { afterEach, expect, it } from 'vitest'
import { cleanup, render, screen } from '../test-utils'
import { EvidenceBadge } from '../components/EvidenceViewControl'
import type { EvidenceInfo } from '../types'

afterEach(() => cleanup())

/**
 * `EvidenceBadge` sigue viva y en uso en dos pantallas (RunsPage, ExperimentsPage)
 * pero se quedó sin cobertura propia cuando `EvidenceView.test.tsx` (Task 7) se
 * borró — ese archivo probaba el control de vista que Task 7 reemplazó, pero de
 * paso ejercitaba este componente al montar la página entera. Repuesto acá, sin
 * pasar por una pantalla completa.
 */
const evidencia = (over: Partial<EvidenceInfo> = {}): EvidenceInfo => ({
  is_evidence: true,
  result_ids: ['clip_bench/a', 'realtime/b'],
  collections: ['dbe_video'],
  clase: 'resultado',
  ...over,
})

it('con dos result_ids, muestra el primero como etiqueta y los dos en el title del tooltip', () => {
  render(<EvidenceBadge evidence={evidencia()} />)
  const badge = screen.getByText('clip_bench/a')
  expect(badge.parentElement?.title).toBe('clip_bench/a\nrealtime/b')
  // La etiqueta es sólo el primero: el segundo vive en el tooltip, no repetido en pantalla.
  expect(screen.queryByText('realtime/b')).toBeNull()
})

it('con un solo result_id, la etiqueta y el title coinciden', () => {
  render(<EvidenceBadge evidence={evidencia({ result_ids: ['clip_bench/a'] })} />)
  const badge = screen.getByText('clip_bench/a')
  expect(badge.parentElement?.title).toBe('clip_bench/a')
})

it('sin evidencia (is_evidence false) no renderiza nada', () => {
  const { container } = render(
    <EvidenceBadge evidence={evidencia({ is_evidence: false, result_ids: [], clase: 'sin_clasificar' })} />,
  )
  expect(container.firstChild).toBeNull()
})

it('sin `evidence` (undefined) tampoco renderiza nada', () => {
  const { container } = render(<EvidenceBadge />)
  expect(container.firstChild).toBeNull()
})
