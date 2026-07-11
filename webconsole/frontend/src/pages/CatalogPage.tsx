import { useEffect, useState } from 'react'
import { getDatasets, getIngestPlugins, getPromptSets } from '../api'
import type { DatasetEntry, IngestPlugin, PromptSet } from '../types'
import { useTarget } from '../useTarget'

export default function CatalogPage() {
  const target = useTarget()
  const [plugins, setPlugins] = useState<IngestPlugin[]>([])
  const [datasets, setDatasets] = useState<DatasetEntry[]>([])
  const [sets, setSets] = useState<PromptSet[]>([])
  // Re-fetchea los catálogos cuando cambia el modelo activo del target (p.ej. tras un
  // restart del servicio con otro EOVRT_MODEL_REF), así no quedan stale.
  const modelRef = target?.model?.ref
  useEffect(() => {
    let alive = true
    getIngestPlugins().then((v) => alive && setPlugins(v)).catch(() => alive && setPlugins([]))
    getDatasets().then((v) => alive && setDatasets(v)).catch(() => alive && setDatasets([]))
    getPromptSets().then((v) => alive && setSets(v)).catch(() => alive && setSets([]))
    return () => {
      alive = false
    }
  }, [modelRef])
  return (
    <div style={{ display: 'grid', gap: 24 }}>
      <section>
        <h2>Modelo del target (read-only)</h2>
        {target?.model ? (
          <ul>
            <li><b>{target.model.ref}</b> — adapter {target.model.adapter}, device {target.model.device}</li>
            <li>
              thresholds:{' '}
              {Object.entries(target.model.thresholds)
                .filter(([, v]) => v != null)
                .map(([k, v]) => `${k}=${v}`)
                .join(', ') || '—'}
              {' '}<em>(fijos por instancia; cambiar de modelo = otra instancia)</em>
            </li>
          </ul>
        ) : (
          <p>Servicio no listo.</p>
        )}
      </section>
      <section>
        <h2>Plugins de ingesta</h2>
        <ul>
          {plugins.map((p) => (
            <li key={p.id}>
              <b>{p.id}</b> ({p.kind}) — {p.description}{' '}
              {!p.available && <em>[no disponible]</em>}
              {p.available && !p.enabled && <em>[no soportado]</em>}
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h2>Datasets</h2>
        <ul>
          {datasets.map((d) => (
            <li key={d.id}>
              <b>{d.id}</b> — {d.description} {!d.available && <em>[no montado]</em>}
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h2>Prompt sets (in-repo)</h2>
        <ul>
          {sets.map((s) => (
            <li key={s.id}>
              <b>{s.id}</b> {s.frozen && <em>[congelado]</em>} —{' '}
              {s.classes.map((c) => c.id).join(', ')}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
