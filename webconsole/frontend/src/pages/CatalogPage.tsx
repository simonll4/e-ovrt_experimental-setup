import { useEffect, useState } from 'react'
import { getDatasets, getIngestPlugins, getPromptSets } from '../api'
import { Badge, Card, EmptyState, MonoCell, PageHeader, Table } from '../components/ui'
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
    <>
      <PageHeader
        title="Catálogos"
        meta="Lo que la instancia activa ofrece hoy — solo lectura"
      />

      <Card title="Modelo de la instancia activa" meta="No se puede cambiar acá" flush>
        {target?.model ? (
          <>
            <Table>
              <thead>
                <tr>
                  <th>Modelo</th>
                  <th>Adaptador</th>
                  <th>Dispositivo</th>
                  <th>Umbrales</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <MonoCell>{target.model.ref}</MonoCell>
                  <MonoCell>{target.model.adapter}</MonoCell>
                  <MonoCell>{target.model.device}</MonoCell>
                  <MonoCell>
                    {Object.entries(target.model.thresholds)
                      .filter(([, v]) => v != null)
                      .map(([k, v]) => `${k}=${v}`)
                      .join(', ') || '—'}
                  </MonoCell>
                </tr>
              </tbody>
            </Table>
            <p className="eo-cap eo-cap--inset">
              Son fijos por instancia: cambiar de modelo significa activar otra instancia
              desde Plataforma.
            </p>
          </>
        ) : (
          <EmptyState hint="El motor de detección todavía no respondió.">
            Servicio no listo
          </EmptyState>
        )}
      </Card>

      <Card title="Fuentes de ingesta" meta={`${plugins.length}`} flush>
        {plugins.length === 0 ? (
          <EmptyState>Sin fuentes de ingesta</EmptyState>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Fuente</th>
                <th>Tipo</th>
                <th>Descripción</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {plugins.map((p) => (
                <tr key={p.id}>
                  <MonoCell>{p.id}</MonoCell>
                  <MonoCell>{p.kind}</MonoCell>
                  <td>{p.description}</td>
                  <td>
                    {!p.available ? (
                      <Badge tone="neutral">No disponible</Badge>
                    ) : !p.enabled ? (
                      <Badge tone="warn">No habilitada</Badge>
                    ) : (
                      <Badge tone="ok">Disponible</Badge>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <Card title="Datasets" meta={`${datasets.length}`} flush>
        {datasets.length === 0 ? (
          <EmptyState>Sin datasets disponibles</EmptyState>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Dataset</th>
                <th>Descripción</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {datasets.map((d) => (
                <tr key={d.id}>
                  <MonoCell>{d.id}</MonoCell>
                  <td>{d.description}</td>
                  <td>
                    {d.available ? (
                      <Badge tone="ok">Montado</Badge>
                    ) : (
                      <Badge tone="neutral">No montado</Badge>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <Card title="Conjuntos de prompts del repositorio" meta={`${sets.length}`} flush>
        {sets.length === 0 ? (
          <EmptyState>Sin conjuntos de prompts</EmptyState>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Conjunto</th>
                <th>Estado</th>
                <th>Clases</th>
              </tr>
            </thead>
            <tbody>
              {sets.map((s) => (
                <tr key={s.id}>
                  <MonoCell>{s.id}</MonoCell>
                  <td>
                    {s.frozen ? <Badge tone="ok">Congelado</Badge> : <Badge tone="neutral">Abierto</Badge>}
                  </td>
                  <MonoCell>{s.classes.map((c) => c.id).join(', ')}</MonoCell>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
    </>
  )
}
