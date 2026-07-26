import { describe, expect, it, afterEach, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { Table, MonoCell, NumCell, SortableHeader, RowNameCell } from '../../components/ui'

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

describe('SortableHeader', () => {
  it('muestra la flecha solo en la columna activa, en la direccion correcta', () => {
    render(
      <table><thead><tr>
        <SortableHeader label="Corrida" sortKey="nm" sortState={{ key: 'nm', dir: 'asc' }} onSort={() => {}} />
        <SortableHeader label="Cuadros/s" sortKey="fps" sortState={{ key: 'nm', dir: 'asc' }} onSort={() => {}} />
      </tr></thead></table>,
    )
    const ths = screen.getAllByRole('columnheader')
    expect(ths[0].textContent).toContain('↑')
    expect(ths[1].textContent).not.toContain('↑')
    expect(ths[1].textContent).not.toContain('↓')
  })

  it('clic dispara onSort con la clave de la columna', () => {
    const onSort = vi.fn()
    render(
      <table><thead><tr>
        <SortableHeader label="Corrida" sortKey="nm" sortState={null} onSort={onSort} />
      </tr></thead></table>,
    )
    fireEvent.click(screen.getByRole('columnheader'))
    expect(onSort).toHaveBeenCalledWith('nm')
  })
})

describe('RowNameCell', () => {
  it('con titulo y subtitulo, el subtitulo va en monoespaciada', () => {
    render(<table><tbody><tr><RowNameCell title="Ronda nocturna" subtitle="run_20260725_143012" /></tr></tbody></table>)
    expect(screen.getByText('Ronda nocturna')).toBeTruthy()
    expect(screen.getByText('run_20260725_143012').className).toContain('eo-mono')
  })
})
