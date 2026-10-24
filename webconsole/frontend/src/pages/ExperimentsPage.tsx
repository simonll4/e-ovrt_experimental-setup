import { useEffect, useState, type ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { ApiError } from '../api'
import { qk } from '../api/keys'
import {
  useCurrentExperiment, useExperimentManifests, useRunExperiment,
} from '../api/queries/experiments'
import { experimentStatusLabel, experimentStatusTone } from '../experimentview'
import { usePreflight } from '../api/queries/platform'
import { AvisoRegistro, EvidenceBadge } from '../components/EvidenceViewControl'
import ClaseChips, { ETIQUETA_CLASE } from '../components/ClaseChips'
import Termino from '../components/Glosario'
import { TERMINO_DE_CLASE } from '../terminos'
import { DeriveExperimentForm } from '../components/DeriveExperimentForm'
import {
  Badge,
  Banner,
  Button,
  Card,
  Disclosure,
  DiscardPrompt,
  EmptyState,
  ErrorBanner,
  Field,
  IconCheck,
  IconWarn,
  LoadingState,
  MonoCell,
  PageHeader,
  RowNameCell,
  SearchInput,
  Select,
  StaleNotice,
  Table,
  TableScroll,
  Tag,
} from '../components/ui'
import { applyPlaneGlossary } from '../labels'
import type { Clase } from '../types'

/** Antigüedad legible de la última ejecución. */
function cuando(iso: string | null | undefined): string {
  if (!iso) return '—'
  const ms = new Date(iso).getTime()
  if (!Number.isFinite(ms)) return '—'
  const min = Math.floor((Date.now() - ms) / 60000)
  if (min < 1) return 'recién'
  if (min < 60) return `hace ${min} min`
  const h = Math.floor(min / 60)
  if (h < 24) return `hace ${h} h`
  return `hace ${Math.floor(h / 24)} d`
}

// Formulario abierto: `selectable` distingue el "Partir de este" de una fila
// (fuente fija, como siempre) del formulario de /experiments/new (fuente
// elegible via el selector "basado en").
type FormMode = { source: string; selectable: boolean } | null

/** Un cambio de formulario pedido mientras había cambios sin guardar. */
type Pedido = { tipo: 'cerrar' } | { tipo: 'abrir'; modo: NonNullable<FormMode> }

function errorMessage(e: unknown): string {
  if (e instanceof ApiError) {
    const payload = (e.payload ?? {}) as { detail?: string; active_experiment_id?: string }
    if (e.status === 409) {
      return `Ya hay un experimento activo: ${payload.active_experiment_id ?? '?'}`
    }
    if (e.status === 422) return 'Manifiesto invalido'
    if (e.status === 502) return 'Servicio no disponible'
    if (e.status === 503) return payload.detail ?? 'Plataforma no lista'
  }
  return String(e)
}

/** Una identidad de plantilla sin resolver (`${EOVRT_EXPERIMENT_ID}`) no es
 *  una ejecución: se muestra literal, consultable, y sin un enlace que no
 *  llevaría a ningún lado. */
const sinResolver = (id: string) => /\$\{[^}]*\}/.test(id)

function Ejecucion({ id }: { id: string }) {
  if (sinResolver(id)) {
    return (
      <span className="eo-unresolved">
        {id}
        <span className="eo-unresolved__why">identidad sin resolver: no hay una ejecución que abrir</span>
      </span>
    )
  }
  return <Link style={{ overflowWrap: 'anywhere' }} to={`/experiments/${id}`}>{id}</Link>
}

export default function ExperimentsPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const isNewRoute = location.pathname === '/experiments/new'
  const preflight = usePreflight()
  const [slug, setSlug] = useState('')
  const [filtro, setFiltro] = useState('')
  const [clase, setClase] = useState<Clase | null>(null)
  const [runError, setRunError] = useState<string | null>(null)
  const [formMode, setFormMode] = useState<FormMode>(null)
  const [formDirty, setFormDirty] = useState(false)
  const [pedido, setPedido] = useState<Pedido | null>(null)
  const [creado, setCreado] = useState<string | null>(null)
  const qc = useQueryClient()

  // Siempre "todas": la separación evidencia/archivada la reemplazó la clase
  // (chips), que filtra del lado del cliente sobre esta misma lista.
  const consultaManifiestos = useExperimentManifests()
  const rows = consultaManifiestos.data ?? null
  const meta = consultaManifiestos.visibility
  const error = consultaManifiestos.error ? String(consultaManifiestos.error) : null
  // Solo se repregunta mientras hay un experimento corriendo (ver la query).
  const current = useCurrentExperiment().data ?? null
  const lanzamiento = useRunExperiment()
  const busy = lanzamiento.isPending

  // Cierra el formulario. /experiments/new es una ruta dedicada: al salir del
  // formulario ahí, se navega de vuelta a /experiments — si no, el efecto de
  // abajo lo reabriría solo, con el primer manifiesto de nuevo.
  const closeForm = () => {
    setFormMode(null)
    setFormDirty(false)
    setPedido(null)
    if (isNewRoute) navigate('/experiments')
  }

  const aplicar = (p: Pedido) => {
    setPedido(null)
    setFormDirty(false)
    if (p.tipo === 'cerrar') closeForm()
    else setFormMode(p.modo)
  }

  /** Cerrar o cambiar de origen con cambios sin guardar pregunta antes. */
  const pedir = (p: Pedido) => {
    if (formMode && formDirty) setPedido(p)
    else aplicar(p)
  }

  const reloadManifests = async () => {
    await qc.invalidateQueries({ queryKey: qk.experiments.manifests })
  }

  // Preselección del desplegable con el primer manifiesto disponible. Sigue
  // siendo un efecto porque es estado de formulario derivado de datos que
  // llegan asincrónicos, no una petición.
  useEffect(() => {
    if (rows && rows.length > 0 && !slug) setSlug(rows[0].slug)
  }, [rows, slug])

  // /experiments/new abre el formulario apenas hay manifiestos para elegir
  // "basado en" (precargado con el primero, como pide el spec).
  useEffect(() => {
    if (isNewRoute && rows && rows.length > 0 && !formMode) {
      setFormMode({ source: rows[0].slug, selectable: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isNewRoute, rows])

  const trigger = async (elegido: string) => {
    if (!elegido || lanzamiento.isPending) return
    setSlug(elegido)
    setRunError(null)
    try {
      const { experiment_id } = await lanzamiento.mutateAsync(elegido)
      navigate(`/experiments/${experiment_id}`)
    } catch (e) {
      setRunError(errorMessage(e))
    }
  }

  // Gate de lanzamiento: sin preflight verde no se lanza (el BFF igualmente lo
  // rechaza con 503; acá se corta antes y con el motivo a la vista).
  const experimentRunning = current?.status === 'running'
  const blocked = !preflight?.ready || experimentRunning
  // Todos los bloqueos, no el primero: mostrar `[0]` obligaba a arreglar uno,
  // reintentar, y descubrir el siguiente.
  const bloqueos: string[] = [
    ...(experimentRunning ? ['Hay un experimento en curso'] : []),
    ...(preflight === null ? ['Verificando servicios…'] : preflight.blockers),
  ]

  const titulo = formMode
    ? formMode.selectable ? 'Nuevo experimento' : `Derivar de ${formMode.source}`
    : isNewRoute ? 'Nuevo experimento' : 'Experimentos'

  // Sin listado todavía: la cabecera queda quieta y sólo el contenido espera o
  // explica el fallo, con reintento.
  if (!rows) {
    return (
      <>
        <PageHeader title={titulo} meta={error ? 'No se pudo leer el catálogo' : 'Cargando el catálogo de manifiestos…'} />
        {error ? (
          <ErrorBanner
            detail={error}
            onRetry={() => void consultaManifiestos.refetch()}
            retrying={consultaManifiestos.isFetching}
          >
            Error listando experimentos: el catálogo de manifiestos no respondió.
          </ErrorBanner>
        ) : (
          <LoadingState lines={5}>Cargando el catálogo de manifiestos…</LoadingState>
        )}
      </>
    )
  }

  const options = rows.map((r) => ({ value: r.slug, label: r.slug }))

  // Conteos SIEMPRE sobre el listado completo (nunca sobre lo ya filtrado):
  // si no, elegir un chip haría desaparecer al resto de los chips.
  const conteos: Partial<Record<Clase, number>> = {}
  for (const r of rows) {
    const c = r.evidence?.clase ?? 'sin_clasificar'
    conteos[c] = (conteos[c] ?? 0) + 1
  }

  const aguja = filtro.trim().toLowerCase()
  const visibles = rows.filter((r) => {
    if (clase && (r.evidence?.clase ?? 'sin_clasificar') !== clase) return false
    if (!aguja) return true
    return `${r.slug} ${r.group ?? ''}`.toLowerCase().includes(aguja)
  })

  // Ausentes en la fixture del contrato congelado: la pantalla tiene que
  // renderizar bien sin ellas.
  const platformTestCount = meta?.platformTestCount
  const platformTestSlugs = meta?.platformTestSlugs
  const totalExecutions = meta?.totalExecutions
  // La proporción, nunca el número absoluto como si fuera estable: el total
  // crece solo. El denominador es TODO lo que hay en disco.
  const proporcionPlataforma = platformTestCount != null && totalExecutions
    ? Math.round((platformTestCount / totalExecutions) * 100)
    : null

  const antesDeEjecutar = (
    <Card
      title="Antes de ejecutar"
      meta={
        bloqueos.length
          ? `${bloqueos.length} bloqueo${bloqueos.length > 1 ? 's' : ''}`
          : 'Todo listo'
      }
    >
      {bloqueos.length === 0 ? (
        <p className="eo-note">
          Los dos motores responden y no hay ningún experimento en curso.
        </p>
      ) : (
        <ul className="eo-blockers">
          {bloqueos.map((b) => (
            <li key={b}>
              <IconWarn />
              <span>{applyPlaneGlossary(b)}</span>
            </li>
          ))}
        </ul>
      )}
      {runError && <ErrorBanner>{applyPlaneGlossary(runError)}</ErrorBanner>}
    </Card>
  )

  const catalogo: ReactNode = rows.length === 0 ? (
    <EmptyState hint="Los manifiestos viven en experiments/ del repositorio.">
      Sin manifiestos todavía
    </EmptyState>
  ) : (
    <>
      <div className="eo-toolbar">
        <SearchInput
          value={filtro}
          onChange={setFiltro}
          placeholder="Buscar por manifiesto o grupo"
          ariaLabel="Buscar manifiestos por nombre o grupo"
        />
        <ClaseChips valor={clase} onChange={setClase} conteos={conteos} />
        <span className="eo-toolbar__count eo-mono">
          {visibles.length} de {rows.length}
        </span>
      </div>

      <Card title="Manifiestos" meta={`${rows.length}`} flush level={formMode ? 3 : 2}>
        {consultaManifiestos.error && (
          <StaleNotice
            what="el catálogo de manifiestos"
            onRetry={() => void consultaManifiestos.refetch()}
            retrying={consultaManifiestos.isFetching}
          />
        )}
        <TableScroll label="Manifiestos">
          <Table aria-label="Manifiestos">
            <thead>
              <tr>
                <th>Manifiesto</th>
                <th>Grupo</th>
                <th>Clase</th>
                <th>Última ejecución</th>
                <th>Estado</th>
                <th className="eo-th--numeric">Corridas</th>
                <th>Cuándo</th>
                <th aria-label="Acciones" />
              </tr>
            </thead>
            <tbody>
              {visibles.map((r) => {
                const ultima = r.last_experiment_id ?? r.experiment_id ?? null
                return (
                  <tr key={r.slug}>
                    <RowNameCell
                      title={<span className="eo-mono">{r.slug}</span>}
                      subtitle={<>{r.description} <EvidenceBadge evidence={r.evidence} /></>}
                    />
                    <td>{r.group ?? '—'}</td>
                    <td>
                      <Tag>
                        <Termino id={TERMINO_DE_CLASE[r.evidence?.clase ?? 'sin_clasificar']}>
                          {ETIQUETA_CLASE[r.evidence?.clase ?? 'sin_clasificar']}
                        </Termino>
                      </Tag>
                    </td>
                    {/* Un manifiesto que nunca se ejecutó no tiene resultado
                        que ver: se muestra apagado y sin enlace. */}
                    <MonoCell>
                      {r.evidence?.executions?.length ? (
                        <div style={{ maxWidth: '36ch' }}>
                          <span className="eo-cell--muted">{r.evidence.executions.length} ejecuciones de evidencia</span>
                          {r.evidence.executions.map(id => (
                            <div key={id}><Ejecucion id={id} /></div>
                          ))}
                        </div>
                      ) : ultima ? (
                        <Ejecucion id={ultima} />
                      ) : (
                        <span className="eo-cell--muted">Nunca se ejecutó</span>
                      )}
                    </MonoCell>
                    <td>
                      {r.last_status ? (
                        <Badge tone={experimentStatusTone({ status: r.last_status })}>
                          {experimentStatusLabel({ status: r.last_status })}
                        </Badge>
                      ) : (
                        <Badge tone="neutral">{r.evidence?.executions?.length ? 'Con evidencia' : 'Sin ejecutar'}</Badge>
                      )}
                    </td>
                    <td className="eo-num">{r.n_runs || '—'}</td>
                    <td className="eo-cell--muted">{cuando(r.last_run_at)}</td>
                    <td className="eo-cell--actions">
                      <Button onClick={() => pedir({ tipo: 'abrir', modo: { source: r.slug, selectable: false } })}>
                        Partir de este
                      </Button>
                      {/* Lanzar desde la fila evita elegir el manifiesto dos
                          veces. En tratamiento secundario: once acciones
                          violetas iguales no dejaban ver la de la pantalla. */}
                      <Button
                        disabled={busy || blocked}
                        aria-busy={(busy && slug === r.slug) || undefined}
                        onClick={() => void trigger(r.slug)}
                      >
                        {busy && slug === r.slug ? 'Lanzando…' : 'Ejecutar'}
                      </Button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </Table>
        </TableScroll>
        {visibles.length === 0 && (
          <EmptyState hint="Probá con otro texto o quitá el filtro de clase.">
            Ningún manifiesto coincide con la búsqueda
          </EmptyState>
        )}
      </Card>

      {/* Sólo si la cabecera está y cuenta algo: la fixture del contrato
          congelado no la manda, y el bloque tiene que desaparecer, no
          romperse ni mostrar un cero. Va al final: es contexto, no catálogo. */}
      {platformTestCount != null && platformTestCount > 0 && (
        <Card title="Pruebas de plataforma" meta="no son experimentos" level={formMode ? 3 : 2}>
          <div className="eo-machine">
            <div className="eo-machine__n">{platformTestCount}</div>
            <div>
              <p className="eo-machine__t">
                <b>Ejecuciones sin manifiesto escritas por la suite de tests</b>
                {/* Nunca "0 slugs" cuando el desglose faltó o llegó corrupto. */}
                {platformTestSlugs && platformTestSlugs.length > 0 ? (
                  <>, repartidas en {platformTestSlugs.length} slugs del orquestador. </>
                ) : (
                  <>. El desglose por slug no está disponible. </>
                )}
                No corresponden a ningún manifiesto del catálogo y no respaldan ninguna
                cifra: son la máquina probándose a sí misma. El total crece solo —la suite
                escribe ejecuciones nuevas en cada corrida completa de la suite—, así que
                {proporcionPlataforma != null ? (
                  <> se cita la proporción (<b>{proporcionPlataforma} % de las {totalExecutions} ejecuciones en disco</b>) y nunca el número absoluto como si fuera estable.</>
                ) : (
                  ' nunca se cita el número absoluto como si fuera estable.'
                )}
              </p>
              {platformTestSlugs && platformTestSlugs.length > 0 && (
                <div className="eo-slugs">
                  {platformTestSlugs.map((s) => (
                    <span key={s.slug} className="eo-slug">{`${s.slug} · ${s.n}`}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </Card>
      )}
    </>
  )

  return (
    <>
      <PageHeader title={titulo} meta={`${rows.length} manifiestos`} />

      {/* Antes de cualquier clase en pantalla: sin el registro o sin la
          taxonomía, la columna Clase y los chips son una clasificación
          fabricada sobre un archivo ausente. */}
      <AvisoRegistro meta={meta} noun="ejecuciones" />

      {current && (
        <Banner tone={current.status === 'running' ? 'live' : 'warn'}>
          Experimento activo{' '}
          <Link to={`/experiments/${current.experiment_id}`}>
            <span className="eo-mono">{current.experiment_id}</span>
          </Link>{' '}
          — <Badge tone={experimentStatusTone(current)}>{experimentStatusLabel(current)}</Badge>
        </Banner>
      )}

      {creado && !formMode && (
        <p className="eo-note eo-feedback" role="status">
          <IconCheck />
          <span>Se creó el manifiesto <span className="eo-mono">{creado}</span>: ya está en el catálogo.</span>
        </p>
      )}

      {formMode ? (
        <>
          {/* El formulario primero; el catálogo completo sigue abajo, plegado,
              para no competir con la creación. */}
          {pedido && (
            <DiscardPrompt
              what="el formulario"
              onKeep={() => setPedido(null)}
              onDiscard={() => aplicar(pedido)}
            />
          )}
          {formMode.selectable && (
            <Field label="Basado en" hint="El manifiesto del que se parte. Cambiarlo vuelve a cargar sus valores.">
              <Select
                value={formMode.source}
                options={options}
                ariaLabel="Basado en"
                onChange={(v) => {
                  if (v !== formMode.source) pedir({ tipo: 'abrir', modo: { ...formMode, source: v } })
                }}
              />
            </Field>
          )}
          <DeriveExperimentForm
            // key: al cambiar la fuente remonta el formulario entero — mismo
            // mecanismo de precarga que al abrirlo por primera vez, sin
            // arrastrar campos "tocados" de la fuente anterior.
            key={`${formMode.selectable ? 'nuevo' : 'derivar'}:${formMode.source}`}
            source={formMode.source}
            mode={formMode.selectable ? 'create' : 'derive'}
            showTitle={false}
            onDirtyChange={setFormDirty}
            onCancel={() => pedir({ tipo: 'cerrar' })}
            onDone={async (newSlug) => {
              // Se espera la recarga ANTES de seleccionar: si no, el desplegable
              // queda por un instante con un valor que no tiene opción.
              await reloadManifests()
              setSlug(newSlug)
              setCreado(newSlug)
              closeForm()
            }}
          />
          <Disclosure summary={`Manifiestos existentes (${rows.length})`}>
            {antesDeEjecutar}
            {catalogo}
          </Disclosure>
        </>
      ) : (
        <>
          {antesDeEjecutar}
          {catalogo}
        </>
      )}
    </>
  )
}
