import type { ReactNode } from 'react'
import { Badge, Tag } from '../../components/ui'
import type { Gen2Cifra, Gen2Estado, Gen2Veredicto } from '../../types'

/** Los tres veredictos del doc 134 (más los dos estados intermedios del driver),
 *  dichos en llano. El código queda en el `title` para quien lo busque. */
export const VEREDICTO_LABEL: Record<string, string> = {
  identico: 'Idéntico a la generación 1',
  equivalente_con_diferencia: 'Equivalente, con la diferencia declarada',
  otra_combinacion: 'Otra combinación: se muestra al lado, no en reemplazo',
  a_revisar: 'Difiere de la generación 1: lo revisa una persona',
  sin_referencia: 'Sin cifra de la generación 1 para comparar',
}

const ESTADO: Record<Gen2Estado, { tono: 'ok' | 'warn' | 'error' | 'neutral'; texto: string }> = {
  completo: { tono: 'ok', texto: 'Completa' },
  parcial: { tono: 'warn', texto: 'Parcial' },
  fallido: { tono: 'error', texto: 'Falló' },
  sin_correr: { tono: 'neutral', texto: 'Todavía no se corrió' },
  desconocida: { tono: 'neutral', texto: 'No está en el catálogo' },
}

/** El estado del pre-registro (`registro`), cuando no es `activa`. */
export const REGISTRO_LABEL: Record<string, string> = {
  opcional: 'opcional',
  pendiente_decision: 'pendiente de decisión',
  no_se_regenera: 'contraste: vale la generación 1',
}

/** Un contraste que no se regenera no está «sin correr»: su cifra es la de la generación 1. */
export const noSeRegenera = (p: { registro?: string | null; estado: Gen2Estado }) =>
  p.registro === 'no_se_regenera' && p.estado === 'sin_correr'

export function EstadoPrueba({ estado, registro }: { estado: Gen2Estado; registro?: string | null }) {
  if (noSeRegenera({ estado, registro })) {
    return <Badge tone="neutral" title="no_se_regenera">Generación 1: no se regenera</Badge>
  }
  const e = ESTADO[estado] ?? ESTADO.desconocida
  return <Badge tone={e.tono}>{e.texto}</Badge>
}

/** El veredicto propuesto por el driver y el confirmado por una persona no se
 *  confunden: el confirmado lleva quién; el propuesto dice que falta confirmar. */
export function Veredicto({ v }: { v: Gen2Veredicto | null | undefined }) {
  if (!v) return null
  if (v.confirmado) {
    const quien = v.confirmado.quien ? ` por ${v.confirmado.quien}` : ''
    return (
      <Badge tone="ok" title={v.confirmado.valor}>
        {VEREDICTO_LABEL[v.confirmado.valor] ?? v.confirmado.valor} · confirmado{quien}
      </Badge>
    )
  }
  return (
    <Tag title={v.propuesto}>
      Propuesto: {VEREDICTO_LABEL[v.propuesto] ?? v.propuesto} (sin confirmar)
    </Tag>
  )
}

/** Una cifra tal cual la escribió el driver; la consola solo la formatea. */
export function valorTexto(valor: unknown, unidad?: string | null): string {
  if (valor === null || valor === undefined || valor === '') return '—'
  if (typeof valor === 'boolean') return valor ? 'sí' : 'no'
  if (typeof valor === 'number') {
    const texto = valor.toLocaleString('es-AR', { maximumFractionDigits: 4 })
    return unidad ? `${texto} ${unidad}` : texto
  }
  return unidad ? `${String(valor)} ${unidad}` : String(valor)
}

export function CifraFila({ c }: { c: Gen2Cifra }) {
  return (
    <tr>
      <td>{c.nombre}</td>
      <td className="eo-num">
        {valorTexto(c.valor, c.unidad)}
        {c.ic95 && <span className="eo-note--meta"> (IC 95 %: {valorTexto(c.ic95[0])} a {valorTexto(c.ic95[1])})</span>}
        {c.n != null && <span className="eo-note--meta"> · n = {valorTexto(c.n)}</span>}
      </td>
      <td className="eo-num">{valorTexto(c.gen1, c.gen1 == null ? null : c.unidad)}</td>
    </tr>
  )
}

/** Las secciones del informe en orden, con lo que agrupa cada una (doc 135 §3.3). */
export const GRUPOS: Array<{ titulo: string; informe: string; prefijos: string[]; explica: ReactNode }> = [
  { titulo: 'Percepción en imágenes', informe: 'Tabla 51', prefijos: ['IMG', 'EXT'],
    explica: 'Qué tan bien detecta cada modelo personas, cascos, chalecos y cabezas descubiertas sobre 6.477 imágenes, por fuente y agregado; y una clase nueva sin entrenar.' },
  { titulo: 'Estado por persona', informe: 'Tabla 52', prefijos: ['PER'],
    explica: 'Si el sistema determina bien, persona por persona, quién no tiene casco o chaleco.' },
  { titulo: 'Alerta por episodio', informe: 'Tabla 53', prefijos: ['ALR'],
    explica: 'Si las alertas aparecen cuando corresponde, contra la referencia temporal anotada a mano del rodaje y de obra real.' },
  { titulo: 'Tiempo real', informe: 'Tabla 54', prefijos: ['DEN', 'RT', 'DIST'],
    explica: 'Cuánto tarda la cadena en vivo, cuánto rendimiento sobrevive a ver menos cuadros por segundo y cuánto tarda la notificación.' },
  { titulo: 'Referencia', informe: '§17.5.7', prefijos: ['GT'],
    explica: 'Cuánto depende cada conclusión de la anotación manual.' },
  { titulo: 'Integridad y plataforma', informe: 'Anexo E · Tablas B.1 y B.3', prefijos: ['INT', 'PLAT'],
    explica: 'Que los insumos sean exactamente los de la generación 1 y dónde y cómo corrió todo.' },
]

export const prefijoDe = (id: string) => id.split('-')[0]
