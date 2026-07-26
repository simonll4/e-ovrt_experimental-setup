import { describe, expect, it, afterEach } from 'vitest'
import { cleanup, render } from '@testing-library/react'
import { IconPlay, IconStop, IconNavRuns } from '../../components/ui/icons'

afterEach(() => cleanup())

describe('icons', () => {
  it('cada icono renderiza un svg 16x16 marcado aria-hidden', () => {
    for (const Icon of [IconPlay, IconStop, IconNavRuns]) {
      const { container } = render(<Icon />)
      const svg = container.querySelector('svg')
      expect(svg).toBeTruthy()
      expect(svg?.getAttribute('aria-hidden')).toBe('true')
    }
  })
})
