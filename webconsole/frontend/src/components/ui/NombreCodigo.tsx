import { Fragment } from 'react'
import { NOMBRE_DE_CODIGO, nombreLlano } from '../../vocabulario'

/** Un código del informe como lo pide el plan (§4.2): el nombre llano primero y el código al lado,
 *  más chico. Sin nombre conocido queda el código solo. `nombre` pisa el del vocabulario cuando la
 *  pantalla ya lo tiene. */
export default function NombreCodigo({ codigo, nombre }: { codigo: string; nombre?: string }) {
  const llano = nombre ?? nombreLlano(codigo)
  if (!llano) return <code className="eo-codigo eo-codigo--solo">{codigo}</code>
  return (
    <span className="eo-nombre-codigo">
      {llano} <code className="eo-codigo">{codigo}</code>
    </span>
  )
}

const CODIGOS = new RegExp(`\\b(${Object.keys(NOMBRE_DE_CODIGO).map((c) => c.replace('-', '\\-')).join('|')})\\b`)

/** Un texto que nombra códigos del informe («CR-02 como el guion») con el nombre llano delante de
 *  cada uno («Sin chaleco CR-02 como el guion»). Si el texto ya trae el nombre justo antes
 *  («Latencia por cuadro G2A»), no se repite: el código queda solo, más chico. */
export function ConCodigos({ texto }: { texto: string }) {
  const partes = texto.split(CODIGOS)
  if (partes.length === 1) return <>{texto}</>
  return (
    <>
      {partes.map((parte, i) => {
        if (i % 2 === 0) return <Fragment key={i}>{parte}</Fragment>
        const llano = NOMBRE_DE_CODIGO[parte]
        const antes = partes[i - 1].trimEnd()
        if (antes.toLowerCase().endsWith(llano.toLowerCase())) return <code key={i} className="eo-codigo">{parte}</code>
        // En medio de una frase, el nombre va en minúscula («Imágenes, sin casco CR-01»).
        const enMedio = antes.length > 0 && !/[.:]$/.test(antes)
        return <NombreCodigo key={i} codigo={parte} nombre={enMedio ? llano[0].toLowerCase() + llano.slice(1) : llano} />
      })}
    </>
  )
}
