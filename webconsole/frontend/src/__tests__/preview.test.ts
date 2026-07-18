import { describe, expect, it } from 'vitest'
import { parsePreviewMessage } from '../preview'

function buildMessage(header: object, jpeg: Uint8Array): ArrayBuffer {
  const hb = new TextEncoder().encode(JSON.stringify(header))
  const buf = new Uint8Array(4 + hb.length + jpeg.length)
  new DataView(buf.buffer).setUint32(0, hb.length)
  buf.set(hb, 4)
  buf.set(jpeg, 4 + hb.length)
  return buf.buffer
}

describe('parsePreviewMessage', () => {
  it('separa header JSON y payload JPEG', () => {
    const header = { seq: 3, ts: 1.5, width: 64, height: 48, mode: 'raw', detections: [] }
    const { header: parsed, jpeg } = parsePreviewMessage(buildMessage(header, new Uint8Array([0xff, 0xd8, 1])))
    expect(parsed.seq).toBe(3)
    expect(parsed.mode).toBe('raw')
    expect(jpeg.size).toBe(3)
  })

  it('conserva las detecciones', () => {
    const det = { label: 'helmet', score: 0.9, bbox_norm_xyxy: [0.1, 0.1, 0.5, 0.5] }
    const header = { seq: 1, ts: 0, width: 64, height: 48, mode: 'detect', detections: [det] }
    const { header: parsed } = parsePreviewMessage(buildMessage(header, new Uint8Array([0xff, 0xd8])))
    expect(parsed.detections).toEqual([det])
  })
})
