import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { getPromptSetDetail } from '../api'
import { qk } from '../api/keys'
import { usePromptSetDetail, usePromptSetList } from '../api/queries/promptSets'
import type { PromptSetDetail, PromptSetDiff } from '../types'
import { promptStatusTone } from '../promptview'
import PromptSetEditor from '../components/PromptSetEditor'
import {
  Badge, Button, Card, EmptyState, ErrorBanner, PageHeader,
} from '../components/ui'

// Los estados son códigos del backend; acá se les pone nombre legible. Un estado
// desconocido cae al código crudo en vez de quedar en blanco.
const STATUS_LABEL: Record<string, string> = {
  exploratory: 'En exploración',
  frozen_pending_review: 'Pendiente de revisión',
  frozen: 'Congelado',
}

/** El ciclo de vida, en orden. La posición en esta lista es lo que decide si un
 *  paso ya se recorrió, es el actual, o todavía no llegó. */
const CICLO = ['exploratory', 'frozen_pending_review', 'frozen'] as const

/** Qué se puede hacer con el conjunto según dónde esté del ciclo. */
const EXPLICACION: Record<string, string> = {
  exploratory:
    'Podés editar las clases y las frases. Al congelarlo pasa a revisión y deja de ser editable.',
  frozen_pending_review:
    'Ya no se puede editar. Revisá las frases y confirmá el congelado; si algo está mal, volvé a exploración.',
  frozen:
    'Congelado y con huella verificable. Para cambiar algo hay que derivar un conjunto nuevo a partir de este.',
}

const EMPTY_NEW_SET: PromptSetDetail = { id: '', status: 'exploratory', classes: [] }

function CicloDeVida({ status }: { status: string }) {
  const actual = CICLO.indexOf(status as (typeof CICLO)[number])
  return (
    <div className="eo-flow">
      {CICLO.map((paso, i) => (
        <span key={paso}>
          {i > 0 && <span className="eo-flow__arrow" aria-hidden="true">→</span>}{' '}
          <span
            className={
              'eo-flow__step' +
              (i === actual ? ' eo-flow__step--on' : i < actual ? ' eo-flow__step--done' : '')
            }
            aria-current={i === actual ? 'step' : undefined}
          >
            {i < actual && <span aria-hidden="true">✓</span>}
            {STATUS_LABEL[paso]}
          </span>{' '}
        </span>
      ))}
    </div>
  )
}

/** Qué cambió respecto del conjunto del que deriva. */
function Cambios({ diff }: { diff: PromptSetDiff }) {
  const partes: string[] = []
  if (diff.classes_added.length) partes.push(`${diff.classes_added.length} clases nuevas`)
  if (diff.classes_removed.length) partes.push(`${diff.classes_removed.length} clases quitadas`)
  const frasesMas = Object.values(diff.phrases_added).reduce((n, f) => n + f.length, 0)
  const frasesMenos = Object.values(diff.phrases_removed).reduce((n, f) => n + f.length, 0)
  if (frasesMas) partes.push(`${frasesMas} frases nuevas`)
  if (frasesMenos) partes.push(`${frasesMenos} frases quitadas`)
  return <>{partes.length ? partes.join(', ') : 'Sin diferencias'}</>
}

export default function PromptSetsPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [editing, setEditing] = useState<PromptSetDetail | null>(null)
  const [creating, setCreating] = useState(false)
  const qc = useQueryClient()

  const consulta = usePromptSetList()
  const sets = consulta.data ?? []
  const error = consulta.error ? 'No se pudieron cargar los conjuntos de prompts' : null

  // Se elige el primero apenas hay listado: el panel de detalle vacío no aporta
  // nada y obligaba a un click extra para ver cualquier cosa.
  useEffect(() => {
    if (!selectedId && sets.length > 0) setSelectedId(sets[0].id)
  }, [sets, selectedId])

  const detalle = usePromptSetDetail(selectedId)
  const seleccionado = detalle.data ?? null
  const estado = seleccionado?.status ?? 'exploratory'

  const refresh = async () => {
    await qc.invalidateQueries({ queryKey: qk.promptSets.all })
  }

  // El editor trabaja sobre una copia local (es un borrador que se edita antes
  // de guardar), así que el detalle se pide puntualmente al abrirlo.
  const abrirEditor = async (id: string) => {
    setEditing(await getPromptSetDetail(id))
  }

  // El editor ocupa la columna derecha en lugar de tapar la pantalla: así se
  // puede saltar a otro conjunto sin volver atrás primero.
  const editor = creating ? (
    <PromptSetEditor
      key="new"
      initial={EMPTY_NEW_SET}
      isNew
      onChanged={async () => { await refresh(); setCreating(false) }}
      onClose={() => setCreating(false)}
    />
  ) : editing ? (
    <PromptSetEditor
      key={editing.id}
      initial={editing}
      onChanged={async () => { await refresh(); setEditing(null) }}
      onClose={() => setEditing(null)}
    />
  ) : null

  return (
    <>
      <PageHeader
        title="Conjuntos de prompts"
        meta="Definen qué clases se buscan y con qué frases se le pide al modelo"
        actions={
          <Button variant="primary" onClick={() => setCreating(true)}>
            Nuevo conjunto
          </Button>
        }
      />
      {error && <ErrorBanner>{error}</ErrorBanner>}

      {/* `!editor` en la condición: sin ningún conjunto, el estado vacío tapaba
          al editor y «Nuevo conjunto» no llevaba a ninguna parte. */}
      {sets.length === 0 && !editor ? (
        <Card>
          <EmptyState hint="Los conjuntos viven en prompts/ del repositorio.">
            Sin conjuntos de prompts todavía
          </EmptyState>
        </Card>
      ) : (
        <div className="eo-pane">
          <Card title="Conjuntos" meta={String(sets.length)} flush>
            {sets.map((s) => (
              <button
                key={s.id}
                type="button"
                className="eo-lrow"
                aria-current={s.id === selectedId}
                onClick={() => setSelectedId(s.id)}
              >
                <span className="eo-lrow__main">
                  <b className="eo-mono">{s.id}</b>
                  <span>
                    {s.track ? `${s.track} · ` : ''}
                    {s.n_classes} clases · {s.n_phrases} frases
                  </span>
                </span>
                <Badge tone={promptStatusTone(s.status)}>
                  {STATUS_LABEL[s.status] ?? s.status}
                </Badge>
              </button>
            ))}
          </Card>

          <div className="eo-pane__col">
            {editor ? (
              editor
            ) : !seleccionado ? (
              <Card>
                <p className="eo-empty">Elegí un conjunto para ver sus clases y sus frases.</p>
              </Card>
            ) : (
              <>
                <Card
                  title={<span className="eo-mono">{seleccionado.id}</span>}
                  meta={
                    <Badge tone={promptStatusTone(estado)}>
                      {STATUS_LABEL[estado] ?? estado}
                    </Badge>
                  }
                >
                  <CicloDeVida status={estado} />
                  <p className="eo-cap">{EXPLICACION[estado] ?? ''}</p>
                  <div className="eo-actions">
                    {estado === 'exploratory' && (
                      <Button variant="primary" onClick={() => void abrirEditor(seleccionado.id)}>
                        Editar clases y frases
                      </Button>
                    )}
                    {estado !== 'exploratory' && (
                      <Button onClick={() => void abrirEditor(seleccionado.id)}>
                        Ver clases y frases
                      </Button>
                    )}
                  </div>
                </Card>

                <Card
                  title="Clases y frases"
                  meta={`${seleccionado.classes.length} clases`}
                >
                  {seleccionado.classes.map((c) => (
                    <div key={c.id} className="eo-phrases">
                      <b>{c.id}</b>
                      <span>
                        {Object.values(c.phrasings)
                          .flat()
                          .map((f) => `«${f}»`)
                          .join(' · ') || 'sin frases'}
                      </span>
                    </div>
                  ))}
                  <p className="eo-cap">
                    {estado === 'exploratory'
                      ? 'Editable: usá «Editar clases y frases» para cambiarlo.'
                      : 'Solo lectura: el conjunto ya no está en exploración.'}
                  </p>
                </Card>

                {seleccionado.derives_from && (
                  <Card title="Origen">
                    <dl className="eo-deflist">
                      <dt>Deriva de</dt>
                      <dd className="eo-mono">{seleccionado.derives_from}</dd>
                      <dt>Qué cambió</dt>
                      <dd>
                        {seleccionado.diff ? (
                          <Cambios diff={seleccionado.diff} />
                        ) : (
                          seleccionado.changes ?? 'sin dato'
                        )}
                      </dd>
                    </dl>
                  </Card>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </>
  )
}
