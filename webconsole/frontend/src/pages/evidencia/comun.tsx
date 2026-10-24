import type { ReactNode } from 'react'
import { ApiError } from '../../api'
import { EmptyState, ErrorBanner, LoadingState, PageHeader, Toggletip } from '../../components/ui'

/** Rótulo legible de los roles del registro que esta consola conoce. Un rol
 *  que no está acá se muestra con su código, sin inventarle nombre; los
 *  conocidos muestran el nombre Y el código. */
export const ROL_LABEL: Record<string, string> = {
  campaign_media: 'Corridas de detección de la campaña',
  campaign_control: 'Corridas de reglas de la campaña',
  control_replay_empirico: 'Repetición empírica de reglas',
  distribucion_live: 'Distribución en vivo',
  benchmark_realtime: 'Banco en tiempo real',
  nivel_a_primaria: 'Nivel A, primaria',
  nivel_a_replica: 'Nivel A, réplica',
  seleccion_modelos: 'Selección de modelos',
  benchmark_modelos: 'Banco de modelos',
  claqueta_y_guards_negativos: 'Claqueta y controles negativos',
}

export function Rol({ role }: { role: string }) {
  const label = ROL_LABEL[role]
  if (!label) return <span className="eo-mono eo-rol__code">{role}</span>
  return <>{label} <span className="eo-mono eo-rol__code">{role}</span></>
}

/** Una cifra con su procedencia dicha en texto. Citada (no leída de un
 *  artefacto de este repositorio) lleva el rótulo y la fuente a un toque; el
 *  `title` queda como complemento para el mouse. */
export function Cifra({
  valor,
  origen,
  fuente,
  className,
}: {
  valor: ReactNode
  origen: string | null | undefined
  fuente: string | null | undefined
  className?: string
}) {
  const citada = origen === 'citada'
  return (
    <>
      <span
        className={[className, citada ? 'eo-cifra--cit' : ''].filter(Boolean).join(' ') || undefined}
        title={fuente ?? undefined}
      >
        {valor}
      </span>
      {valor != null && valor !== '—' && (
        <span className="eo-origen eo-fig__src">
          {citada ? 'citada' : 'leída del artefacto'}
          {citada && fuente && (
            <Toggletip label="fuente" ariaLabel="Fuente de la cifra citada">{fuente}</Toggletip>
          )}
        </span>
      )}
    </>
  )
}

/** Envoltorio común de todos los niveles de evidencia: la misma contención y
 *  la misma cabecera, también cuando el archivo falta o la lectura falla. */
export function Evidencia({ children }: { children: ReactNode }) {
  return <div className="eo-evidence">{children}</div>
}

/** Los estados de una lectura del archivo, con la cabecera en su lugar. */
export function EstadoDeLectura({
  titulo,
  q,
  noExiste,
}: {
  titulo: string
  q: { isPending: boolean; error: unknown; isFetching: boolean; refetch: () => unknown }
  /** Texto para un 404 real, si ese nivel puede decir "no existe". */
  noExiste?: string
}) {
  if (q.isPending) {
    return (
      <Evidencia>
        <PageHeader title={titulo} meta="Lectura del archivo curado" />
        <LoadingState lines={4}>Leyendo archivo de evidencia…</LoadingState>
      </Evidencia>
    )
  }
  const es404 = q.error instanceof ApiError && q.error.status === 404
  return (
    <Evidencia>
      <PageHeader title={titulo} />
      {es404 && noExiste ? (
        <ErrorBanner>{noExiste}</ErrorBanner>
      ) : (
        <ErrorBanner detail={String(q.error)} onRetry={() => void q.refetch()} retrying={q.isFetching}>
          No se pudo leer el archivo de evidencia.
        </ErrorBanner>
      )}
    </Evidencia>
  )
}

/** El archivo no está en esta máquina: una condición del entorno, dicha con su
 *  remedio, dentro de la misma estructura que el resto. */
export function ArchivoAusente({ message }: { message?: string | null }) {
  return (
    <Evidencia>
      <PageHeader title="Evidencia" meta="Lectura del archivo curado" />
      <EmptyState hint={message ?? undefined}>Archivo de evidencia no disponible</EmptyState>
    </Evidencia>
  )
}
