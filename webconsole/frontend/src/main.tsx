import React from 'react'
import ReactDOM from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import './styles/tokens.css'
import './styles/base.css'
import './styles/ui.css'
import App from './App'
import { crearQueryClient } from './api/queryClient'

// Una sola instancia para toda la aplicación: es la caché compartida que hace
// que el listado de corridas, la píldora de la barra lateral y los contadores se
// sirvan de la misma petición en vez de tener cada uno su propio intervalo.
const queryClient = crearQueryClient()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <HashRouter>
        <App />
      </HashRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
