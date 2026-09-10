import { Badge, Card, EmptyState, MonoCell, PageHeader, Table } from '../components/ui'
import { useTarget } from '../api/queries/platform'
import { useCatalogPromptSets, useDatasets, useIngestPlugins } from '../api/queries/catalog'
import { sourceLabel } from '../runview'

/** Nombre legible de cada umbral del modelo. Las claves son de la API. */
const UMBRAL_LABEL: Record<string, string> = {
  confidence: 'Confianza mínima',
  iou: 'Solapamiento máximo',
  box: 'Umbral de caja',
  text: 'Umbral de texto',
}

/** Una fuente acotada termina sola; una en vivo no. */
const KIND_LABEL: Record<string, string> = {
  bounded: 'Acotado',
  live: 'En vivo',
}

const dec2 = (v: number): string => v.toFixed(2).replace('.', ',')

function Metrica({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="eo-metric__label">{label}</div>
      <div className="eo-metric__value">{children}</div>
    </div>
  )
}

export default function CatalogPage() {
  const target = useTarget()
  // Los catálogos llevan la referencia del modelo en su clave de caché, así que
  // se recargan solos si el servicio reinicia con otro modelo. Antes eso era un
  // efecto keyado en `modelRef` repetido acá y en Nueva corrida.
  const plugins = useIngestPlugins().data ?? []
  const datasets = useDatasets().data ?? []
  const sets = useCatalogPromptSets().data ?? []
  return (
    <>
      <PageHeader
        title="Catálogos"
        meta="Lo que la instancia activa ofrece hoy — solo lectura"
      />

      {/* Tarjeta destacada y no una tabla de una fila: el modelo en uso es el
          contexto de todo lo demás de la pantalla, no un registro más. */}
      {target?.model ? (
        <section className="eo-target">
          <div className="eo-target__label">Modelo en uso</div>
          <div className="eo-target__name">{target.model.ref}</div>
          <div className="eo-target__foot">
            <Metrica label="Adaptador">{target.model.adapter ?? '—'}</Metrica>
            <Metrica label="Dispositivo">{target.model.device ?? '—'}</Metrica>
            {Object.entries(target.model.thresholds)
              .filter(([, v]) => v != null)
              .map(([k, v]) => (
                <Metrica key={k} label={UMBRAL_LABEL[k] ?? k}>
                  {dec2(Number(v))}
                </Metrica>
              ))}
          </div>
          <p className="eo-cap">
            Estos valores son fijos por instancia. Para usar otro modelo hay que activar otra
            instancia desde Plataforma.
          </p>
        </section>
      ) : (
        <Card title="Modelo en uso" flush>
          <EmptyState hint="El motor de detección todavía no respondió.">
            Servicio no listo
          </EmptyState>
        </Card>
      )}

      <Card
        title="Orígenes de imágenes"
        meta={`${plugins.filter((p) => p.enabled).length} de ${plugins.length} disponibles`}
        flush
      >
        {plugins.length === 0 ? (
          <EmptyState>Sin orígenes de imágenes</EmptyState>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Origen</th>
                <th>Tipo</th>
                <th>Disponibilidad</th>
                <th>Por qué</th>
              </tr>
            </thead>
            <tbody>
              {plugins.map((p) => (
                <tr key={p.id}>
                  <td>{sourceLabel(p.id)}</td>
                  <td>{KIND_LABEL[p.kind] ?? p.kind}</td>
                  <td>
                    {!p.available ? (
                      <Badge tone="neutral">No disponible</Badge>
                    ) : !p.enabled ? (
                      <Badge tone="warn">No habilitada</Badge>
                    ) : (
                      <Badge tone="ok">Disponible</Badge>
                    )}
                  </td>
                  {/* El motivo del backend gana sobre la descripción genérica:
                      dice por qué NO se puede usar, que es lo que se busca acá. */}
                  <td className="eo-cell--wrap">{p.disabled_reason ?? p.description}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <Card title="Conjuntos de imágenes" meta={`${datasets.length}`} flush>
        {datasets.length === 0 ? (
          <EmptyState>Sin conjuntos de imágenes</EmptyState>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Conjunto</th>
                <th>Por qué</th>
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
                <th className="eo-th--numeric">Clases</th>
                <th>Clases que define</th>
              </tr>
            </thead>
            <tbody>
              {sets.map((s) => (
                <tr key={s.id}>
                  <MonoCell>{s.id}</MonoCell>
                  <td>
                    {s.frozen ? <Badge tone="ok">Congelado</Badge> : <Badge tone="neutral">Abierto</Badge>}
                  </td>
                  <td className="eo-num">{s.classes.length}</td>
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
