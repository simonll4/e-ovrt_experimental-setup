import {
  createContext, useContext, useEffect, useMemo, useState, type ReactNode,
} from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getDocumentacion, qk } from '../api'
import type { TerminoDef } from '../types'

/** El vocabulario de la consola, compartido por todas las pantallas.
 *
 *  REGLA QUE NO SE NEGOCIA: un término **sin definición se renderiza como texto
 *  plano**, nunca como algo clickeable que no dice nada. Este proyecto ya se
 *  comió ocho veces el mismo defecto —una ausencia de dato convertida en una
 *  afirmación— y un chip marcado que al abrirlo no explica nada es exactamente
 *  eso. `Termino` sólo marca lo que encontró en el vocabulario cargado.
 *
 *  El provider NO pide nada hasta que se monta el primer `Termino`: una pantalla
 *  sin términos marcados no hace ninguna petición. Y sin provider —un
 *  componente renderizado suelto, como hacen varios tests— todo término cae a
 *  texto plano sin pedir ni romper.
 */
interface Glosario {
  terminos: Record<string, TerminoDef>
  pedir: () => void
}

const GlosarioCtx = createContext<Glosario | null>(null)

export function GlosarioProvider({ children }: { children: ReactNode }) {
  const [pedido, setPedido] = useState(false)
  const q = useQuery({
    queryKey: qk.documentacion,
    queryFn: getDocumentacion,
    enabled: pedido,
    // El archivo lo edita una persona y se lee del disco: no hay nada que
    // refrescar mientras la consola está abierta.
    staleTime: Infinity,
  })
  const valor = useMemo<Glosario>(() => ({
    terminos: q.data?.terminos ?? {},
    pedir: () => setPedido(true),
  }), [q.data])
  return <GlosarioCtx.Provider value={valor}>{children}</GlosarioCtx.Provider>
}

/** La definición de un término, o `undefined`. Las pantallas que necesitan
 *  decidir algo con el dato (y no sólo mostrarlo) preguntan por acá. */
export function useTermino(id: string): TerminoDef | undefined {
  const ctx = useContext(GlosarioCtx)
  const pedir = ctx?.pedir
  useEffect(() => { pedir?.() }, [pedir])
  return ctx?.terminos[id]
}

/** Un término marcado: subrayado punteado, la definición en el `title` y
 *  enlace a su entrada en `/documentacion` — la misma convención con la que la
 *  consola ya marca una cifra citada (`.eo-cifra--cit`).
 *
 *  `children` manda sobre el nombre del vocabulario: la pantalla ya sabe cómo
 *  escribe ese término (p. ej. «CR-01 — Presencia de persona sin casco») y el
 *  glosario no se lo pisa. */
export default function Termino({
  id, children, className,
}: { id: string; children?: ReactNode; className?: string }) {
  const def = useTermino(id)
  const texto = children ?? def?.termino ?? id
  if (!def) return <>{texto}</>
  return (
    <Link
      className={['eo-termino', className].filter(Boolean).join(' ')}
      to={`/documentacion#${encodeURIComponent(def.id)}`}
      title={`${def.termino} — ${def.definicion}`}
    >
      {texto}
    </Link>
  )
}
