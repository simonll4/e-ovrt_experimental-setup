import { Link, useLocation } from 'react-router-dom'
import { Card, EmptyState, PageHeader } from '../components/ui'

/**
 * Ruta inexistente.
 *
 * Antes no había ninguna: una URL mal escrita —o un marcador de una versión
 * anterior de la consola, que es el caso frecuente— dejaba el armazón dibujado
 * con el contenido en blanco, sin decir qué había pasado.
 */
export default function NotFoundPage() {
  const { pathname } = useLocation()
  return (
    <>
      <PageHeader title="Esa pantalla no existe" />
      <Card>
        <EmptyState
          hint={
            <>
              Puede ser un marcador viejo. Volvé a <Link to="/">Corridas</Link> y buscá desde
              ahí.
            </>
          }
        >
          No hay nada en <span className="eo-mono">{pathname}</span>
        </EmptyState>
      </Card>
    </>
  )
}
