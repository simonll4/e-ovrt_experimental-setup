import { useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useFalsasAlarmasErr01 } from '../../api/queries/gen2'
import { Card, MonoCell, SegmentedControl, Table, TableScroll } from '../../components/ui'
import NombreCodigo from '../../components/ui/NombreCodigo'
import { CAUSA_FALSA_ALARMA } from '../../vocabulario'
import './Clip.css'

const TODAS = 'todas'

/** Las falsas alarmas por sujeto en obra real, una por una, con su causa (ERR-01). Cada una abre su clip en el
 *  run de ALR-08, con el cuadro de la alerta y la persona que la disparó: «mostrame una falsa alarma por EPP no
 *  detectado». La causa se puede pedir por la dirección (`?causa=P-no-detectado`), que es como enlaza la pregunta
 *  «¿Qué pasa en obra real?». */
export default function FalsasAlarmasUnaPorUna() {
  const q = useFalsasAlarmasErr01()
  const [params, setParams] = useSearchParams()
  const causa = params.get('causa') ?? TODAS
  const pedida = params.get('causa')
  const cargada = Boolean(q.data)
  // Se llega con una causa desde «¿Qué pasa en obra real?» («ver los casos»): la lista es lo que se pidió, así que
  // se baja a ella en vez de dejar a quien llega arriba de todo.
  useEffect(() => {
    if (pedida && cargada) document.getElementById('falsas-alarmas')?.scrollIntoView?.({ block: 'start' })
  }, [pedida, cargada])
  if (q.isPending || q.error || !q.data) return null
  const { falsas_alarmas: filas, prueba_de_las_alertas: deDonde } = q.data
  const causas = Object.keys(CAUSA_FALSA_ALARMA).filter((c) => filas.some((f) => f.causa === c))
  const visibles = causa === TODAS ? filas : filas.filter((f) => f.causa === causa)
  const elegir = (valor: string) => {
    const siguiente = new URLSearchParams(params)
    if (valor === TODAS) siguiente.delete('causa')
    else siguiente.set('causa', valor)
    setParams(siguiente, { replace: true })
  }
  return (
    <Card id="falsas-alarmas" className="eo-falsas" title="Las falsas alarmas, una por una"
      meta={`${visibles.length} de ${filas.length} · cada una abre su clip`} flush>
      <div className="eo-gen2__filtro">
        <SegmentedControl
          label="Causa"
          value={causa}
          onChange={elegir}
          options={[{ value: TODAS, label: 'Todas' },
            ...causas.map((c) => ({ value: c, label: CAUSA_FALSA_ALARMA[c].nombre }))]}
        />
        {causa !== TODAS && CAUSA_FALSA_ALARMA[causa] && (
          <p className="eo-note">{CAUSA_FALSA_ALARMA[causa].nombre}: {CAUSA_FALSA_ALARMA[causa].que}.</p>
        )}
      </div>
      <TableScroll label="Las falsas alarmas, una por una">
        <Table aria-label="Las falsas alarmas, una por una">
          <thead>
            <tr><th>Clip</th><th>Condición</th><th className="eo-num">Cuadro</th>{causa === TODAS && <th>Causa</th>}<th>Luz</th></tr>
          </thead>
          <tbody>
            {visibles.map((f) => (
              <tr key={f.alert_id}>
                <MonoCell>
                  <Link to={`/resultados/${encodeURIComponent(deDonde)}/clips/${encodeURIComponent(f.clip)}?${new URLSearchParams({ alerta: f.alert_id })}`}
                    aria-label={`Ver esta falsa alarma en el clip ${f.clip}`}>{f.clip}</Link>
                </MonoCell>
                <td><NombreCodigo codigo={f.condicion} /></td>
                <td className="eo-num">{f.cuadro ?? '—'}</td>
                {causa === TODAS && <td>{CAUSA_FALSA_ALARMA[f.causa]?.nombre ?? f.causa}</td>}
                <td>{f.iluminacion ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </TableScroll>
    </Card>
  )
}
