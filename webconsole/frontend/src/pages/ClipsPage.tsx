import { useMemo, useState } from 'react'

import { clipMediaUrl } from '../api'
import { useClips, useMasters } from '../api/queries/clips'
import TrimDialog from '../components/TrimDialog'
import { Badge, Card, EmptyState, ErrorBanner, PageHeader, SearchInput } from '../components/ui'
import type { ClipEntry, MasterEntry } from '../types'

/** Panel derecho: o se recorta un master, o se reproduce un clip, nunca las dos.
 * El estado único evita que queden dos reproductores cargando video a la vez. */
type Panel = { kind: 'trim'; master: MasterEntry } | { kind: 'clip'; clipId: string } | null

const segundos = (ms: number | null | undefined) =>
  ms != null ? `${(ms / 1000).toFixed(1)} s` : '—'

export default function ClipsPage() {
  const [panel, setPanel] = useState<Panel>(null)
  const [filtro, setFiltro] = useState('')

  const consultaMasters = useMasters()
  const consultaClips = useClips()
  const masters: MasterEntry[] = consultaMasters.data ?? []
  const clips: ClipEntry[] = consultaClips.data ?? []
  const fallo = consultaMasters.error ?? consultaClips.error
  const error = fallo ? (fallo instanceof Error ? fallo.message : String(fallo)) : null

  // El filtro es una sola caja para las dos listas: el operador busca "4.1" o "p7"
  // sin tener que acordarse de si eso es un master o un clip.
  const q = filtro.trim().toLowerCase()
  const mastersVisibles = useMemo(
    () =>
      q === ''
        ? masters
        : masters.filter(
            (m) =>
              m.name.toLowerCase().includes(q) ||
              (m.scenario ?? '').toLowerCase().includes(q) ||
              m.clips.some((c) => c.toLowerCase().includes(q)),
          ),
    [masters, q],
  )
  const clipsVisibles = useMemo(
    () => (q === '' ? clips : clips.filter((c) => c.clip_id.toLowerCase().includes(q))),
    [clips, q],
  )

  const clipActivo =
    panel?.kind === 'clip' ? clips.find((c) => c.clip_id === panel.clipId) : undefined

  return (
    <div className="eo-clips">
      <PageHeader
        title="Clips"
        meta={`${masters.length} materiales · ${clips.length} clips recortados`}
      />
      {error && <ErrorBanner>{error}</ErrorBanner>}

      {/* El buscador va en su propia barra, no entre las acciones del
          encabezado: filtra el contenido de abajo, no la pantalla. */}
      <div className="eo-toolbar">
        <SearchInput
          value={filtro}
          onChange={setFiltro}
          placeholder="Buscar en materiales y clips"
          ariaLabel="Buscar en materiales y clips"
        />
      </div>

      <div className="eo-clips__grid">
        <div className="eo-clips__rail">
          <Card title={`Materiales (${mastersVisibles.length}/${masters.length})`}>
            {mastersVisibles.length === 0 ? (
              <EmptyState>{masters.length === 0 ? 'No hay materiales grabados.' : 'Nada coincide.'}</EmptyState>
            ) : (
              <ul className="eo-rows eo-rows--scroll">
                {mastersVisibles.map((m) => {
                  const activo = panel?.kind === 'trim' && panel.master.name === m.name
                  return (
                    <li
                      key={m.name}
                      className={activo ? 'eo-row eo-row--active' : 'eo-row'}
                    >
                      <div className="eo-row__main">
                        <span className="eo-row__name">{m.name}</span>
                        <small className="eo-note">
                          {m.scenario ?? 'sin escenario'} · {segundos(m.duration_ms)} ·{' '}
                          {!m.readable ? (
                            <Badge tone="error">Ilegible</Badge>
                          ) : m.clips.length > 0 ? (
                            m.clips.join(', ')
                          ) : (
                            'sin recortar'
                          )}
                        </small>
                      </div>
                      <button
                        type="button"
                        disabled={!m.readable}
                        onClick={() => setPanel({ kind: 'trim', master: m })}
                      >
                        Recortar
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </Card>

          <Card title={`Clips generados (${clipsVisibles.length}/${clips.length})`}>
            {clipsVisibles.length === 0 ? (
              <EmptyState>{clips.length === 0 ? 'Todavía no hay clips.' : 'Nada coincide.'}</EmptyState>
            ) : (
              <ul className="eo-rows eo-rows--scroll">
                {clipsVisibles.map((c) => {
                  const activo = panel?.kind === 'clip' && panel.clipId === c.clip_id
                  return (
                    <li key={c.clip_id} className={activo ? 'eo-row eo-row--active' : 'eo-row'}>
                      <button
                        type="button"
                        className="eo-row__pick"
                        onClick={() => setPanel({ kind: 'clip', clipId: c.clip_id })}
                      >
                        <span className="eo-row__name">{c.clip_id}</span>
                        <small className="eo-note">
                          {segundos(c.duration_ms)} · {c.resolution ?? '—'}
                        </small>
                        {c.warnings.map((w) => (
                          <small key={w} className="eo-note eo-note--warn">
                            ⚠ {w}
                          </small>
                        ))}
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </Card>
        </div>

        <div className="eo-clips__work">
          {panel?.kind === 'trim' && (
            <TrimDialog
              key={panel.master.name}
              master={panel.master}
              onClose={() => setPanel(null)}
              // `TrimDialog` todavía llama a `generateClip` directo. Cuando pase
              // a usar `useGenerateClip`, la invalidación es automática y este
              // callback sobra.
              onGenerated={() => {
                void consultaMasters.refetch()
                void consultaClips.refetch()
              }}
            />
          )}
          {panel?.kind === 'clip' && (
            <Card title={`Reproducir ${panel.clipId}`}>
              <video controls className="eo-video" src={clipMediaUrl(panel.clipId)} />
              <p className="eo-note">
                {segundos(clipActivo?.duration_ms)} · {clipActivo?.resolution ?? '—'} ·{' '}
                {clipActivo?.fps ?? '—'} fps · master {clipActivo?.master ?? '—'}
              </p>
              <div className="eo-actions">
                <button type="button" onClick={() => setPanel(null)}>
                  Cerrar
                </button>
              </div>
            </Card>
          )}
          {panel == null && (
            <Card title="Elegí un material o un clip">
              <EmptyState>
                Los materiales son las grabaciones completas. Los clips son recortes con nombre, que después podés usar como fuente de una corrida.
              </EmptyState>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
