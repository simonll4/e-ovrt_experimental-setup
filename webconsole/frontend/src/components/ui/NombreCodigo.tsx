import { nombreLlano } from '../../vocabulario'

/** Un código del informe como lo pide el plan (§4.2): el nombre llano primero y el código al
 *  lado, más chico. Sin nombre conocido queda el código solo. `nombre` pisa el del vocabulario
 *  cuando la pantalla ya lo tiene. */
export default function NombreCodigo({ codigo, nombre }: { codigo: string; nombre?: string }) {
  const llano = nombre ?? nombreLlano(codigo)
  if (!llano) return <code className="eo-codigo eo-codigo--solo">{codigo}</code>
  return (
    <span className="eo-nombre-codigo">
      {llano} <code className="eo-codigo">{codigo}</code>
    </span>
  )
}
