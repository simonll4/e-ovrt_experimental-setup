import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { getPromptSetDetail } from '../api'
import { qk } from '../api/keys'
import { usePromptSetDetail, usePromptSetList } from '../api/queries/promptSets'
import type { PromptSetDetail, PromptSetDiff } from '../types'
import { promptStatusTone } from '../promptview'
import PromptSetEditor from '../components/PromptSetEditor'
import {
  Badge, Button, Card, DiscardPrompt, EmptyState, ErrorBanner, IconChevron, LoadingState,
  PageHeader, StaleNotice, enfocarCuandoAparezca,
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

/** Ciclo de vida como secuencia textual: tres etapas numeradas, con «hecho»,
 *  «actual» o «pendiente» en texto. El separador vive dentro de su etapa: al
 *  envolver no quedan flechas sueltas. */
function CicloDeVida({ status }: { status: string }) {
  const actual = CICLO.indexOf(status as (typeof CICLO)[number])
  return (
    <ol className="eo-flow" aria-label="Ciclo de vida del conjunto">
      {CICLO.map((paso, i) => {
        const estado = i === actual ? 'on' : i < actual ? 'done' : null
        return (
          <li key={paso} className={estado ? `eo-flow__item eo-flow__item--${estado}` : 'eo-flow__item'}>
            {i > 0 && <span className="eo-flow__sep" aria-hidden="true"><IconChevron /></span>}
            <span className="eo-flow__box">
              <span className="eo-flow__n">{i + 1}</span>
              <span
                className={'eo-flow__step' + (estado ? ` eo-flow__step--${estado}` : '')}
                aria-current={i === actual ? 'step' : undefined}
              >
                {STATUS_LABEL[paso]}
              </span>
              <span className="eo-flow__state">
                {estado === 'done' ? 'hecho' : estado === 'on' ? 'actual' : 'pendiente'}
              </span>
            </span>
          </li>
        )
      })}
    </ol>
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

/** Lo que se pidió mientras el editor tenía cambios sin guardar. */
type Pendiente = { tipo: 'elegir'; id: string } | { tipo: 'nuevo' }

export default function PromptSetsPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [editing, setEditing] = useState<PromptSetDetail | null>(null)
  const [creating, setCreating] = useState(false)
  const [editorDirty, setEditorDirty] = useState(false)
  const [pendiente, setPendiente] = useState<Pendiente | null>(null)
  const [abriendo, setAbriendo] = useState<{ id: string; error?: string } | null>(null)
  const qc = useQueryClient()

  const consulta = usePromptSetList()
  const sets = consulta.data ?? []
  const cargandoLista = consulta.isPending && !consulta.data
  const errorLista = consulta.error && !consulta.data ? String(consulta.error) : null

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
  // de guardar), así que el detalle se pide puntualmente al abrirlo. La espera y
  // el fallo se muestran: antes un fallo acá era una promesa rechazada muda.
  const abrirEditor = async (id: string) => {
    if (abriendo) return
    setAbriendo({ id })
    try {
      setEditing(await getPromptSetDetail(id))
      setAbriendo(null)
    } catch (e) {
      setAbriendo({ id, error: String(e) })
    }
  }

  const cerrarEditor = () => {
    setEditing(null)
    setCreating(false)
    setEditorDirty(false)
  }

  // Cerrar desde el editor (Cerrar, Guardar, Eliminar): el foco vuelve al
  // detalle, que reaparece en la misma columna.
  const cerrarYVolver = () => {
    cerrarEditor()
    enfocarCuandoAparezca('#eo-conjunto-detalle .eo-card__title')
  }

  const aplicar = (p: Pendiente) => {
    setPendiente(null)
    cerrarEditor()
    if (p.tipo === 'elegir') setSelectedId(p.id)
    else setCreating(true)
  }

  /** Elegir otro conjunto o empezar uno nuevo con el editor abierto: si hay
   *  cambios sin guardar, se pregunta antes. */
  const pedir = (p: Pendiente) => {
    const editorAbierto = creating || editing
    if (editorAbierto && editorDirty) setPendiente(p)
    else if (editorAbierto) aplicar(p)
    else if (p.tipo === 'elegir') setSelectedId(p.id)
    else setCreating(true)
  }

  // El editor ocupa la columna derecha en lugar de tapar la pantalla: así se
  // puede saltar a otro conjunto sin volver atrás primero.
  const editor = creating ? (
    <PromptSetEditor
      key="new"
      initial={EMPTY_NEW_SET}
      isNew
      onDirtyChange={setEditorDirty}
      onChanged={async () => { cerrarYVolver(); await refresh() }}
      onClose={cerrarYVolver}
    />
  ) : editing ? (
    <PromptSetEditor
      key={editing.id}
      initial={editing}
      onDirtyChange={setEditorDirty}
      onChanged={async () => { cerrarYVolver(); await refresh() }}
      onClose={cerrarYVolver}
    />
  ) : null

  const panelDetalle = () => {
    if (detalle.isPending && selectedId) {
      return (
        <Card title={<span className="eo-mono">{selectedId}</span>}>
          <LoadingState lines={3}>Leyendo el conjunto {selectedId}…</LoadingState>
        </Card>
      )
    }
    if (detalle.error && !seleccionado) {
      return (
        <Card title={<span className="eo-mono">{selectedId}</span>}>
          <ErrorBanner
            detail={String(detalle.error)}
            onRetry={() => void detalle.refetch()}
            retrying={detalle.isFetching}
          >
            No se pudo leer el conjunto {selectedId}.
          </ErrorBanner>
        </Card>
      )
    }
    if (!seleccionado) {
      return (
        <Card>
          <EmptyState>Elegí un conjunto para ver sus clases y sus frases.</EmptyState>
        </Card>
      )
    }
    return (
      <>
        <Card id="eo-conjunto-detalle" title={<span className="eo-mono">{seleccionado.id}</span>}>
          {detalle.error && (
            <StaleNotice what="el conjunto" onRetry={() => void detalle.refetch()} retrying={detalle.isFetching} />
          )}
          <CicloDeVida status={estado} />
          <p className="eo-cap">{EXPLICACION[estado] ?? ''}</p>
          {abriendo?.error && abriendo.id === seleccionado.id && (
            <ErrorBanner
              detail={abriendo.error}
              onRetry={() => { setAbriendo(null); void abrirEditor(seleccionado.id) }}
            >
              No se pudo abrir el editor de {seleccionado.id}.
            </ErrorBanner>
          )}
          <div className="eo-actions">
            {estado === 'exploratory' && (
              <Button
                variant="primary"
                disabled={abriendo != null && !abriendo.error}
                onClick={() => void abrirEditor(seleccionado.id)}
              >
                {abriendo && !abriendo.error ? 'Abriendo…' : 'Editar clases y frases'}
              </Button>
            )}
            {estado !== 'exploratory' && (
              <Button
                disabled={abriendo != null && !abriendo.error}
                onClick={() => void abrirEditor(seleccionado.id)}
              >
                {abriendo && !abriendo.error ? 'Abriendo…' : 'Ver clases y frases'}
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
              <div>
                <dt>Deriva de</dt>
                <dd className="eo-mono">{seleccionado.derives_from}</dd>
              </div>
              <div>
                <dt>Qué cambió</dt>
                <dd>
                  {seleccionado.diff ? (
                    <Cambios diff={seleccionado.diff} />
                  ) : (
                    seleccionado.changes ?? 'sin dato'
                  )}
                </dd>
              </div>
            </dl>
          </Card>
        )}
      </>
    )
  }

  return (
    <>
      <PageHeader
        title="Conjuntos de prompts"
        meta="Definen qué clases se buscan y con qué frases se le pide al modelo"
        actions={
          <Button variant="primary" onClick={() => pedir({ tipo: 'nuevo' })}>
            Nuevo conjunto
          </Button>
        }
      />

      {pendiente && (
        <DiscardPrompt
          what="el editor"
          onKeep={() => setPendiente(null)}
          onDiscard={() => aplicar(pendiente)}
        />
      )}

      {/* `!editor` en la condición: sin ningún conjunto, el estado vacío tapaba
          al editor y «Nuevo conjunto» no llevaba a ninguna parte. */}
      {cargandoLista && !editor ? (
        <Card>
          <LoadingState lines={4}>Cargando los conjuntos de prompts…</LoadingState>
        </Card>
      ) : errorLista && !editor ? (
        <ErrorBanner detail={errorLista} onRetry={() => void consulta.refetch()} retrying={consulta.isFetching}>
          No se pudieron cargar los conjuntos de prompts.
        </ErrorBanner>
      ) : sets.length === 0 && !editor ? (
        <Card>
          <EmptyState
            hint="Los conjuntos viven en prompts/ del repositorio."
            action={<Button onClick={() => pedir({ tipo: 'nuevo' })}>Crear el primero</Button>}
          >
            Sin conjuntos de prompts todavía
          </EmptyState>
        </Card>
      ) : (
        <div className="eo-pane">
          <Card title="Conjuntos" meta={consulta.data ? String(sets.length) : undefined} flush>
            {consulta.error && consulta.data && (
              <StaleNotice what="la lista" onRetry={() => void consulta.refetch()} retrying={consulta.isFetching} />
            )}
            {sets.map((s) => (
              <button
                key={s.id}
                type="button"
                className="eo-lrow"
                aria-current={s.id === selectedId}
                onClick={() => pedir({ tipo: 'elegir', id: s.id })}
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
            {editor ?? panelDetalle()}
          </div>
        </div>
      )}
    </>
  )
}
