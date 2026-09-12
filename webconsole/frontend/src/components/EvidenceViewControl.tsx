import { useState } from 'react'
import type { EvidenceInfo, EvidenceListingMeta, EvidenceView } from '../types'
import { Badge, Banner, SegmentedControl } from './ui'

export function useEvidenceView(surface: 'runs' | 'experiments') {
  const key = `eo-evidence-view-${surface}`
  const [view, setView] = useState<EvidenceView>(() => {
    try {
      const saved = localStorage.getItem(key)
      if (saved === 'todas' || saved === 'archivadas') return saved
    } catch { /* El navegador puede deshabilitar el almacenamiento. */ }
    return 'evidencia'
  })
  const changeView = (value: EvidenceView) => {
    setView(value)
    try { localStorage.setItem(key, value) } catch { /* La selección sigue funcionando. */ }
  }
  return [view, changeView] as const
}

export default function EvidenceViewControl({ view, onChange, meta, noun }: {
  view: EvidenceView
  onChange: (view: EvidenceView) => void
  meta?: EvidenceListingMeta
  noun: 'corridas' | 'ejecuciones'
}) {
  const archived = noun === 'ejecuciones' ? meta?.archivedExecutions : meta?.archived
  return (
    <div className="eo-toolbar" role="group" aria-label="Vista de evidencia">
      <SegmentedControl<EvidenceView> value={view} onChange={onChange} options={[
        { value: 'evidencia', label: 'Evidencia' },
        { value: 'archivadas', label: 'Archivadas' },
        { value: 'todas', label: 'Todas' },
      ]} />
      {meta?.available === false ? (
        <span className="eo-note">Registro de evidencia no disponible en esta máquina. Elegí Todas para ver el historial.</span>
      ) : view === 'evidencia' && archived != null && archived > 0 ? (
        <span className="eo-note">{archived} {noun} archivadas</span>
      ) : null}
    </div>
  )
}

/**
 * Lo que la clasificación de esta pantalla presupone, declarado cuando falta.
 *
 * Sin esto la pantalla arma una frase perfectamente formada —«472 corridas ·
 * agrupadas en 1 resultados de respaldo», chip «Fuera del registro 472»—
 * construida entera sobre un archivo ausente, sin una sola advertencia. Son
 * DOS fallas distintas y se dicen distinto:
 *
 * - `available: false` — el archivo CONGELADO (`results/evidence-runs/`, los
 *   cuatro CSV) no está, o está y no trae una sola fila. Ninguna corrida es
 *   evidencia de nada.
 * - `clasificacionAvailable: false` — el archivo de evidencia carga, pero la
 *   configuración MUTABLE (`clasificacion.yaml`, que edita una persona) no
 *   está, o está y no declara ningún rol que el registro use. Es la peor de las
 *   dos porque todo se ve normal: cada corrida cae a «Fuera del registro» en
 *   silencio.
 * - `rolesSinClasificar > 0` con la clasificación disponible — hay una
 *   clasificación y es PARCIAL. Ningún booleano distingue esto de "está todo
 *   bien". El TITULAR es un conteo medido; la explicación NO puede ser
 *   universal: `clase_de` toma la clase MÁS FUERTE entre los roles de la
 *   corrida (y una excepción explícita gana sobre todo), así que una corrida
 *   con un rol sin clasificar y otro clasificado se muestra con clase. Hoy hay
 *   49 corridas con más de un rol en el registro: "puede haber", nunca "se
 *   muestran".
 *
 * Los dos primeros flags miran CONTENIDO, no existencia de archivo (R-31), así
 * que NINGUNA de estas frases puede afirmar que un archivo "falta": eso sería
 * convertir una señal que dejó de significar ausencia en una afirmación de
 * ausencia. Cada banner dice el estado que su flag significa y separa el
 * remedio, porque restaurar del backup no sirve para un archivo presente.
 *
 * Ausente (`undefined`) NO es `false`: sin la cabecera no se afirma nada — es
 * lo que pasa con la fixture del contrato congelado, que no la manda.
 */
export function AvisoRegistro({ meta, noun }: {
  meta?: EvidenceListingMeta
  noun: 'corridas' | 'ejecuciones'
}) {
  if (meta?.available === false) {
    return <Banner tone="warn">
      <b>Registro de evidencia no disponible en esta máquina.</b> Ninguna de las {noun} que
      se listan abajo está clasificada por su evidencia: el archivo curado
      (<span className="eo-mono">results/evidence-runs/</span>) no se encontró, o está
      presente y no trae una sola fila. Si falta, restauralo desde la capa de evidencia
      del backup; si está, regeneralo
      con <span className="eo-mono">python3 tools/evidence_runs.py sync</span>. Después
      reiniciá la consola.
    </Banner>
  }
  if (meta?.clasificacionAvailable === false) {
    return <Banner tone="warn">
      <b>Taxonomía de clases no disponible.</b> El archivo de evidencia sí cargó,
      pero <span className="eo-mono">results/evidence-vista/clasificacion.yaml</span> no
      está, o está y no declara ningún rol de los que el registro usa: toda clase que se
      muestre abajo es «Fuera del registro» por ausencia de la declaración, no por una
      decisión sobre esas {noun}. Abrí el archivo antes de reponerlo: si está ahí, el
      problema es su contenido, no su falta.
    </Banner>
  }
  const { rolesSinClasificar: sinClase, rolesDelRegistro: total } = meta ?? {}
  if (sinClase != null && total != null && sinClase > 0) {
    return <Banner tone="warn">
      <b>Clasificación incompleta: {sinClase} de {total} roles sin clasificar.</b> Puede
      haber {noun} que se muestren «Fuera del registro» porque nadie declaró la clase de su
      rol en <span className="eo-mono">results/evidence-vista/clasificacion.yaml</span>, no
      porque queden fuera del registro. No son necesariamente todas: una corrida con más de
      un rol toma la clase más fuerte de los suyos, así que un rol sin declarar puede quedar
      tapado por otro que sí lo está.
    </Banner>
  }
  return null
}

export function EvidenceBadge({ evidence }: { evidence?: EvidenceInfo }) {
  if (!evidence?.is_evidence) return null
  const label = evidence.result_ids[0] ?? 'Evidencia'
  return <span className="eo-evidence-badge" title={evidence.result_ids.join('\n') || evidence.reason}>
    <Badge tone="neutral">{label}</Badge>
  </span>
}
