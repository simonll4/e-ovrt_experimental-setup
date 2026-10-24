import Button from './Button'

/** Datos conocidos + una actualización que falló: los datos quedan a la vista
 *  y se dice que pueden estar viejos. Convertir ese fallo en un vacío o en un
 *  error de pantalla completa borraba lo único que se sabía. */
export default function StaleNotice({
  what,
  onRetry,
  retrying,
}: {
  what: string
  onRetry?: () => void
  retrying?: boolean
}) {
  return (
    <div className="eo-stale" role="status">
      <span>
        No se pudo actualizar {what}. Se muestran los últimos datos recibidos.
      </span>
      {onRetry && (
        <Button variant="ghost" onClick={onRetry} disabled={retrying}>
          {retrying ? 'Reintentando…' : 'Reintentar'}
        </Button>
      )}
    </div>
  )
}
