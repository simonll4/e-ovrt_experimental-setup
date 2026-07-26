import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import CatalogPage from '../pages/CatalogPage'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getDatasets: vi.fn(),
  getIngestPlugins: vi.fn(),
  getPromptSets: vi.fn(),
}))

vi.mock('../useTarget', () => ({
  useTarget: () => null,
}))

beforeEach(() => vi.clearAllMocks())
afterEach(() => cleanup())

describe('CatalogPage', () => {
  it('las tablas usan la clase de densidad de consola', async () => {
    vi.mocked(api.getIngestPlugins).mockResolvedValue([
      { id: 'p1', kind: 'file', description: 'desc', available: true, enabled: true } as any,
    ])
    vi.mocked(api.getDatasets).mockResolvedValue([])
    vi.mocked(api.getPromptSets).mockResolvedValue([])
    render(<CatalogPage />)
    await waitFor(() => expect(screen.getByText('p1')).toBeTruthy())
    const table = document.querySelector('.eo-table')
    expect(table?.className).toContain('eo-table--dense')
  })
})
