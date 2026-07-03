import { useEffect, useReducer, useRef } from 'react'
import { streamUrl } from './api'
import type { StreamEvent } from './types'

const HISTORY_MAX = 300
const ERRORS_MAX = 100
const RECONNECT_MS = 2000

export interface LiveState {
  lastMetric: Extract<StreamEvent, { type: 'metric' }> | null
  fpsHistory: number[]
  latencyHistory: number[]
  detectionsTotal: number
  errors: Array<Extract<StreamEvent, { type: 'error' }>>
  finalState: { status: string; error: string | null } | null
}

export const initialLiveState = (): LiveState => ({
  lastMetric: null,
  fpsHistory: [],
  latencyHistory: [],
  detectionsTotal: 0,
  errors: [],
  finalState: null,
})

export function applyEvent(state: LiveState, event: StreamEvent): LiveState {
  switch (event.type) {
    case 'metric':
      return {
        ...state,
        lastMetric: event,
        fpsHistory: [...state.fpsHistory, event.fps].slice(-HISTORY_MAX),
        latencyHistory: [...state.latencyHistory, event.latency_total_ms].slice(-HISTORY_MAX),
      }
    case 'detection':
      return { ...state, detectionsTotal: state.detectionsTotal + event.count }
    case 'error':
      return { ...state, errors: [...state.errors, event].slice(-ERRORS_MAX) }
    case 'state':
      return { ...state, finalState: { status: event.status, error: event.error } }
    default:
      return state
  }
}

export function useRunStream(runId: string, enabled: boolean): LiveState {
  const [state, dispatch] = useReducer(applyEvent, undefined, initialLiveState)
  const stopped = useRef(false)
  useEffect(() => {
    if (!enabled) return
    stopped.current = false
    let socket: WebSocket | null = null
    let timer: ReturnType<typeof setTimeout>
    const connect = () => {
      socket = new WebSocket(streamUrl(runId))
      socket.onmessage = (message) => dispatch(JSON.parse(message.data) as StreamEvent)
      // Fallback ante caída: RECONECTAR (el run activo sigue siendo suscribible);
      // el polling de GET /api/runs/{id} solo re-hidrata estado, no telemetría.
      socket.onclose = (ev) => {
        if (!stopped.current && ev.code !== 4404 && ev.code !== 1000) {
          timer = setTimeout(connect, RECONNECT_MS)
        }
      }
    }
    connect()
    return () => {
      stopped.current = true
      clearTimeout(timer)
      socket?.close()
    }
  }, [runId, enabled])
  return state
}
