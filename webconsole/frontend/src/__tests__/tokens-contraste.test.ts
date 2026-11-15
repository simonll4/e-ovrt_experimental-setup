// @vitest-environment node
// Sin DOM: lee styles/tokens.css del disco y mide.
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const css = readFileSync(new URL('../styles/tokens.css', import.meta.url), 'utf8')

/** El contraste de los dos temas, medido sobre los valores reales de styles/tokens.css (plan
 *  §10: «los colores de estado y los de los gráficos se definen como pares claro y oscuro, con el
 *  contraste comprobado en los dos»). Si alguien cambia un color y lo deja debajo del mínimo,
 *  este test lo dice antes de que se vea. */

function bloque(selector: string): Record<string, string> {
  const i = css.indexOf(selector)
  if (i < 0) throw new Error(`tokens.css no tiene el bloque ${selector}`)
  const ini = css.indexOf('{', i)
  const fin = css.indexOf('}', ini)
  const vars: Record<string, string> = {}
  for (const m of css.slice(ini + 1, fin).matchAll(/--([\w-]+):\s*([^;]+);/g)) vars[m[1]] = m[2].trim()
  return vars
}

type RGB = [number, number, number]

const hex = (h: string): RGB => {
  const s = h.replace('#', '')
  const l = s.length === 3 ? s.split('').map((c) => c + c).join('') : s
  return [0, 2, 4].map((k) => parseInt(l.slice(k, k + 2), 16)) as RGB
}

/** Un `rgba()` compuesto sobre su fondo; un hex queda como está. */
const sobre = (color: string, fondo: RGB): RGB => {
  const m = color.match(/rgba\(\s*(\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\s*\)/)
  if (!m) return hex(color)
  const a = Number(m[4])
  return [1, 2, 3].map((k, i) => Math.round(Number(m[k]) * a + fondo[i] * (1 - a))) as RGB
}

const luminancia = (c: RGB) => {
  const [r, g, b] = c.map((v) => {
    const x = v / 255
    return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

const contraste = (a: RGB, b: RGB) => {
  const [x, y] = [luminancia(a), luminancia(b)].sort((p, q) => q - p)
  return (x + 0.05) / (y + 0.05)
}

const claro = bloque(':root {')
const TEMAS: Array<[string, Record<string, string>]> = [
  ['claro', claro],
  ['oscuro', { ...claro, ...bloque(':root[data-theme="dark"]') }],
]

/** Las series que el tema claro deja debajo de 3:1 contra la superficie: la paleta de
 *  referencia lo admite si el gráfico rotula sus marcas (src/palette.ts). Una que no esté en esta
 *  lista y baje de 3:1 es un error. */
const SERIES_CON_ROTULO: Record<string, string[]> = { claro: ['c3', 'c4', 'c5'], oscuro: [] }

describe.each(TEMAS)('tema %s', (nombre, v) => {
  const superficies = { bg: hex(v.bg), s1: hex(v.s1), s2: hex(v.s2), s3: hex(v.s3) }

  it('el texto, incluidos motivos y metadatos, pasa 4,5:1 sobre todas las superficies', () => {
    for (const t of ['tx', 'tx2', 'tx3', 'tx4', 'ac-tx']) {
      for (const [s, fondo] of Object.entries(superficies)) {
        expect(contraste(hex(v[t]), fondo), `--${t} sobre ${s}`).toBeGreaterThanOrEqual(4.5)
      }
    }
  })

  it('los estados se leen como texto sobre las tarjetas y sobre su propio tinte', () => {
    for (const t of ['ok', 'wn', 'sr', 'er', 'live']) {
      for (const s of ['s1', 's2'] as const) {
        expect(contraste(hex(v[t]), superficies[s]), `--${t} sobre ${s}`).toBeGreaterThanOrEqual(4.5)
      }
      const tinte = sobre(v[`${t}-bg`], superficies.s1)
      expect(contraste(hex(v[t]), tinte), `--${t} sobre --${t}-bg`).toBeGreaterThanOrEqual(4.5)
    }
  })

  it('el borde de un control y el anillo de foco pasan 3:1; el texto sobre el acento, 4,5:1', () => {
    for (const s of ['s1', 's2'] as const) {
      expect(contraste(hex(v['bd-ctl']), superficies[s]), `--bd-ctl sobre ${s}`).toBeGreaterThanOrEqual(3)
      expect(contraste(hex(v.ac), superficies[s]), `--ac sobre ${s}`).toBeGreaterThanOrEqual(3)
    }
    expect(contraste(hex(v.ac), superficies.bg), '--ac sobre bg').toBeGreaterThanOrEqual(3)
    expect(contraste(hex(v['ac-text-on']), hex(v.ac)), '--ac-text-on sobre --ac').toBeGreaterThanOrEqual(4.5)
  })

  it('cada serie pasa 3:1 sobre la tarjeta, salvo las declaradas con rótulo', () => {
    for (let i = 1; i <= 8; i++) {
      const c = `c${i}`
      if (SERIES_CON_ROTULO[nombre].includes(c)) continue
      expect(contraste(hex(v[c]), superficies.s1), `--${c} sobre s1`).toBeGreaterThanOrEqual(3)
    }
  })
})
