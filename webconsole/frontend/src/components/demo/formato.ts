/** Formatos de la demo: castellano llano, coma decimal, segundos con un decimal. */

export function segundos(ms: number | null | undefined, decimales = 1): string {
  if (ms == null || Number.isNaN(ms)) return '—'
  return (ms / 1000).toLocaleString('es-AR', {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  })
}

export function numero(valor: number | null | undefined, decimales = 1): string {
  if (valor == null || Number.isNaN(valor)) return '—'
  return valor.toLocaleString('es-AR', { maximumFractionDigits: decimales })
}

export function cronometro(totalS: number | null | undefined): string {
  if (totalS == null || totalS < 0) return '00:00'
  const s = Math.floor(totalS)
  const mm = String(Math.floor(s / 60)).padStart(2, '0')
  const ss = String(s % 60).padStart(2, '0')
  return `${mm}:${ss}`
}

export function hora(iso: string | null | undefined): string {
  if (!iso) return '—'
  const fecha = new Date(iso)
  if (Number.isNaN(fecha.getTime())) return iso
  return fecha.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function fechaCorta(iso: string | null | undefined): string {
  if (!iso) return '—'
  const fecha = new Date(iso)
  if (Number.isNaN(fecha.getTime())) return iso
  return fecha.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit' })
}

export const SEVERIDAD: Record<string, string> = { high: 'alta', medium: 'media', low: 'baja' }

/** «Sin casco» / «Sin chaleco»: lo que se ve en la tarjeta mientras confirma. */
export const FALTA: Record<string, string> = { 'CR-01': 'Sin casco', 'CR-02': 'Sin chaleco' }
