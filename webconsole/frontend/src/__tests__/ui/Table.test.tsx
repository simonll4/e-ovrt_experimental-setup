import { describe, expect, it, afterEach } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { Table, MonoCell, NumCell } from '../../components/ui'

afterEach(() => cleanup())

describe('Table', () => {
  it('renderiza un <table> con las clases eo-table y eo-table--dense', () => {
    const { container } = render(
      <Table>
        <tbody><tr><td>fila</td></tr></tbody>
      </Table>,
    )
    const table = container.querySelector('table')
    expect(table?.className).toContain('eo-table')
    expect(table?.className).toContain('eo-table--dense')
  })
})

describe('MonoCell', () => {
  it('renderiza un <td> monoespaciado con el contenido y title opcional', () => {
    render(
      <table><tbody><tr><MonoCell title="run_20260726_100000">run_20260726_100000</MonoCell></tr></tbody></table>,
    )
    const cell = screen.getByText('run_20260726_100000')
    expect(cell.tagName).toBe('TD')
    expect(cell.className).toContain('eo-mono')
    expect(cell.getAttribute('title')).toBe('run_20260726_100000')
  })
})

describe('NumCell', () => {
  it('renderiza un <td> alineado a la derecha con cifras tabulares', () => {
    render(<table><tbody><tr><NumCell>42</NumCell></tr></tbody></table>)
    expect(screen.getByText('42').className).toContain('eo-num')
  })
})
