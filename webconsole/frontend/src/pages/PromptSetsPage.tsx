import { useCallback, useEffect, useState } from 'react'
import {
  getPromptSetDetail, listPromptSets,
} from '../api'
import type { PromptSetDetail, PromptSetSummary } from '../types'
import { promptStatusTone } from '../promptview'
import PromptSetEditor from '../components/PromptSetEditor'
import { Badge, EmptyState, ErrorBanner } from '../components/ui'

const STATUS_LABEL: Record<string, string> = {
  exploratory: 'exploratory',
  frozen_pending_review: 'frozen_pending_review',
  frozen: 'frozen',
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
    <div>
      <h2>Prompt sets</h2>
      {error && <ErrorBanner>{error}</ErrorBanner>}
      <button type="button" onClick={() => setCreating(true)}>Nuevo set</button>
      <table className="eo-table">
        <thead>
          <tr><th>id</th><th>estado</th><th>track</th><th>clases</th><th>frases</th><th>deriva de</th></tr>
        </thead>
        <tbody>
          {sets.map((s) => (
            <tr key={s.id} onClick={() => void open(s.id)} style={{ cursor: 'pointer' }}>
              <td>
                <button type="button" className="eo-linklike" onClick={() => void open(s.id)}>
                  {s.id}
                </button>
              </td>
              <td><Badge tone={promptStatusTone(s.status)}>{STATUS_LABEL[s.status] ?? s.status}</Badge></td>
              <td>{s.track ?? ''}</td>
              <td>{s.n_classes}</td>
              <td>{s.n_phrases}</td>
              <td>{s.derives_from ?? ''}</td>
            </tr>
          ))}
          {sets.length === 0 && (
            <tr><td colSpan={6}><EmptyState>Sin prompt sets todavía.</EmptyState></td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
