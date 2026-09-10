import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { ApiError } from '../api'
import { qk } from '../api/keys'
import {
  useCurrentExperiment, useExperimentManifests, useRunExperiment,
} from '../api/queries/experiments'
import { experimentStatusLabel, experimentStatusTone } from '../experimentview'
import { usePreflight } from '../api/queries/platform'
import PlatformStatus from '../components/PlatformStatus'
import EvidenceViewControl, { EvidenceBadge, useEvidenceView } from '../components/EvidenceViewControl'
import { DeriveExperimentForm } from '../components/DeriveExperimentForm'
import {
  Badge,
  Banner,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Field,
  IconWarn,
  MonoCell,
  PageHeader,
  RowNameCell,
  SearchInput,
  Select,
  Table,
} from '../components/ui'
import { applyPlaneGlossary } from '../labels'

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

// Formulario abierto: `selectable` distingue el "Derivar" de una fila (fuente
// fija, como siempre) del formulario de /experiments/new (fuente elegible via
// el selector "basado en").
type FormMode = { source: string; selectable: boolean } | null

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

export default function ExperimentsPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const isNewRoute = location.pathname === '/experiments/new'
  const preflight = usePreflight()
  const [slug, setSlug] = useState('')
  const [filtro, setFiltro] = useState('')
  const [runError, setRunError] = useState<string | null>(null)
  const [formMode, setFormMode] = useState<FormMode>(null)
  const qc = useQueryClient()
  const [vista, setVista] = useEvidenceView('experiments')

  const consultaManifiestos = useExperimentManifests(vista)
  const rows = consultaManifiestos.data ?? null
  const error = consultaManifiestos.error ? String(consultaManifiestos.error) : null
  // Solo se repregunta mientras hay un experimento corriendo (ver la query).
  const current = useCurrentExperiment().data ?? null
  const lanzamiento = useRunExperiment()
  const busy = lanzamiento.isPending

  // Cierra el formulario. /experiments/new es una ruta dedicada: al salir del
  // formulario ahí, se navega de vuelta a /experiments — si no, la ruta sigue
  // siendo /experiments/new con formMode en null y el efecto de abajo lo
  // reabriría solo, con el primer manifiesto de nuevo (perdiendo lo elegido).
  const closeForm = () => {
    setFormMode(null)
    if (isNewRoute) navigate('/experiments')
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
    if (!elegido) return
    setSlug(elegido)
    setRunError(null)
    try {
      const { experiment_id } = await lanzamiento.mutateAsync(elegido)
      navigate(`/experiments/${experiment_id}`)
    } catch (e) {
      setRunError(errorMessage(e))
    }
    // `busy` lo lleva la mutación (`lanzamiento.isPending`): no hay que
    // acordarse de bajarlo en un `finally`.
  }

  // Gate de lanzamiento: sin preflight verde no se lanza (el BFF igualmente lo
  // rechaza con 503; acá se corta antes y con el motivo a la vista).
  const experimentRunning = current?.status === 'running'
  const blocked = !preflight?.ready || experimentRunning
  // Todos los bloqueos, no el primero: `preflight.blockers` siempre fue un
  // array y mostrar `[0]` obligaba a arreglar uno, reintentar, y descubrir el
  // siguiente. Se listan juntos para poder resolverlos de una.
  const bloqueos: string[] = [
    ...(experimentRunning ? ['Hay un experimento en curso'] : []),
    ...(preflight === null ? ['Verificando servicios…'] : preflight.blockers),
  ]

  if (error) return <ErrorBanner>Error listando experimentos: {error}</ErrorBanner>
  if (!rows) return <p className="eo-empty">Cargando…</p>

  const options = rows.map((r) => ({ value: r.slug, label: r.slug }))

  const aguja = filtro.trim().toLowerCase()
  const visibles = aguja
    ? rows.filter((r) => `${r.slug} ${r.group ?? ''}`.toLowerCase().includes(aguja))
    : rows

  return (
    <>
      {/* Sin acción propia en el encabezado: "+ Nuevo experimento" ya vive en la
          barra lateral, y repetirlo acá chocaba con el título de la tarjeta del
          formulario, que también dice "Nuevo experimento". */}
      <PageHeader title="Experimentos" meta={`${rows.length} manifiestos`} />
      <EvidenceViewControl view={vista} onChange={setVista}
        meta={consultaManifiestos.visibility} noun="ejecuciones" />

      {current && (
        <Banner tone={current.status === 'running' ? 'live' : 'warn'}>
          Experimento activo{' '}
          <Link to={`/experiments/${current.experiment_id}`}>
            <span className="eo-mono">{current.experiment_id}</span>
          </Link>{' '}
          — <Badge tone={experimentStatusTone(current)}>{experimentStatusLabel(current)}</Badge>
        </Banner>
      )}

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
            <PlatformStatus status={preflight} /> Los dos motores responden y no hay ningún
            experimento en curso.
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

      {formMode && (
        <>
          {formMode.selectable && (
            <Field label="Basado en">
              <Select
                value={formMode.source}
                options={options}
                ariaLabel="Basado en"
                onChange={(v) => setFormMode({ ...formMode, source: v })}
              />
            </Field>
          )}
          <DeriveExperimentForm
            // key: al cambiar la fuente en el selector de arriba, remonta el
            // formulario entero — mismo mecanismo de precarga que al abrirlo
            // por primera vez, sin duplicar esa lógica ni arrastrar campos
            // "tocados" de la fuente anterior.
            key={formMode.source}
            source={formMode.source}
            mode={formMode.selectable ? 'create' : 'derive'}
            onCancel={closeForm}
            onDone={async (newSlug) => {
              // Se espera la recarga ANTES de seleccionar: si no, el desplegable
              // queda por un instante con un valor que no tiene opción, y muestra
              // el placeholder — el operador vería una cosa y lanzaría otra, justo
              // en el momento en que quiere confirmar qué va a correr.
              await reloadManifests()
              setSlug(newSlug)
              closeForm()
            }}
          />
        </>
      )}
      {rows.length === 0 ? (
        vista !== 'todas' && consultaManifiestos.visibility ? (
          <EmptyState hint="Elegí Todas para consultar las recetas del catálogo.">
            No hay manifiestos en esta vista
          </EmptyState>
        ) : (
          <EmptyState hint="Los manifiestos viven en experiments/ del repositorio.">
            Sin manifiestos todavía
          </EmptyState>
        )
      ) : (
        <>
          <div className="eo-toolbar">
            <SearchInput
              value={filtro}
              onChange={setFiltro}
              placeholder="Buscar por manifiesto o grupo"
              ariaLabel="Buscar manifiestos por nombre o grupo"
            />
            <span className="eo-toolbar__count eo-mono">
              {visibles.length} de {rows.length}
            </span>
          </div>

          <Card title="Manifiestos" meta={`${rows.length}`} flush>
            <Table>
              <thead>
                <tr>
                  <th>Manifiesto</th>
                  <th>Grupo</th>
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
                      {/* Un manifiesto que nunca se ejecutó no tiene resultado
                          que ver: se muestra apagado y sin enlace en vez de un
                          guion que no explica nada. */}
                      <MonoCell>
                        {r.evidence?.executions?.length ? (
                          <div style={{ maxWidth: '36ch' }}>
                            <span className="eo-cell--muted">{r.evidence.executions.length} ejecuciones de evidencia</span>
                            {r.evidence.executions.map(id => (
                              <div key={id}><Link style={{ overflowWrap: 'anywhere' }} to={`/experiments/${id}`}>{id}</Link></div>
                            ))}
                          </div>
                        ) : ultima ? (
                          <Link to={`/experiments/${ultima}`}>{ultima}</Link>
                        ) : (
                          <span
                            className="eo-cell--muted"
                            title="Todavía no se ejecutó, no hay resultado que ver"
                          >
                            Nunca se ejecutó
                          </span>
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
                        <Button onClick={() => setFormMode({ source: r.slug, selectable: false })}>
                          Partir de este
                        </Button>{' '}
                        {/* Lanzar desde la fila evita elegir el manifiesto dos
                            veces: una en el desplegable y otra con la vista. */}
                        <Button
                          variant="primary"
                          disabled={busy || blocked}
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
            {visibles.length === 0 && (
              <EmptyState hint="Probá con otro texto.">
                Ningún manifiesto coincide con la búsqueda
              </EmptyState>
            )}
          </Card>
        </>
      )}
    </>
  )
}
