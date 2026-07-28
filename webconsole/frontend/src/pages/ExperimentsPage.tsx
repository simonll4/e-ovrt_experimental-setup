import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ApiError, getCurrentExperiment, getExperimentManifests, runExperiment } from '../api'
import type { ExperimentManifestSummary, ExperimentRunState } from '../types'
import { experimentStatusLabel, experimentStatusTone } from '../experimentview'
import { usePreflight } from '../usePreflight'
import PlatformStatus from '../components/PlatformStatus'
import { DeriveExperimentForm } from '../components/DeriveExperimentForm'
import {
  Badge,
  Banner,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Field,
  MonoCell,
  PageHeader,
  RowNameCell,
  Select,
  Table,
} from '../components/ui'
import { applyPlaneGlossary } from '../labels'

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
  const [rows, setRows] = useState<ExperimentManifestSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [current, setCurrent] = useState<ExperimentRunState | null>(null)
  const [slug, setSlug] = useState('')
  const [busy, setBusy] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)
  const [formMode, setFormMode] = useState<FormMode>(null)

  // Cierra el formulario. /experiments/new es una ruta dedicada: al salir del
  // formulario ahí, se navega de vuelta a /experiments — si no, la ruta sigue
  // siendo /experiments/new con formMode en null y el efecto de abajo lo
  // reabriría solo, con el primer manifiesto de nuevo (perdiendo lo elegido).
  const closeForm = () => {
    setFormMode(null)
    if (isNewRoute) navigate('/experiments')
  }

  const reloadManifests = () =>
    getExperimentManifests()
      .then((r) => {
        setRows(r)
        setError(null)
        return r
      })
      .catch((e) => {
        setError(String(e))
        return null
      })

  useEffect(() => {
    let alive = true
    reloadManifests().then((r) => {
      if (alive && r && r.length > 0 && !slug) setSlug(r[0].slug)
    })
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // /experiments/new abre el formulario apenas hay manifiestos para elegir
  // "basado en" (precargado con el primero, como pide el spec).
  useEffect(() => {
    if (isNewRoute && rows && rows.length > 0 && !formMode) {
      setFormMode({ source: rows[0].slug, selectable: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isNewRoute, rows])

  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout>
    const tick = () =>
      getCurrentExperiment()
        .then((c) => {
          if (!alive) return
          setCurrent(c)
          if (c?.status === 'running') timer = setTimeout(tick, 4000)
        })
        .catch(() => {
          /* banner de estado activo: silencioso si falla el poll */
        })
    tick()
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [])

  const trigger = async () => {
    if (!slug) return
    setBusy(true)
    setRunError(null)
    try {
      const { experiment_id } = await runExperiment({ slug })
      navigate(`/experiments/${experiment_id}`)
    } catch (e) {
      setRunError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  // Gate de lanzamiento: sin preflight verde no se lanza (el BFF igualmente lo
  // rechaza con 503; acá se corta antes y con el motivo a la vista).
  const experimentRunning = current?.status === 'running'
  const blocked = !preflight?.ready || experimentRunning
  const blockedReason = experimentRunning
    ? 'hay un experimento en curso'
    : preflight === null
      ? 'verificando servicios…'
      : preflight.blockers[0]

  if (error) return <ErrorBanner>Error listando experimentos: {error}</ErrorBanner>
  if (!rows) return <p className="eo-empty">Cargando…</p>

  const options = rows.map((r) => ({ value: r.slug, label: r.slug }))

  return (
    <>
      {/* Sin acción propia en el encabezado: "+ Nuevo experimento" ya vive en la
          barra lateral, y repetirlo acá chocaba con el título de la tarjeta del
          formulario, que también dice "Nuevo experimento". */}
      <PageHeader title="Experimentos" meta={`${rows.length} manifiestos`} />

      {current && (
        <Banner tone={current.status === 'running' ? 'live' : 'warn'}>
          Experimento activo{' '}
          <Link to={`/experiments/${current.experiment_id}`}>
            <span className="eo-mono">{current.experiment_id}</span>
          </Link>{' '}
          — <Badge tone={experimentStatusTone(current)}>{experimentStatusLabel(current)}</Badge>
        </Banner>
      )}

      <Card title="Lanzar un experimento">
        <div className="eo-launchbar">
          <PlatformStatus status={preflight} />
          <Select value={slug} options={options} onChange={setSlug} placeholder="Elegí un manifiesto" />
          <Button variant="primary" onClick={trigger} disabled={busy || !slug || blocked}>
            {busy ? 'Lanzando…' : 'Lanzar experimento'}
          </Button>
        </div>
        {blocked && !busy && (
          <p className="eo-note eo-note--warn">
            No se puede lanzar: {applyPlaneGlossary(String(blockedReason ?? 'servicios no listos'))}.
          </p>
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
        <EmptyState hint="Los manifiestos viven en experiments/ del repositorio.">
          Sin manifiestos todavía
        </EmptyState>
      ) : (
        <Card title="Manifiestos" meta={`${rows.length}`} flush>
          <Table>
            <thead>
              <tr>
                <th>Manifiesto</th>
                <th>Grupo</th>
                <th>Última ejecución</th>
                <th aria-label="Acciones" />
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.slug}>
                  <RowNameCell title={<span className="eo-mono">{r.slug}</span>} subtitle={r.description ?? undefined} />
                  <td>{r.group ?? '—'}</td>
                  <MonoCell>
                    {r.experiment_id ? (
                      <Link to={`/experiments/${r.experiment_id}`}>{r.experiment_id}</Link>
                    ) : (
                      '—'
                    )}
                  </MonoCell>
                  <td className="eo-cell--actions">
                    <Button onClick={() => setFormMode({ source: r.slug, selectable: false })}>
                      Derivar
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>
      )}
    </>
  )
}
