import { useCallback, useEffect, useState } from 'react'
import {
  getPromptSetDetail, listPromptSets,
} from '../api'
import type { PromptSetDetail, PromptSetSummary } from '../types'
import { promptStatusTone } from '../promptview'
import PromptSetEditor from '../components/PromptSetEditor'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  MonoCell,
  NumCell,
  PageHeader,
  Table,
} from '../components/ui'

// Los estados son códigos del backend; acá se les pone nombre legible. Un estado
// desconocido cae al código crudo en vez de quedar en blanco.
const STATUS_LABEL: Record<string, string> = {
  exploratory: 'Exploratorio',
  frozen_pending_review: 'Congelado, a revisar',
  frozen: 'Congelado',
}

const EMPTY_NEW_SET: PromptSetDetail = { id: '', status: 'exploratory', classes: [] }

export default function PromptSetsPage() {
  const [sets, setSets] = useState<PromptSetSummary[]>([])
  const [selected, setSelected] = useState<PromptSetDetail | null>(null)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setSets(await listPromptSets())
    } catch {
      setError('No se pudieron cargar los prompt sets')
    }
  }, [])

  useEffect(() => { void refresh() }, [refresh])

  const open = async (id: string) => {
    setSelected(await getPromptSetDetail(id))
  }

  if (selected || creating) {
    return (
      <div>
        <button type="button" className="eo-linklike"
          onClick={() => { setSelected(null); setCreating(false) }}>
          ← Prompt sets
        </button>
        {error && <ErrorBanner>{error}</ErrorBanner>}
        {selected && (
          <PromptSetEditor
            key={selected.id}
            initial={selected}
            onChanged={async () => { await refresh(); setSelected(null) }}
            onClose={() => setSelected(null)}
          />
        )}
        {creating && (
          <PromptSetEditor
            key="new"
            initial={EMPTY_NEW_SET}
            isNew
            onChanged={async () => { await refresh(); setCreating(false) }}
            onClose={() => setCreating(false)}
          />
        )}
      </div>
    )
  }

  return (
    <>
      <PageHeader
        title="Conjuntos de prompts"
        meta={`${sets.length} conjuntos`}
        actions={
          <Button variant="primary" onClick={() => setCreating(true)}>
            Nuevo conjunto
          </Button>
        }
      />
      {error && <ErrorBanner>{error}</ErrorBanner>}
      <Card flush>
        <Table>
          <thead>
            <tr>
              <th>Conjunto</th>
              <th>Estado</th>
              <th>Track</th>
              <th className="eo-num">Clases</th>
              <th className="eo-num">Frases</th>
              <th>Deriva de</th>
            </tr>
          </thead>
          <tbody>
            {sets.map((s) => (
              <tr key={s.id} onClick={() => void open(s.id)} style={{ cursor: 'pointer' }}>
                <MonoCell>
                  <button type="button" className="eo-linklike" onClick={() => void open(s.id)}>
                    {s.id}
                  </button>
                </MonoCell>
                <td>
                  <Badge tone={promptStatusTone(s.status)}>
                    {STATUS_LABEL[s.status] ?? s.status}
                  </Badge>
                </td>
                <MonoCell>{s.track ?? '—'}</MonoCell>
                <NumCell>{s.n_classes}</NumCell>
                <NumCell>{s.n_phrases}</NumCell>
                <MonoCell>{s.derives_from ?? '—'}</MonoCell>
              </tr>
            ))}
          </tbody>
        </Table>
        {sets.length === 0 && (
          <EmptyState hint="Los conjuntos viven en prompts/ del repositorio.">
            Sin conjuntos de prompts todavía
          </EmptyState>
        )}
      </Card>
    </>
  )
}
