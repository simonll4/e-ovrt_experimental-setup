import { useEffect, useRef, useState } from 'react'
import { previewStreamUrl } from './api'
import type { PreviewFrameHeader } from './types'

export interface PreviewLive {
  connected: boolean
  frameUrl: string | null
  header: PreviewFrameHeader | null
  fps: number
  finalState: { status: string; error: string | null } | null
}

export function parsePreviewMessage(data: ArrayBuffer): { header: PreviewFrameHeader; jpeg: Blob } {
  const view = new DataView(data)
  const headerLen = view.getUint32(0)
  const header = JSON.parse(
    new TextDecoder().decode(new Uint8Array(data, 4, headerLen)),
  ) as PreviewFrameHeader
  const jpeg = new Blob([new Uint8Array(data, 4 + headerLen)], { type: 'image/jpeg' })
  return { header, jpeg }
}

const INITIAL: PreviewLive = { connected: false, frameUrl: null, header: null, fps: 0, finalState: null }

export function usePreviewStream(enabled: boolean): PreviewLive {
  const [state, setState] = useState<PreviewLive>(INITIAL)
  const urlRef = useRef<string | null>(null)
  const timesRef = useRef<number[]>([])

  useEffect(() => {
    if (!enabled) {
      setState(INITIAL)
      return
    }
    const ws = new WebSocket(previewStreamUrl())
    ws.binaryType = 'arraybuffer'
    ws.onopen = () => setState((s) => ({ ...s, connected: true }))
    ws.onmessage = (ev) => {
      if (typeof ev.data === 'string') {
        const parsed = JSON.parse(ev.data) as { type: string; status: string; error: string | null }
        if (parsed.type === 'state') {
          setState((s) => ({ ...s, finalState: { status: parsed.status, error: parsed.error } }))
        }
        return
      }
      const { header, jpeg } = parsePreviewMessage(ev.data as ArrayBuffer)
      const url = URL.createObjectURL(jpeg)
      if (urlRef.current) URL.revokeObjectURL(urlRef.current)
      urlRef.current = url
      const now = performance.now()
      timesRef.current = [...timesRef.current.filter((t) => now - t < 1000), now]
      setState((s) => ({ ...s, frameUrl: url, header, fps: timesRef.current.length }))
    }
    ws.onclose = () => setState((s) => ({ ...s, connected: false }))
    return () => {
      ws.close()
      if (urlRef.current) URL.revokeObjectURL(urlRef.current)
      urlRef.current = null
      timesRef.current = []
    }
  }, [enabled])

  return state
}
