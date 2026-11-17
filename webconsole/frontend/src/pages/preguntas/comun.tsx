import { Fragment } from 'react'
import type { CifraPregunta } from '../../types'

/** Una cifra resuelta por el backend, como texto: la consola solo la formatea (plan §9). Una que no
 *  resolvió se muestra como «—», nunca como un número inventado. */
export function textoCifra(c: CifraPregunta | undefined): string {
  if (!c || !c.ok || c.valor === null || c.valor === undefined) return '—'
  const { valor } = c
  if (c.total != null) return `${String(valor)} de ${c.total}`
  if (c.formato === 'verificado' || typeof valor === 'boolean') {
    if (valor === true || valor === 'ok') return 'sí'
    if (valor === false) return 'no'
  }
  if (typeof valor !== 'number') return conUnidad(String(valor), c.unidad)
  const decimales = c.decimales
  const opciones: Intl.NumberFormatOptions = decimales == null
    ? { maximumFractionDigits: 4 }
    : { minimumFractionDigits: decimales, maximumFractionDigits: decimales }
  if (c.formato === 'porcentaje') return `${(valor * 100).toLocaleString('es-AR', opciones)} %`
  const texto = valor.toLocaleString('es-AR', opciones)
  return conUnidad(c.formato === 'signo' && valor > 0 ? `+${texto}` : texto, c.unidad)
}

const conUnidad = (texto: string, unidad?: string | null) => (unidad ? `${texto} ${unidad}` : texto)

const MARCADOR = /\{([a-z0-9_]+)\}/g

/** Un texto del archivo de preguntas con sus marcadores `{id}` reemplazados por la cifra resuelta. */
export function Plantilla({ texto, cifras }: { texto: string; cifras: Record<string, CifraPregunta> }) {
  const partes = texto.split(MARCADOR)
  return (
    <>
      {partes.map((parte, i) => (i % 2 === 0
        ? <Fragment key={i}>{parte}</Fragment>
        : <b key={i} className="eo-cifra-resuelta">{textoCifra(cifras[parte])}</b>))}
    </>
  )
}

/** Una celda de una tabla del informe: una o varias cifras, cada una con su etiqueta. */
export function CeldaCifras({ items }: { items: CifraPregunta[] | null }) {
  if (!items || items.length === 0) return <span className="eo-note--meta">—</span>
  return (
    <>
      {items.map((c, i) => (
        <Fragment key={i}>
          {i > 0 && <span className="eo-celda__sep"> · </span>}
          {/* Cada cifra con su etiqueta va junta: si la celda no entra, se parte entre una cifra y la siguiente. */}
          <span className="eo-celda__item">
            {c.etiqueta && <span className="eo-celda__etiqueta">{c.etiqueta} </span>}
            <span className={c.ok ? 'eo-celda__valor' : 'eo-celda__valor eo-celda__valor--falla'} title={c.error}>
              {textoCifra(c)}
            </span>
          </span>
        </Fragment>
      ))}
    </>
  )
}

/** Una fecha `AAAA-MM-DD` dicha en llano («29 de octubre de 2026»). */
export function fechaLlana(iso: string | null | undefined): string {
  if (!iso) return '—'
  const [a, m, d] = iso.split('-').map(Number)
  if (!a || !m || !d) return iso
  return new Date(Date.UTC(a, m - 1, d)).toLocaleDateString('es-AR', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' })
}
