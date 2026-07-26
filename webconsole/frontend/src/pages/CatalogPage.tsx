import { useEffect, useState } from 'react'
import { getDatasets, getIngestPlugins, getPromptSets } from '../api'
import { Card, EmptyState, Table } from '../components/ui'
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
    <div style={{ display: 'grid', gap: 'var(--space-1)' }}>
      <Card title="Modelo de la instancia activa (solo lectura)">
        {target?.model ? (
          <Table>
            <thead>
              <tr><th>ref</th><th>adaptador</th><th>dispositivo</th><th>umbrales</th></tr>
            </thead>
            <tbody>
              <tr>
                <td>{target.model.ref}</td>
                <td>{target.model.adapter}</td>
                <td>{target.model.device}</td>
                <td>
                  {Object.entries(target.model.thresholds)
                    .filter(([, v]) => v != null)
                    .map(([k, v]) => `${k}=${v}`)
                    .join(', ') || '—'}
                </td>
              </tr>
            </tbody>
          </Table>
        ) : (
          <EmptyState>Servicio no operativo.</EmptyState>
        )}
        {target?.model && <small>(fijos por instancia; cambiar de modelo = otra instancia)</small>}
      </Card>
      <Card title="Plugins de ingesta">
        {plugins.length === 0 ? (
          <EmptyState>Sin plugins de ingesta.</EmptyState>
        ) : (
          <Table>
            <thead>
              <tr><th>id</th><th>tipo</th><th>descripción</th><th>estado</th></tr>
            </thead>
            <tbody>
              {plugins.map((p) => (
                <tr key={p.id}>
                  <td>{p.id}</td>
                  <td>{p.kind}</td>
                  <td>{p.description}</td>
                  <td>
                    {!p.available && <em>no disponible</em>}
                    {p.available && !p.enabled && <em>no soportado</em>}
                    {p.available && p.enabled && '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
      <Card title="Datasets">
        {datasets.length === 0 ? (
          <EmptyState>Sin datasets disponibles.</EmptyState>
        ) : (
          <Table>
            <thead>
              <tr><th>id</th><th>descripción</th><th>estado</th></tr>
            </thead>
            <tbody>
              {datasets.map((d) => (
                <tr key={d.id}>
                  <td>{d.id}</td>
                  <td>{d.description}</td>
                  <td>{!d.available ? <em>no montado</em> : '—'}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
      <Card title="Conjuntos de prompts (del repositorio)">
        {sets.length === 0 ? (
          <EmptyState>Sin conjuntos de prompts.</EmptyState>
        ) : (
          <Table>
            <thead>
              <tr><th>id</th><th>estado</th><th>clases</th></tr>
            </thead>
            <tbody>
              {sets.map((s) => (
                <tr key={s.id}>
                  <td>{s.id}</td>
                  <td>{s.frozen ? <em>congelado</em> : '—'}</td>
                  <td>{s.classes.map((c) => c.id).join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
    </div>
  )
}
