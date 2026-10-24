#!/usr/bin/env node
// QA visual y de comportamiento de la consola, aislado del BFF real.
//
//   node webconsole/tools/capture_console.mjs --out tools/captures/qa \
//     --playwright-module <ruta a playwright/index.mjs> --chromium <ruta a chrome.exe>
//
// El Playwright no es dependencia del proyecto: se reutiliza el de un runtime
// de herramientas (`--playwright-module`). Para instalar uno propio:
//   npm install --prefix webconsole/tools/.capture-runtime playwright@1.57.0
//
// Modo sintético (el único que corre escenarios): compila el frontend, lo
// sirve desde un servidor estático propio SIN proxy, e intercepta todo /api —
// HTTP y WebSocket— con `capture_fixtures.mjs`. Una petición que el escenario
// no declara lo hace fallar: no hay fallback al BFF de :8090.
//
// Opciones: --solo <texto> filtra escenarios por id; --sin-build reutiliza el
// dist ya compilado; --base-url <url> captura las rutas contra un BFF sembrado
// (modo anterior, sin escenarios ni intercepción).
import { createHash } from 'node:crypto'
import { spawn } from 'node:child_process'
import { once } from 'node:events'
import { mkdir, mkdtemp, readFile, rm, stat, writeFile } from 'node:fs/promises'
import { createServer as createHttpServer } from 'node:http'
import { tmpdir } from 'node:os'
import { dirname, extname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { parseArgs } from 'node:util'
import { FECHA, PNG, crearMundo, experimentId, runId } from './capture_fixtures.mjs'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const { values } = parseArgs({ options: {
  out: { type: 'string', default: 'tools/captures/qa' },
  'base-url': { type: 'string' },
  'playwright-module': { type: 'string', default: resolve(root, 'tools/.capture-runtime/node_modules/playwright/index.mjs') },
  chromium: { type: 'string' },
  solo: { type: 'string' },
  'sin-build': { type: 'boolean', default: false },
  synthetic: { type: 'boolean', default: true },
  'run-id': { type: 'string' },
  'experiment-id': { type: 'string' },
} })
const output = resolve(root, values.out)
await mkdir(output, { recursive: true })
const { chromium } = await import(pathToFileURL(resolve(values['playwright-module'])).href)
const lanzar = { headless: true, ...(values.chromium ? { executablePath: values.chromium } : {}) }

const RID = 'clip_bench/t1_gdinotiny560_v2short_scene'
const ANCHOS = [390, 768, 1280, 1920]
const ALTO = 900
// Chequeos con resultado conocido: si no coinciden, el escenario falla.
const ESPERADO = {
  cajonContieneFoco: true, cajonEscapeCierra: true, focoVuelveAlMenu: true, navegarEnfocaEncabezado: true,
  borradoSintetico: true, selectorPorTeclado: true, ampliacionCierraConEscape: true, focoTapadoPorPie: false,
  preguntaAntesDeCambiar: true, novenaDeshabilitada: true, animacionesAnuladas: true,
}

// ── Rutas: los 19 patrones de App.tsx, con parámetros reales ───────────────
const source = await readFile(resolve(root, 'frontend/src/App.tsx'), 'utf8')
const patrones = [...source.matchAll(/<Route\s+path="([^"]+)"/g)].map((m) => m[1])
const rutaDe = (p) => ({
  '/evidencia/paso': '/evidencia/paso?n=3',
  '/evidencia/resultado': `/evidencia/resultado?${new URLSearchParams({ id: RID, paso: '3' })}`,
  '/evidencia/run': `/evidencia/run?${new URLSearchParams({ plane: 'media-plane', run_id: 'm1', id: RID, paso: '3' })}`,
  '/runs/:id': `/runs/${runId}`,
  '/experiments/:id': `/experiments/${experimentId}`,
  '*': '/ruta-inexistente/con/un/camino/bastante/largo/que/no/existe/en/la/consola',
}[p] ?? p)

// ── Modo anterior: BFF sembrado, sin intercepción ──────────────────────────
if (values['base-url']) {
  const browser = await chromium.launch(lanzar)
  const results = []
  for (const [i, p] of patrones.entries()) {
    const route = rutaDe(p).replace(runId, values['run-id'] ?? runId).replace(experimentId, values['experiment-id'] ?? experimentId)
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'es-AR', timezoneId: 'UTC' })
    const page = await context.newPage()
    await page.goto(`${values['base-url'].replace(/\/$/, '')}/#${route}`, { waitUntil: 'networkidle' })
    const png = `${String(i).padStart(2, '0')}-${p.replace(/[^a-z0-9]/gi, '-').replace(/^-|-$/g, '') || 'corridas'}.png`
    const bytes = await page.screenshot({ path: resolve(output, png), fullPage: true })
    results.push({ route, png, sha256: createHash('sha256').update(bytes).digest('hex') })
    await context.close()
  }
  await writeFile(resolve(output, 'manifest.json'), JSON.stringify({ mode: 'seeded-bff', results }, null, 2) + '\n')
  await browser.close()
  process.exit(0)
}

// ── Compilación y servidor estático propio ─────────────────────────────────
const dist = resolve(root, 'frontend/dist')
if (!values['sin-build']) {
  const build = spawn(process.execPath, ['node_modules/vite/bin/vite.js', 'build'], { cwd: resolve(root, 'frontend'), stdio: 'inherit' })
  const [code] = await once(build, 'exit')
  if (code !== 0) throw Error('vite build falló')
}
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon' }
const servidor = createHttpServer(async (req, res) => {
  const pathname = decodeURIComponent(new URL(req.url, 'http://x').pathname)
  // Nada de /api llega acá: el navegador lo intercepta. Si llegara, es una
  // fuga y se responde con error, nunca se reenvía.
  if (pathname.startsWith('/api/')) { res.writeHead(599); res.end('fuga a /api sin interceptar'); return }
  let archivo = join(dist, pathname === '/' ? 'index.html' : pathname)
  try { if (!(await stat(archivo)).isFile()) archivo = join(dist, 'index.html') } catch { archivo = join(dist, 'index.html') }
  res.writeHead(200, { 'Content-Type': MIME[extname(archivo)] ?? 'application/octet-stream' })
  res.end(await readFile(archivo))
})
servidor.listen(0, '127.0.0.1')
await once(servidor, 'listening')
const BASE = `http://127.0.0.1:${servidor.address().port}`

// ── Mediciones dentro de la página ─────────────────────────────────────────
/* eslint-disable no-undef */
function medirEnPagina(opciones) {
  const de = document.documentElement
  const rect = (el) => { const r = el.getBoundingClientRect(); return { x: Math.round(r.left * 10) / 10, w: Math.round(r.width * 10) / 10, y: Math.round(r.top), h: Math.round(r.height * 10) / 10 } }
  const desc = (el) => `${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''}${el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : ''}`
  const out = {
    viewport: { innerWidth, innerHeight, clientWidth: de.clientWidth, scrollWidth: de.scrollWidth, scrollHeight: de.scrollHeight, dpr: devicePixelRatio },
    desbordeDocumento: de.scrollWidth > de.clientWidth + 1,
    regionesLocales: [], desbordesNoPrevistos: [], recortes: [], causantes: [],
  }
  // Si el documento desborda, qué elementos terminan más allá del borde (los
  // más profundos: el causante, no sus contenedores).
  if (out.desbordeDocumento) {
    const fuera = [...document.querySelectorAll('body *')].filter((el) => el.getBoundingClientRect().right > de.clientWidth + 1)
    out.causantes = fuera.filter((el) => ![...el.children].some((h) => fuera.includes(h))).slice(0, 6)
      .map((el) => ({ el: desc(el), right: Math.round(el.getBoundingClientRect().right), texto: (el.textContent ?? '').trim().slice(0, 50) }))
    // Texto que sale de una caja que sí entra (overflow visible).
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
    for (let n = walker.nextNode(); n && out.causantes.length < 10; n = walker.nextNode()) {
      if (!n.textContent.trim()) continue
      const range = document.createRange()
      range.selectNodeContents(n)
      const r = range.getBoundingClientRect()
      if (r.width && r.right > de.clientWidth + 1) out.causantes.push({ el: `texto en ${desc(n.parentElement)}`, right: Math.round(r.right), texto: n.textContent.trim().slice(0, 50) })
    }
  }
  // Altura fantasma: el documento no sigue más allá del área principal (p. ej.
  // texto .eo-sr absoluto que escapa de una lista con scroll propio).
  const principal = document.querySelector('.eo-main')
  if (principal) {
    const fondo = principal.getBoundingClientRect().bottom + scrollY
    out.alturaSobrante = Math.max(0, Math.round(de.scrollHeight - Math.max(fondo, innerHeight)))
    if (out.alturaSobrante > 2) {
      const abajo = [...document.querySelectorAll('body *')].filter((el) => { const r = el.getBoundingClientRect(); return r.height > 0 && r.bottom + scrollY > fondo + 2 })
      out.causantesAltura = abajo.filter((el) => ![...el.children].some((h) => abajo.includes(h))).slice(0, 6).map((el) => ({ el: desc(el), padre: desc(el.parentElement), texto: (el.textContent ?? '').trim().slice(0, 40) }))
    }
  }
  // Desborde horizontal: sólo en regiones locales previstas y usables con teclado.
  const permitidas = ['eo-tablewrap', 'eo-bars__scroll', 'eo-tabs']
  for (const el of document.querySelectorAll('body *')) {
    if (el.scrollWidth <= el.clientWidth + 1 || el.clientWidth === 0) continue
    const cs = getComputedStyle(el)
    if (cs.overflowX === 'auto' || cs.overflowX === 'scroll') {
      const prevista = permitidas.some((c) => el.classList.contains(c)) || el.tagName === 'TEXTAREA' || el.tagName === 'PRE'
      const teclado = el.tabIndex >= 0 || el.getAttribute('role') === 'tablist'
      const info = { el: desc(el), scrollWidth: el.scrollWidth, clientWidth: el.clientWidth, role: el.getAttribute('role'), nombre: el.getAttribute('aria-label'), teclado }
      if (prevista && teclado) out.regionesLocales.push(info)
      else out.desbordesNoPrevistos.push(info)
    } else if (cs.overflowX === 'hidden' || cs.overflowX === 'clip') {
      // .eo-sr se recorta a propósito: es texto sólo para lectores de pantalla.
      if (!el.matches('.eo-sr') && (cs.textOverflow === 'ellipsis' || el.closest('.eo-sidebar'))) out.recortes.push({ el: desc(el), texto: (el.textContent ?? '').slice(0, 60) })
    }
  }
  // Ejes: lo que cuelga directo del contenido comparte el mismo borde izquierdo.
  const contenido = document.querySelector('#contenido')
  if (contenido) {
    const pad = parseFloat(getComputedStyle(contenido).paddingLeft)
    const eje = contenido.getBoundingClientRect().left + pad
    const hijos = [...contenido.children, ...[...contenido.querySelectorAll(':scope > .eo-evidence, :scope > .eo-doc')].flatMap((w) => [...w.children])]
      .filter((el) => !el.matches('.eo-evidence, .eo-doc, .eo-doc__layout, .eo-sr, dialog') && el.getBoundingClientRect().width > 0)
    out.eje = { x: Math.round(eje * 10) / 10, fuera: hijos.filter((el) => Math.abs(el.getBoundingClientRect().left - eje) > 1).map((el) => ({ el: desc(el), x: rect(el).x })) }
    out.contenido = rect(contenido)
  }
  // Línea de tiempo: tres gráficos con igual inicio y ancho, eje alineado, cursor con alto útil.
  const plots = [...document.querySelectorAll('.eo-timeline__plot')]
  if (plots.length) {
    const r = plots.map(rect)
    const eje = document.querySelector('.eo-timeline__scalebody')
    const er = eje ? rect(eje) : null
    const cursores = [...document.querySelectorAll('.eo-timeline__cursor')].map(rect)
    out.timeline = {
      graficos: r,
      alineados: r.every((x) => Math.abs(x.x - r[0].x) <= 1 && Math.abs(x.w - r[0].w) <= 1),
      ejeAlineado: er ? Math.abs(er.x - r[0].x) <= 1 && Math.abs(er.w - r[0].w) <= 1 : null,
      altoDetecciones: r[0].h,
      cursores: cursores.map((c) => c.h),
    }
  }
  // Contraste sobre colores computados y fondos reales.
  if (opciones.contraste) {
    const parse = (c) => {
      let m = c.match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/)
      if (m) return [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]]
      m = c.match(/color\(srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)(?:\s*\/\s*([\d.]+))?\)/)
      if (m) return [+m[1] * 255, +m[2] * 255, +m[3] * 255, m[4] == null ? 1 : +m[4]]
      return null
    }
    const lum = ([r, g, b]) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4 }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b) }
    const sobre = (top, bot) => { const a = top[3]; return [top[0] * a + bot[0] * (1 - a), top[1] * a + bot[1] * (1 - a), top[2] * a + bot[2] * (1 - a), 1] }
    const fondo = (el) => {
      const capas = []
      for (let n = el; n; n = n.parentElement) {
        const c = parse(getComputedStyle(n).backgroundColor)
        if (c && c[3] > 0) { capas.push(c); if (c[3] >= 1) break }
      }
      let base = parse(getComputedStyle(document.body).backgroundColor) ?? [18, 18, 17, 1]
      for (const c of capas.reverse()) base = sobre(c, base)
      return base
    }
    const fallas = []
    let revisados = 0
    const visible = (el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 }
    for (const el of document.querySelectorAll('body *')) {
      if (!el.childNodes.length || !visible(el)) continue
      if (![...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) continue
      if (el.closest('[disabled], [aria-disabled="true"], [aria-hidden="true"], .eo-tip, svg, dialog:not([open])')) continue
      const cs = getComputedStyle(el)
      let alfa = 1
      for (let n = el; n; n = n.parentElement) alfa *= parseFloat(getComputedStyle(n).opacity)
      const fg = parse(cs.color)
      if (!fg) continue
      const bg = fondo(el)
      const color = sobre([fg[0], fg[1], fg[2], fg[3] * alfa], bg)
      const l1 = lum(color), l2 = lum(bg)
      const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05)
      const tam = parseFloat(cs.fontSize)
      const grande = tam >= 24 || (tam >= 18.66 && parseInt(cs.fontWeight) >= 700)
      revisados++
      if (ratio < (grande ? 3 : 4.5)) fallas.push({ el: desc(el), texto: el.textContent.trim().slice(0, 40), ratio: Math.round(ratio * 100) / 100, tam })
      if (tam < 12) fallas.push({ el: desc(el), texto: el.textContent.trim().slice(0, 40), tamanioMenorA12: tam })
    }
    for (const input of document.querySelectorAll('input[placeholder], textarea[placeholder]')) {
      const fg = parse(getComputedStyle(input, '::placeholder').color)
      const bg = fondo(input)
      if (!fg) continue
      const l1 = lum(sobre(fg, bg)), l2 = lum(bg)
      const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05)
      revisados++
      if (ratio < 4.5) fallas.push({ el: desc(input), placeholder: input.placeholder, ratio: Math.round(ratio * 100) / 100 })
    }
    out.contraste = { revisados, fallas }
  }
  // Áreas táctiles: en pantallas chicas los controles miden al menos 44×44.
  if (opciones.tactil) {
    const chicos = []
    for (const el of document.querySelectorAll('button, a[href], input:not([type=hidden]), select, [role=tab], summary, [tabindex="0"]')) {
      if (!visible(el) || el.closest('.eo-crumbs, .eo-rowname, p, dd, td > a, li > a.eo-mono, .eo-doc__rids, .eo-mini__list, .eo-evstep__t, .eo-picklist, .eo-tablewrap, .eo-trace__list, label')) continue
      const r = el.getBoundingClientRect()
      if (r.height < 43.5 || r.width < 43.5) chicos.push({ el: desc(el), w: Math.round(r.width), h: Math.round(r.height), texto: (el.textContent ?? '').trim().slice(0, 30) })
    }
    out.tactil = { menoresA44: chicos }
  }
  function visible(el) { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 }
  return out
}
/* eslint-enable no-undef */

// ── Escenarios ─────────────────────────────────────────────────────────────
const escenarios = []
const agregar = (e) => escenarios.push({ anchos: ANCHOS, mundo: {}, ...e })

for (const p of patrones) {
  const ruta = rutaDe(p)
  agregar({ id: `ruta${p === '/' ? '-corridas' : p.replace(/[^a-z0-9]+/gi, '-').replace(/-$/, '')}`, ruta, anchos: [...ANCHOS, 320], contraste: true })
}

// Armazón
agregar({ id: 'shell-colapsado', ruta: '/', anchos: [1280], antes: (ctx) => ctx.addInitScript(() => localStorage.setItem('eovrt-sidebar-collapsed', '1')) })
agregar({ id: 'shell-cajon', ruta: '/', anchos: [390, 768], pasos: async (page, r) => {
  const menu = page.getByRole('button', { name: 'Abrir navegación' })
  await menu.focus()
  await menu.click()
  const dialogo = page.getByRole('dialog', { name: 'Navegación principal' })
  await dialogo.waitFor()
  const dentro = []
  for (let i = 0; i < 25; i++) {
    await page.keyboard.press('Tab')
    // Desde el último control de un diálogo modal el foco puede salir a la
    // interfaz del navegador (activeElement = body): eso no es foco detrás.
    dentro.push(await page.evaluate(() => {
      const a = document.activeElement
      return !a || a === document.body || Boolean(a.closest('dialog[open]'))
    }))
  }
  r.chequeos.cajonContieneFoco = dentro.every(Boolean)
  await page.screenshot({ path: resolve(output, `${r.base}-abierto.png`), fullPage: false })
  await page.keyboard.press('Escape')
  r.chequeos.cajonEscapeCierra = !(await dialogo.isVisible())
  r.chequeos.focoVuelveAlMenu = await page.evaluate(() => document.activeElement?.getAttribute('aria-label') === 'Abrir navegación')
  await menu.click()
  await page.getByRole('dialog').getByRole('link', { name: 'Experimentos' }).click()
  await page.waitForTimeout(400)
  r.chequeos.navegarEnfocaEncabezado = await page.evaluate(() => document.activeElement?.tagName === 'H1')
} })
agregar({ id: 'shell-verificando', ruta: '/compose', anchos: [390, 1280], mundo: { pendientes: [/GET \/api\/target/] } })
agregar({ id: 'shell-error-conexion', ruta: '/compose', anchos: [1280], mundo: { target: 'error' } })
agregar({ id: 'shell-cargando-modelo', ruta: '/compose', anchos: [1280], mundo: { target: 'cargando' } })
agregar({ id: 'shell-motor-caido', ruta: '/compose', anchos: [1280], mundo: { target: 'caido', preflight: 'bloqueado' } })

// Corridas
agregar({ id: 'corridas-grupo-abierto', ruta: '/', anchos: [390, 1280], pasos: async (page) => {
  await page.getByRole('button', { name: /Mostrar las corridas de Línea de base/ }).click()
  await page.getByRole('table', { name: /Corridas de Línea de base/ }).waitFor()
} })
agregar({ id: 'corridas-individual-orden-pagina', ruta: '/', anchos: [390, 768, 1280], pasos: async (page, r) => {
  await page.getByRole('button', { name: /Agrupar por resultado/ }).click()
  await page.getByRole('table', { name: 'Corridas' }).waitFor()
  const boton = page.getByRole('columnheader', { name: /Cuadros\/s/ }).getByRole('button')
  await boton.focus()
  await page.keyboard.press('Enter')
  await page.waitForTimeout(300)
  r.chequeos.ordenPorTeclado = await page.getByRole('columnheader', { name: /Cuadros\/s/ }).getAttribute('aria-sort')
  await page.getByRole('button', { name: 'Siguiente' }).click()
  await page.waitForTimeout(300)
} })
agregar({ id: 'corridas-filtros-busqueda', ruta: '/', anchos: [390, 1280], pasos: async (page) => {
  await page.getByRole('button', { name: /Agrupar por resultado/ }).click()
  await page.getByRole('button', { name: 'Fallidas' }).click()
  await page.getByRole('searchbox').fill('hist')
  await page.waitForTimeout(500)
} })
agregar({ id: 'corridas-borrado', ruta: '/', anchos: [1280], pasos: async (page, r) => {
  await page.getByRole('button', { name: /Agrupar por resultado/ }).click()
  await page.getByRole('button', { name: /Borrar run_20260909_080000_video/ }).click()
  await page.getByRole('button', { name: 'Sí, borrar' }).click()
  await page.waitForTimeout(400)
  r.chequeos.borradoSintetico = r.mundo.log.some((l) => l.method === 'DELETE' && l.pathname.endsWith('run_20260909_080000_video'))
} })
agregar({ id: 'corridas-cargando', ruta: '/', anchos: [390, 1280], mundo: { pendientes: [/GET \/api\/runs\/grupos/] } })
agregar({ id: 'corridas-error', ruta: '/', anchos: [1280], mundo: { fallar: [{ re: /GET \/api\/runs\/grupos/, status: 404 }] } })
agregar({ id: 'corridas-vacio', ruta: '/', anchos: [390, 1280], mundo: { corridas: 'vacio' } })

// Nueva corrida
const elegir = async (page, campo, opcion) => {
  await page.getByRole('button', { name: campo }).click()
  await page.getByRole('option', { name: opcion }).click()
}
agregar({ id: 'compose-completo', ruta: '/compose', anchos: [390, 768, 1280, 1920], pasos: async (page, r) => {
  // El selector se completa con el teclado.
  const sel = page.getByRole('button', { name: 'Conjunto del catálogo' })
  await sel.focus()
  await page.keyboard.press('ArrowDown')
  await page.keyboard.press('ArrowDown')
  await page.keyboard.press('Enter')
  r.chequeos.selectorPorTeclado = (await sel.textContent())?.includes('bench_v3') ?? false
  await elegir(page, 'Conjunto de prompts', 'cr01_cr02_v2_short — congelado')
} })
agregar({ id: 'compose-lanzar-pendiente', ruta: '/compose', anchos: [1280], mundo: { pendientes: [/POST \/api\/runs$/] }, pasos: async (page, r) => {
  await elegir(page, 'Conjunto del catálogo', 'bench_v3')
  await elegir(page, 'Conjunto de prompts', 'cr01_cr02_v2_short — congelado')
  await page.getByRole('button', { name: 'Lanzar corrida' }).click()
  await page.getByRole('button', { name: 'Lanzando corrida…' }).waitFor()
  const post = r.mundo.log.find((l) => l.method === 'POST' && l.pathname === '/api/runs')
  r.chequeos.payloadLanzado = post?.body
} })
agregar({ id: 'compose-error-422', ruta: '/compose', anchos: [1280], mundo: { fallar: [{ re: /POST \/api\/runs$/, status: 422 }] }, pasos: async (page) => {
  await elegir(page, 'Conjunto del catálogo', 'bench_v3')
  await elegir(page, 'Conjunto de prompts', 'cr01_cr02_v2_short — congelado')
  await page.getByRole('button', { name: 'Lanzar corrida' }).click()
  await page.waitForTimeout(400)
} })
agregar({ id: 'compose-rtsp-manifiesto', ruta: '/compose?from=perimetro_lluvia', anchos: [390, 1280] })
agregar({ id: 'compose-modelo-del-manifiesto', ruta: '/compose?from=base_obra', anchos: [1280] })

// Detalle de corrida
const tab = (nombre) => async (page) => { await page.getByRole('tab', { name: new RegExp(`^${nombre}`) }).click(); await page.waitForTimeout(300) }
agregar({ id: 'corrida-traza', ruta: `/runs/${runId}`, anchos: [390, 768, 1280, 1920], pasos: async (page, r) => {
  const lista = page.getByRole('listbox', { name: 'Cuadros de la traza' })
  await lista.focus()
  await page.keyboard.press('ArrowDown')
  await page.keyboard.press('ArrowDown')
  await page.keyboard.press('ArrowDown')
  await page.waitForTimeout(200)
  r.chequeos.cursorSigueALista = await page.evaluate(() => [...document.querySelectorAll('.eo-timeline__cursor')].map((c) => c.style.left))
  // Salto desde la línea de tiempo a la segunda página.
  const control = page.getByRole('slider', { name: /Cuadro elegido/ })
  await control.focus()
  await page.keyboard.press('End')
  await page.waitForTimeout(400)
  r.chequeos.saltoAPagina = await page.evaluate(() => document.querySelector('.eo-trace__list [aria-selected="true"]')?.textContent ?? null)
} })
agregar({ id: 'corrida-preview-ausente', ruta: `/runs/${runId}`, anchos: [390, 1280], pasos: async (page) => {
  await page.getByRole('option', { name: /frame_000003/ }).click()
  await page.waitForTimeout(300)
} })
agregar({ id: 'corrida-ampliar', ruta: `/runs/${runId}`, anchos: [390, 1280], pasos: async (page, r) => {
  await page.getByRole('option', { name: /frame_000001/ }).click()
  await page.getByRole('button', { name: 'Ampliar' }).click()
  await page.getByRole('dialog').waitFor()
  await page.keyboard.press('Escape')
  r.chequeos.ampliacionCierraConEscape = !(await page.getByRole('dialog').isVisible().catch(() => false))
  await page.getByRole('button', { name: 'Ampliar' }).click()
  await page.waitForTimeout(200)
} })
agregar({ id: 'corrida-filtro-alertas', ruta: `/runs/${runId}`, anchos: [1280], pasos: async (page) => { await page.getByLabel('Solo alertas').check(); await page.waitForTimeout(300) } })
agregar({ id: 'corrida-resumen', ruta: `/runs/${runId}`, anchos: [390, 768, 1280], pasos: tab('Resumen') })
agregar({ id: 'corrida-evaluacion', ruta: `/runs/${runId}`, anchos: [390, 1280], pasos: async (page, r) => {
  const traza = page.getByRole('tab', { name: /^Traza/ })
  await traza.focus()
  await page.keyboard.press('ArrowRight')
  await page.keyboard.press('ArrowRight')
  r.chequeos.pestanasConFlechas = await page.evaluate(() => document.activeElement?.textContent)
  await page.waitForTimeout(300)
} })
agregar({ id: 'corrida-evaluacion-no-aplica', ruta: '/runs/run_20260909_080000_video', anchos: [390, 1280], pasos: tab('Evaluación') })
agregar({ id: 'corrida-archivos', ruta: `/runs/${runId}`, anchos: [390, 1280], pasos: tab('Archivos') })
agregar({ id: 'corrida-en-curso', ruta: '/runs/run_20260909_115500_vivo', anchos: [390, 1280] })
agregar({ id: 'corrida-fallida', ruta: '/runs/run_20260909_070000_falla', anchos: [1280] })
agregar({ id: 'corrida-id-largo', ruta: '/runs/run_20260909_063000_detenida_con_un_identificador_muy_largo_para_probar_el_corte', anchos: [320, 390] })

// Experimentos
agregar({ id: 'experimentos-bloqueado', ruta: '/experiments', anchos: [390, 1280], mundo: { preflight: 'bloqueado' } })
agregar({ id: 'experimentos-en-curso', ruta: '/experiments', anchos: [1280], mundo: { experimentoActual: 'exp_20260909_115000_vivo' } })
agregar({ id: 'experimentos-derivar', ruta: '/experiments', anchos: [390, 768, 1280], pasos: async (page) => {
  await page.getByRole('button', { name: 'Partir de este' }).first().click()
  await page.getByLabel(/warmup_frames/).waitFor()
  await page.waitForTimeout(300)
} })
agregar({ id: 'experimentos-nuevo-defaults-fallidos', ruta: '/experiments/new', anchos: [390, 1280], mundo: { fallar: [{ re: /derive-defaults/, status: 500 }] } })
agregar({ id: 'experimentos-nuevo-dirty', ruta: '/experiments/new', anchos: [1280], pasos: async (page) => {
  await page.getByLabel(/nombre nuevo/i).fill('base_obra_v2')
  await page.getByRole('button', { name: 'Cancelar' }).click()
  await page.waitForTimeout(200)
} })
agregar({ id: 'experimento-riesgo-activo', ruta: '/experiments/exp_20260909_115000_vivo', anchos: [390, 1280], mundo: { experimentoActual: 'exp_20260909_115000_vivo' } })
agregar({ id: 'experimento-no-medidas-abiertas', ruta: `/experiments/${experimentId}`, anchos: [390, 1280], pasos: async (page) => {
  await page.getByText(/^Sin medir \(18\)/).click()
  await page.waitForTimeout(200)
} })

// Conjuntos de prompts
agregar({ id: 'prompts-pendiente', ruta: '/prompts', anchos: [390, 1280], pasos: async (page) => { await page.getByRole('button', { name: /eind_v1/ }).click(); await page.waitForTimeout(300) } })
agregar({ id: 'prompts-clases-largas', ruta: '/prompts', anchos: [390, 768, 1280], pasos: async (page) => { await page.getByRole('button', { name: /exploracion_clases_largas/ }).click(); await page.waitForTimeout(300) } })
agregar({ id: 'prompts-estado-desconocido', ruta: '/prompts', anchos: [1280], pasos: async (page) => { await page.getByRole('button', { name: /estado_desconocido/ }).click(); await page.waitForTimeout(300) } })
agregar({ id: 'prompts-editor', ruta: '/prompts', anchos: [390, 768, 1280], pasos: async (page, r) => {
  await page.getByRole('button', { name: /ocho_clases/ }).click()
  await page.getByRole('button', { name: 'Editar clases y frases' }).click()
  await page.getByLabel(/^Descripción/).fill('Ocho clases editadas')
  // El foco no queda debajo del pie fijo.
  const tapados = []
  for (let i = 0; i < 18; i++) {
    await page.keyboard.press('Tab')
    tapados.push(await page.evaluate(() => {
      const a = document.activeElement
      const pie = document.querySelector('.eo-editor__foot')
      // Al salir del último control el foco pasa a body (cromo del navegador): no es un control tapado.
      if (!a || a === document.body || a === document.documentElement || !pie || pie.contains(a)) return false
      const ra = a.getBoundingClientRect(), rp = pie.getBoundingClientRect()
      if (!(ra.bottom > rp.top + 1 && ra.top < rp.bottom)) return false
      return `${a.tagName.toLowerCase()}${a.id ? '#' + a.id : ''} ${Math.round(ra.top)}-${Math.round(ra.bottom)} pie ${Math.round(rp.top)}`
    }))
  }
  r.chequeos.focoTapadoPorPie = tapados.some(Boolean)
  if (r.chequeos.focoTapadoPorPie) r.chequeos.focoTapadoDetalle = tapados.filter(Boolean)
} })
agregar({ id: 'prompts-error-guardado', ruta: '/prompts', anchos: [1280], mundo: { fallar: [{ re: /PUT \/api\/prompt-sets/, status: 422 }] }, pasos: async (page) => {
  await page.getByRole('button', { name: /ocho_clases/ }).click()
  await page.getByRole('button', { name: 'Editar clases y frases' }).click()
  await page.getByRole('button', { name: 'Guardar' }).click()
  await page.waitForTimeout(300)
} })

// Cámaras
agregar({ id: 'camaras-cargando', ruta: '/cameras', anchos: [390, 1280], mundo: { pendientes: [/GET \/api\/cameras$/] } })
agregar({ id: 'camaras-vacio', ruta: '/cameras', anchos: [390, 1280], mundo: { camaras: 'vacio' } })
agregar({ id: 'camaras-error', ruta: '/cameras', anchos: [1280], mundo: { camaras: 'error' } })
agregar({ id: 'camaras-alta', ruta: '/cameras', anchos: [390, 768, 1280], pasos: async (page) => { await page.getByRole('button', { name: 'Agregar cámara' }).click(); await page.waitForTimeout(200) } })
agregar({ id: 'camaras-identidad-a-b', ruta: '/cameras', anchos: [1280], pasos: async (page, r) => {
  await page.locator('.eo-lrow', { hasText: 'Portón norte' }).getByRole('button', { name: 'Editar' }).click()
  await page.getByLabel(/^Nombre/).fill('Portón editado')
  await page.locator('.eo-lrow', { hasText: 'OAK-D laboratorio' }).getByRole('button', { name: 'Editar' }).click()
  r.chequeos.preguntaAntesDeCambiar = await page.getByText(/Hay cambios sin guardar en la cámara/).isVisible()
  await page.getByRole('button', { name: 'Descartar cambios' }).click()
  await page.getByRole('button', { name: 'Guardar' }).click()
  await page.waitForTimeout(300)
  const put = r.mundo.log.find((l) => l.method === 'PUT')
  r.chequeos.putDeB = put ? { path: put.pathname, body: put.body } : null
} })
agregar({ id: 'camaras-plugin-desconocido', ruta: '/cameras', anchos: [390, 1280], pasos: async (page) => {
  await page.locator('.eo-lrow', { hasText: 'plugin que esta consola' }).getByRole('button', { name: 'Editar' }).click()
  await page.waitForTimeout(200)
} })
agregar({ id: 'camaras-preview-detect', ruta: '/cameras', anchos: [390, 1280], ws: 'frames', pasos: async (page) => {
  await page.getByRole('button', { name: 'Con detecciones' }).click()
  await page.getByLabel('Conjunto de prompts').selectOption('ocho_clases')
  await page.waitForTimeout(300)
  await page.locator('.eo-lrow', { hasText: 'Portón norte' }).getByRole('button', { name: 'Probar' }).click()
  await page.waitForTimeout(700)
} })
agregar({ id: 'camaras-preview-raw', ruta: '/cameras', anchos: [1280], ws: 'frames', pasos: async (page) => {
  await page.locator('.eo-lrow', { hasText: 'Portón norte' }).getByRole('button', { name: 'Probar' }).click()
  await page.waitForTimeout(700)
} })
agregar({ id: 'camaras-retomar', ruta: '/cameras', anchos: [1280], mundo: { preview: { status: 'streaming', preview_id: 'pv0', mode: 'raw', error: null } } })
agregar({ id: 'camaras-exclusion-corrida', ruta: '/cameras', anchos: [1280], mundo: { previewBloqueada: true }, pasos: async (page) => {
  await page.locator('.eo-lrow', { hasText: 'Portón norte' }).getByRole('button', { name: 'Probar' }).click()
  await page.waitForTimeout(300)
} })
agregar({ id: 'grabacion-en-curso', ruta: '/cameras', anchos: [390, 1280], mundo: { grabacion: { state: 'recording', basename: 'P1-a-take3', elapsed_ms: 12_400, size_bytes: 2_400_000 } } })
agregar({ id: 'grabacion-iniciando', ruta: '/cameras', anchos: [1280], mundo: { grabacion: { state: 'starting', basename: 'P1-a-take3' } } })

// Clips y recorte
agregar({ id: 'clips-vacio-global', ruta: '/clips', anchos: [390, 1280], antes: null, mundo: {}, interceptarExtra: (mundo) => { mundo.estado.masters = []; mundo.estado.clips = [] } })
agregar({ id: 'clips-recorte-dos-marcas', ruta: '/clips', anchos: [390, 1280], pasos: async (page) => {
  await page.getByRole('button', { name: 'Recortar' }).first().click()
  const video = page.getByTestId('trim-video')
  await video.evaluate((v) => Object.defineProperty(v, 'currentTime', { value: 4.2, writable: true }))
  await page.getByRole('button', { name: 'casco_fuera' }).click()
  await video.evaluate((v) => { v.currentTime = 24.5 })
  await page.getByRole('button', { name: 'casco_puesto' }).click()
  await page.getByLabel('Regenerar').selectOption('a_p1_c01')
} })
agregar({ id: 'clips-recorte-cuatro-marcas', ruta: '/clips', anchos: [390, 1280], pasos: async (page) => {
  await page.getByRole('button', { name: 'Recortar' }).nth(1).click()
  const video = page.getByTestId('trim-video')
  for (const [t, l] of [[3, 'casco_fuera'], [9, 'chaleco_fuera'], [18, 'chaleco_puesto'], [30, 'casco_puesto']]) {
    await video.evaluate((v, x) => Object.defineProperty(v, 'currentTime', { value: x, writable: true, configurable: true }), t)
    await page.getByRole('button', { name: l }).click()
  }
  await page.getByRole('button', { name: 'Generar clip' }).click()
  await page.waitForTimeout(300)
} })
agregar({ id: 'clips-generar-falla', ruta: '/clips', anchos: [1280], mundo: { fallar: [{ re: /POST \/api\/clips/, status: 500 }] }, pasos: async (page) => {
  await page.getByRole('button', { name: 'Recortar' }).first().click()
  const video = page.getByTestId('trim-video')
  await video.evaluate((v) => Object.defineProperty(v, 'currentTime', { value: 4.2, writable: true }))
  await page.getByRole('button', { name: 'casco_fuera' }).click()
  await page.getByRole('button', { name: 'casco_puesto' }).click()
  await page.getByRole('button', { name: 'Generar clip' }).click()
  await page.waitForTimeout(300)
} })

// Comparar
const marcar = (n) => async (page) => {
  const casillas = page.getByRole('checkbox')
  for (let i = 0; i < n; i++) await casillas.nth(i).check()
  await page.waitForTimeout(400)
}
agregar({ id: 'comparar-una', ruta: '/compare', anchos: [390, 1280], pasos: marcar(1) })
agregar({ id: 'comparar-dos', ruta: '/compare', anchos: [390, 768, 1280], pasos: marcar(2) })
agregar({ id: 'comparar-ocho', ruta: '/compare', anchos: [390, 1280, 1920], pasos: async (page, r) => {
  await marcar(8)(page)
  r.chequeos.novenaDeshabilitada = await page.getByRole('checkbox').nth(8).isDisabled()
} })
agregar({ id: 'comparar-pendiente', ruta: '/compare', anchos: [1280], mundo: { pendientes: [/GET \/api\/compare/] }, pasos: marcar(2) })
agregar({ id: 'comparar-error', ruta: '/compare', anchos: [1280], mundo: { fallar: [{ re: /GET \/api\/compare/, status: 500 }] }, pasos: marcar(2) })
agregar({ id: 'comparar-conjuntos-distintos', ruta: '/compare', anchos: [1280], pasos: async (page) => {
  await page.getByRole('checkbox').nth(0).check()
  await page.getByRole('checkbox', { name: 'Banco 9' }).check()
  await page.waitForTimeout(300)
} })

// Catálogo, plataforma, documentación
agregar({ id: 'catalogo-80-clases', ruta: '/catalog', anchos: [390, 1280], pasos: async (page) => { await page.getByRole('button', { name: 'Ver las 80 clases' }).click() } })
agregar({ id: 'catalogo-servicio-caido', ruta: '/catalog', anchos: [1280], mundo: { target: 'error' } })
agregar({ id: 'plataforma-sin-orquestacion', ruta: '/platform', anchos: [390, 1280], mundo: { instancias: '501' } })
agregar({ id: 'documentacion-familia-abierta', ruta: '/documentacion#T1', anchos: [390, 1280] })

// Evidencia
agregar({ id: 'evidencia-ausente', ruta: '/evidencia', anchos: [390, 1280], mundo: { evidencia: 'ausente' } })
agregar({ id: 'evidencia-resultado-pagina-2', ruta: `/evidencia/resultado?${new URLSearchParams({ id: RID, paso: '3' })}`, anchos: [390, 1280], pasos: async (page, r) => {
  await page.getByRole('button', { name: 'Siguiente' }).click()
  await page.waitForTimeout(400)
  r.chequeos.paginaConservaParametros = await page.evaluate(() => location.hash)
} })
agregar({ id: 'evidencia-corrida-archivada', ruta: `/evidencia/run?${new URLSearchParams({ plane: 'control-plane', run_id: 'c1', id: RID })}`, anchos: [390, 1280] })
agregar({ id: 'evidencia-fuente-citada', ruta: '/evidencia', anchos: [390, 1280], pasos: async (page) => { await page.getByRole('button', { name: 'Fuente de la cifra citada' }).first().click() } })

// Movimiento reducido y zoom real
agregar({ id: 'movimiento-reducido', ruta: '/', anchos: [1280], reducedMotion: 'reduce', mundo: { pendientes: [/GET \/api\/runs\/grupos/] }, pasos: async (page, r) => {
  r.chequeos.animacionesAnuladas = await page.evaluate(() => [...document.querySelectorAll('.eo-skel__line, .eo-badge__pulse')]
    .every((el) => parseFloat(getComputedStyle(el).animationDuration) <= 0.001))
} })
for (const ruta of ['/', '/compose', `/runs/${runId}`, '/experiments', '/prompts', '/cameras', '/compare', `/evidencia/resultado?${new URLSearchParams({ id: RID })}`]) {
  agregar({ id: `zoom200${ruta.replace(/[^a-z0-9]+/gi, '-').slice(0, 30)}`, ruta, anchos: [1280], zoom: 2 })
}

// ── Ejecución ──────────────────────────────────────────────────────────────
const solos = values.solo ? values.solo.split(',') : null
const filtrar = solos ? escenarios.filter((e) => solos.some((x) => e.id === x || (x.endsWith('*') && e.id.startsWith(x.slice(0, -1))))) : escenarios
const browser = await chromium.launch(lanzar)
const version = browser.version()
const resultados = []

async function nuevoContexto(e, ancho) {
  if (e.zoom) {
    // Zoom REAL del navegador: la preferencia de zoom por defecto del perfil,
    // no `deviceScaleFactor` ni `zoom` de CSS.
    const dir = await mkdtemp(join(tmpdir(), 'eo-zoom-'))
    await mkdir(join(dir, 'Default'), { recursive: true })
    await writeFile(join(dir, 'Default', 'Preferences'), JSON.stringify({ partition: { default_zoom_level: { x: Math.log(e.zoom) / Math.log(1.2) } } }))
    const ctx = await chromium.launchPersistentContext(dir, { ...lanzar, viewport: null, args: [`--window-size=${ancho},${ALTO}`], locale: 'es-AR', timezoneId: 'UTC' })
    return { ctx, cerrar: async () => { await ctx.close(); await rm(dir, { recursive: true, force: true }) } }
  }
  const ctx = await browser.newContext({ viewport: { width: ancho, height: ALTO }, deviceScaleFactor: 1, locale: 'es-AR', timezoneId: 'UTC', reducedMotion: e.reducedMotion ?? 'no-preference' })
  return { ctx, cerrar: () => ctx.close() }
}

function frameDePreview(seq) {
  const header = Buffer.from(JSON.stringify({ seq, ts: seq, width: 640, height: 360, mode: 'detect', detections: [{ label: 'person', score: 0.86, bbox_norm_xyxy: [0.2, 0.2, 0.5, 0.95] }] }))
  const len = Buffer.alloc(4)
  len.writeUInt32BE(header.length)
  return Buffer.concat([len, header, PNG])
}

for (const e of filtrar) {
  for (const ancho of e.anchos) {
    const base = `${e.id}-${ancho}`
    const mundo = crearMundo(e.mundo)
    e.interceptarExtra?.(mundo)
    const r = { escenario: e.id, ruta: e.ruta, viewportSolicitado: { width: ancho, height: ALTO }, zoom: e.zoom ?? 1, base, chequeos: {}, errores: [], peticiones: 0, mundo }
    const { ctx, cerrar } = await nuevoContexto(e, ancho)
    let enVuelo = 0
    try {
      if (e.antes) await e.antes(ctx)
      await ctx.route((url) => new URL(url).pathname.startsWith('/api/'), async (route) => {
        const req = route.request()
        const url = new URL(req.url())
        let body = null
        try { body = req.postData() ? JSON.parse(req.postData()) : null } catch { body = req.postData() }
        r.peticiones++
        const res = mundo.responder({ method: req.method(), pathname: url.pathname, query: url.searchParams, body })
        if (!res) {
          r.errores.push(`Sin fixture: ${req.method()} ${url.pathname}${url.search}`)
          await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'Petición no declarada en el escenario' }) })
          return
        }
        if (res.pendiente) return // queda sin respuesta: es el estado que se quiere mirar
        enVuelo++
        try {
          if (res.binary) await route.fulfill({ status: res.status, contentType: res.contentType, body: res.binary })
          else await route.fulfill({ status: res.status, contentType: 'application/json', headers: res.headers, body: res.body == null ? '' : JSON.stringify(res.body) })
        } finally { enVuelo-- }
      })
      await ctx.routeWebSocket((url) => new URL(url).pathname.startsWith('/api/'), (ws) => {
        const path = new URL(ws.url()).pathname
        if (path !== '/api/preview/stream') { r.errores.push(`WebSocket no declarado: ${path}`); ws.close(); return }
        if (e.ws === 'frames') {
          let seq = 0
          const id = setInterval(() => { try { ws.send(frameDePreview(++seq)) } catch { clearInterval(id) } }, 150)
          ws.onClose(() => clearInterval(id))
        }
      })
      const page = ctx.pages()[0] ?? await ctx.newPage()
      page.on('pageerror', (error) => r.errores.push(`pageerror: ${error.message}`))
      page.on('console', (msg) => {
        if (msg.type() !== 'error') return
        const t = msg.text()
        // Las respuestas de error que el escenario declara son esperadas.
        if (/Failed to load resource/.test(t)) return
        r.errores.push(`console: ${t.slice(0, 200)}`)
      })
      await page.clock.setFixedTime(new Date(FECHA))
      await page.goto(`${BASE}/#${e.ruta}`)
      await page.getByRole('heading', { level: 1 }).first().waitFor({ timeout: 10_000 })
      const quieto = async () => {
        for (let i = 0; i < 40; i++) { await page.waitForTimeout(100); if (enVuelo === 0) break }
        await page.waitForTimeout(250)
      }
      await quieto()
      if (e.pasos) { await e.pasos(page, r); await quieto() }
      const medidas = await page.evaluate(medirEnPagina, { contraste: ancho === 1280 || ancho === 390, tactil: ancho < 768 })
      Object.assign(r, medidas)
      // Las barras fijas se dibujan donde quedó el scroll: se captura desde arriba
      // para que todas las capturas sean comparables (las medidas ya se tomaron).
      await page.evaluate(() => window.scrollTo(0, 0))
      const png = `${base}.png`
      const bytes = await page.screenshot({ path: resolve(output, png), fullPage: true, animations: 'disabled', caret: 'hide' })
      r.png = png
      r.sha256 = createHash('sha256').update(bytes).digest('hex')
      if (medidas.desbordeDocumento) r.errores.push(`Desborde del documento: scrollWidth ${medidas.viewport.scrollWidth} > clientWidth ${medidas.viewport.clientWidth} — ${medidas.causantes.map((c) => `${c.el} «${c.texto}»`).join('; ')}`)
      if (medidas.alturaSobrante > 2) r.errores.push(`Altura fantasma de ${medidas.alturaSobrante} px — ${(medidas.causantesAltura ?? []).map((c) => `${c.el} en ${c.padre}`).join('; ')}`)
      if (medidas.desbordesNoPrevistos.length) r.errores.push(`Desborde local no previsto: ${medidas.desbordesNoPrevistos.map((d) => d.el).join(', ')}`)
      if (medidas.timeline && (!medidas.timeline.alineados || medidas.timeline.ejeAlineado === false)) r.errores.push('Línea de tiempo desalineada')
      for (const [k, v] of Object.entries(r.chequeos)) if (k in ESPERADO && v !== ESPERADO[k]) r.errores.push(`Chequeo ${k}: ${JSON.stringify(v)}`)
    } catch (error) {
      r.errores.push(`excepción: ${error.message.split('\n')[0]}`)
    } finally {
      await cerrar()
    }
    r.log = mundo.log.filter((l) => l.method !== 'GET').map((l) => ({ method: l.method, pathname: l.pathname, body: l.body }))
    delete r.mundo
    resultados.push(r)
    console.log(`${base}: ${r.errores.length ? `${r.errores.length} errores — ${r.errores[0]}` : 'ok'}`)
  }
}

await browser.close()
servidor.close()
const resumen = {
  generado: new Date().toISOString(), modo: 'synthetic-http-ws-fixtures', fechaFija: FECHA, navegador: version,
  escenarios: new Set(resultados.map((r) => r.escenario)).size, capturas: resultados.length,
  conErrores: resultados.filter((r) => r.errores.length).map((r) => ({ base: r.base, errores: r.errores })),
  desbordesDocumento: resultados.filter((r) => r.desbordeDocumento).map((r) => r.base),
  contraste: resultados.filter((r) => r.contraste?.fallas.length).map((r) => ({ base: r.base, fallas: r.contraste.fallas })),
  tactil: resultados.filter((r) => r.tactil?.menoresA44.length).map((r) => ({ base: r.base, controles: r.tactil.menoresA44 })),
  ejesFuera: resultados.filter((r) => r.eje?.fuera.length).map((r) => ({ base: r.base, fuera: r.eje.fuera })),
}
await writeFile(resolve(output, 'manifest.json'), JSON.stringify({ resumen, resultados }, null, 2) + '\n')
console.log(JSON.stringify({ capturas: resumen.capturas, conErrores: resumen.conErrores.length, desbordes: resumen.desbordesDocumento.length, contraste: resumen.contraste.length, tactil: resumen.tactil.length, ejes: resumen.ejesFuera.length }))
if (resumen.conErrores.length) process.exitCode = 1
