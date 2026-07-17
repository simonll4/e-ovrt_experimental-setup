import type { BadgeTone } from './types'

export function promptStatusTone(status: string): BadgeTone {
  if (status === 'frozen') return 'ok'
  if (status === 'frozen_pending_review') return 'warn'
  return 'neutral' // exploratory y cualquier estado nuevo
}
