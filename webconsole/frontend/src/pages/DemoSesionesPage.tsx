import { Link } from 'react-router-dom'
import { useTomas } from '../api/queries/gen2'
import { Card, Disclosure, MonoCell, PageHeader, Table, TableScroll } from '../components/ui'
import NombreCodigo from '../components/ui/NombreCodigo'
import type { TomaEnVivo, VistaTomas } from '../types'
import { EstadoDeLectura } from './evidencia/comun'
import './DemoPage.css'

const TIPO: Record<VistaTomas['otras'][number]['tipo'], string> = {
  descartada: 'Descartada',
  calibracion: 'Calibración',
  ensayo: 'Ensayo',
  exploracion: 'Exploración',
  no_evaluable: 'No evaluable',
  sin_prueba: 'Sin prueba',
}

function EnlaceToma({ sid, disponible }: { sid: string; disponible: boolean }) {
  if (!disponible) {
    return <span className="eo-note--meta" title={sid}>no está en este equipo: el video no se publica</span>
  }
  return <Link className="eo-mono" to={`/demo/resultado/${encodeURIComponent(sid)}`}>{sid}</Link>
}

const siNo = (v: boolean | null | undefined) =>
  v == null ? '—' : v ? 'sí' : <span className="eo-note--error">no</span>

function TomasDeUnaPrueba({ id, tomas }: { id: string; tomas: TomaEnVivo[] }) {
  const con = (campo: 'stream' | 'motor' | 'camara' | 'remera') => tomas.some((t) => t[campo])
  const evaluadas = tomas.filter((t) => t.como_se_esperaba != null)
  const comoElGuion = evaluadas.filter((t) => t.como_se_esperaba).length
  return (
    <Card
      title={<Link to={`/resultados/${encodeURIComponent(id)}`}><NombreCodigo codigo={id} /></Link>}
      meta={evaluadas.length > 0 ? `${comoElGuion} de ${evaluadas.length} como el guion` : `${tomas.length} tomas`}
      flush
    >
      <TableScroll label={`Tomas de ${id}`}>
        <Table aria-label={`Tomas de ${id}`}>
          <thead>
            <tr>
              <th>Escena</th>
              {con('stream') && <th>Stream</th>}
              {con('motor') && <th>Motor</th>}
              {con('camara') && <th>Cámara</th>}
              {con('remera') && <th>Remera</th>}
              <th>Como el guion</th>
              <th>Toma</th>
            </tr>
          </thead>
          <tbody>
            {tomas.map((t) => (
              <tr key={t.session_id}>
                <td>{t.escena ?? '—'}</td>
                {con('stream') && <td>{t.stream ?? '—'}</td>}
                {con('motor') && <MonoCell>{t.motor ?? '—'}</MonoCell>}
                {con('camara') && <MonoCell>{t.camara ?? '—'}</MonoCell>}
                {con('remera') && <td>{t.remera ?? '—'}</td>}
                <td>
                  {siNo(t.como_se_esperaba)}
                  {t.sujeto_como_se_esperaba != null && t.sujeto_como_se_esperaba !== t.como_se_esperaba && (
                    <span className="eo-note--meta"> · por sujeto: {t.sujeto_como_se_esperaba ? 'sí' : 'no'}</span>
                  )}
                </td>
                <td><EnlaceToma sid={t.session_id} disponible={t.disponible} /></td>
              </tr>
            ))}
          </tbody>
        </Table>
      </TableScroll>
    </Card>
  )
}

/** «Tomas en vivo» (plan de la consola, §6): las sesiones de las jornadas agrupadas por la prueba en la que
 *  cuentan, cada una con su escena y si salió como el guion. Lo que no cuenta —calibraciones, ensayos,
 *  exploraciones y tomas descartadas— va plegado, con su motivo. Cada toma abre su resultado. */
export default function DemoSesionesPage() {
  const q = useTomas()
  if (q.isPending || q.error) return <EstadoDeLectura titulo="Tomas en vivo" q={q} />
  const { pruebas, otras } = q.data
  const total = pruebas.reduce((n, p) => n + p.tomas.length, 0)
  return (
    <div className="eo-gen2">
      <PageHeader title="Tomas en vivo" meta={`${total} tomas en ${pruebas.length} pruebas`} />
      {pruebas.map((p) => <TomasDeUnaPrueba key={p.id} id={p.id} tomas={p.tomas} />)}
      {otras.length > 0 && (
        <Card>
          <Disclosure summary={<h2 className="eo-gen2__plegado">Ensayos, calibraciones y tomas que no cuentan ({otras.length})</h2>}>
            <TableScroll label="Tomas que no cuentan">
              <Table aria-label="Tomas que no cuentan">
                <thead><tr><th>Toma</th><th>Escena</th><th>Qué es</th><th>Motivo</th></tr></thead>
                <tbody>
                  {otras.map((o) => (
                    <tr key={o.session_id}>
                      <td><EnlaceToma sid={o.session_id} disponible={o.disponible} /></td>
                      <td>{o.escena ?? '—'}</td>
                      <td>{TIPO[o.tipo] ?? o.tipo}</td>
                      <td>
                        {o.motivo}
                        {o.quien && <span className="eo-note--meta"> · firmó {o.quien}{o.prueba ? ` en ${o.prueba}` : ''}</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </TableScroll>
          </Disclosure>
        </Card>
      )}
    </div>
  )
}
