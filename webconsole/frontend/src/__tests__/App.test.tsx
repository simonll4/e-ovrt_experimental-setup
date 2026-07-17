import { describe, expect, it, vi, afterEach } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../App'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getTarget: vi.fn().mockResolvedValue(null),
  listRuns: vi.fn().mockResolvedValue([]),
}))

afterEach(() => cleanup())

describe('App', () => {
  it('renderiza el título de la consola', () => {
    render(<MemoryRouter><App /></MemoryRouter>)
    expect(screen.getByText('E-OVRT')).toBeTruthy()
  })
})
