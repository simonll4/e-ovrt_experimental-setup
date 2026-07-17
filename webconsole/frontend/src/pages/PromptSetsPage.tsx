import { useCallback, useEffect, useState } from 'react'
import {
  getPromptSetDetail, listPromptSets,
} from '../api'
import type { PromptSetDetail, PromptSetSummary } from '../types'
import PromptSetEditor from '../components/PromptSetEditor'

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

  return (
    <div className="prompt-sets-page">
      <h2>Prompt sets</h2>
      {error && <p role="alert">{error}</p>}
      <button type="button" onClick={() => setCreating(true)}>Nuevo set</button>
      <table>
        <thead>
          <tr><th>id</th><th>estado</th><th>track</th><th>clases</th><th>frases</th><th>deriva de</th></tr>
        </thead>
        <tbody>
          {sets.map((s) => (
            <tr key={s.id} onClick={() => void open(s.id)} style={{ cursor: 'pointer' }}>
              <td>{s.id}</td>
              <td><span className={`badge badge-${s.status}`}>{STATUS_LABEL[s.status] ?? s.status}</span></td>
              <td>{s.track ?? ''}</td>
              <td>{s.n_classes}</td>
              <td>{s.n_phrases}</td>
              <td>{s.derives_from ?? ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
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
