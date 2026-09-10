import { useState, type ReactElement, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  render as renderRTL,
  renderHook as renderHookRTL,
  type RenderOptions,
  type RenderHookOptions,
} from '@testing-library/react'

/**
 * Utilidades de render para tests.
 *
 * Todo lo que consuma datos pasa por TanStack Query, así que necesita un
 * `QueryClientProvider`. En vez de repetir el envoltorio en cada archivo, los
 * tests importan `render` de acá en lugar de `@testing-library/react`.
 *
 * El cliente se crea **por test**, no una vez por módulo: compartirlo filtraría
 * la caché de un caso al siguiente y los tests pasarían o fallarían según el
 * orden en que corren.
 */
export function crearQueryClientDePrueba(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Un test que ejercita el camino de error no debe esperar reintentos.
        retry: false,
        // OJO: no se desactiva `refetchInterval`. Hay tests que dependen del
        // poll (por ejemplo, que los catálogos se recarguen cuando el servicio
        // reinicia con otro modelo) y apagarlo los volvía verdes por la razón
        // equivocada. Los intervalos se detienen al desmontar, así que con
        // `cleanup()` no quedan timers colgados.
        refetchOnWindowFocus: false,
        gcTime: 0,
      },
      mutations: { retry: false },
    },
  })
}

function Envoltorio({ children }: { children: ReactNode }) {
  const [client] = useState(crearQueryClientDePrueba)
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

export function render(ui: ReactElement, options?: Omit<RenderOptions, 'wrapper'>) {
  return renderRTL(ui, { wrapper: Envoltorio, ...options })
}

export function renderHook<Resultado, Props>(
  hook: (props: Props) => Resultado,
  options?: Omit<RenderHookOptions<Props>, 'wrapper'>,
) {
  return renderHookRTL(hook, { wrapper: Envoltorio, ...options })
}

// El resto se reexporta explícitamente, NO con `export *`: al reexportar todo,
// el `render` y el `renderHook` de la librería pisaban a los de acá y los tests
// volvían a renderizar sin el provider — el síntoma era un "No QueryClient set"
// en archivos que ya importaban de este módulo.
export {
  act,
  cleanup,
  fireEvent,
  screen,
  waitFor,
  waitForElementToBeRemoved,
  within,
} from '@testing-library/react'
