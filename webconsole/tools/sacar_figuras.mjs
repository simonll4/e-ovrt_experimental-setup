#!/usr/bin/env node
// Saca las diez figuras del informe (plan de la consola de evidencia, §8) de una consola que ya está corriendo.
// Lee `GET /api/figuras` —que a su vez lee results/evidence-vista/figuras.yaml— y, para cada figura con fuente:
//
//   - un gráfico: lo captura de la página de su pregunta (`/preguntas/<id>`, el elemento `[data-figura=<id>]`);
//   - una pantalla: captura ese elemento de esa pantalla;
//   - un archivo: lo copia tal cual o, con `recorte_arriba`, sin esa franja de arriba (píxel a píxel).
//
// Cada una va al destino que dice la consola, y a ninguna otra parte: la carpeta pública
// `results/gen2/<prueba>/capturas/` (solo gráficos y pantallas de texto: si el elemento capturado tiene una
// imagen, un video o un lienzo, no se guarda) o la privada `defensa/capturas/figuras/` (personas y cuadros de
// terceros; no va a git). Se sacan en el tema claro. Las pendientes se listan con su motivo y no se generan.
//
//   node webconsole/tools/sacar_figuras.mjs [--base http://localhost:8090] [--solo id,id] [--escala 2]
//
// Playwright, como en `mirar_pantallas.mjs`: `--playwright-module`, `webconsole/tools/.capture-runtime` o NODE_PATH.
import { existsSync } from 'node:fs'
import { copyFile, mkdir, readFile } from 'node:fs/promises'
import { dirname, join, relative, resolve, sep } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { parseArgs } from 'node:util'

const aqui = dirname(fileURLToPath(import.meta.url))
const repo = resolve(aqui, '..', '..')
const { values: o } = parseArgs({
  options: {
    base: { type: 'string', default: 'http://localhost:8090' }, solo: { type: 'string' },
    ancho: { type: 'string', default: '1280' }, alto: { type: 'string', default: '900' },
    escala: { type: 'string', default: '2' }, espera: { type: 'string', default: '2500' },
    'playwright-module': { type: 'string' }, chromium: { type: 'string' },
  },
})

const PUBLICA = /^results\/gen2\/[A-Z]+-\d+\/capturas\/figura-\d{2}-[a-z0-9-]+\.png$/
const PRIVADA = /^defensa\/capturas\/figuras\/figura-\d{2}-[a-z0-9-]+\.png$/

/** El destino, ya resuelto, si es uno de los permitidos; si no, null. */
function destinoPermitido(f) {
  const d = f.destino ?? ''
  const permitido = f.privada ? PRIVADA.test(d) : PUBLICA.test(d)
  if (!permitido) return null
  const ruta = resolve(repo, d)
  return relative(repo, ruta).split(sep).join('/') === d ? ruta : null
}

async function cargarPlaywright() {
  const candidatos = [
    o['playwright-module'],
    join(aqui, '.capture-runtime', 'node_modules', 'playwright', 'index.mjs'),
    ...(process.env.NODE_PATH ?? '').split(':').filter(Boolean).map((p) => join(p, 'playwright', 'index.mjs')),
  ].filter(Boolean)
  for (const c of candidatos) if (existsSync(c)) return import(pathToFileURL(resolve(c)).href)
  throw new Error('no encuentro Playwright: instalalo en webconsole/tools/.capture-runtime o pasá --playwright-module')
}

const respuesta = await fetch(`${o.base}/api/figuras`).catch((e) => {
  console.error(`no pude leer ${o.base}/api/figuras: ${e.message}`)
  process.exit(2)
})
if (!respuesta.ok) {
  console.error(`${o.base}/api/figuras respondió ${respuesta.status}`)
  process.exit(2)
}
const vista = await respuesta.json()
if (vista.errores?.length) {
  console.error(`las cifras de los gráficos no resuelven:\n  ${vista.errores.join('\n  ')}`)
  process.exit(2)
}
const solo = o.solo ? new Set(o.solo.split(',').map((s) => s.trim())) : null
const figuras = vista.figuras.filter((f) => !solo || solo.has(f.id))

let contexto = null
let crudo = null
let navegador = null
async function lanzar() {
  if (!navegador) {
    const { chromium } = await cargarPlaywright()
    navegador = await chromium.launch(o.chromium ? { executablePath: o.chromium } : {})
  }
  return navegador
}

/** Copia una imagen sin las `arriba` filas de arriba: se dibuja a escala 1 y se captura el resto. */
async function copiarRecortada(origen, destino, arriba) {
  if (!crudo) crudo = await (await lanzar()).newContext({ deviceScaleFactor: 1 })
  const p = await crudo.newPage()
  try {
    const datos = (await readFile(origen)).toString('base64')
    await p.setContent(`<body style="margin:0"><img id="i" style="display:block" src="data:image/png;base64,${datos}"></body>`)
    const { w, h } = await p.$eval('#i', (img) => img.decode().then(() => ({ w: img.naturalWidth, h: img.naturalHeight })))
    if (!(arriba > 0 && arriba < h)) throw new Error(`recorte_arriba fuera de la imagen (${h} px de alto)`)
    await p.setViewportSize({ width: w, height: h })
    await p.screenshot({ path: destino, clip: { x: 0, y: arriba, width: w, height: h - arriba } })
  } finally {
    await p.close()
  }
}

async function pagina() {
  if (!contexto) {
    contexto = await (await lanzar()).newContext({
      viewport: { width: Number(o.ancho), height: Number(o.alto) }, deviceScaleFactor: Number(o.escala),
      locale: 'es-AR', colorScheme: 'light',
    })
    // Las figuras van en el tema claro, como lo dejaría elegido el selector (src/tema.ts).
    await contexto.addInitScript(() => {
      try { localStorage.setItem('eovrt-tema', 'claro') } catch { /* sin almacenamiento: rige el claro */ }
    })
  }
  return contexto.newPage()
}

async function capturar(f, ruta, selector, destino) {
  const p = await pagina()
  try {
    await p.goto(`${o.base}/#${ruta}`, { waitUntil: 'domcontentloaded', timeout: 30000 })
    const el = p.locator(selector).first()
    await el.waitFor({ state: 'visible', timeout: 20000 })
    await p.waitForTimeout(Number(o.espera))
    // Las imágenes del elemento, cargadas del todo antes de capturar.
    await el.evaluate((nodo) => Promise.all([...nodo.querySelectorAll('img')].map((img) => (img.complete
      ? null : new Promise((listo) => { img.onload = listo; img.onerror = listo })))))
    if (!f.privada) {
      const conImagen = await el.evaluate((nodo) => nodo.querySelectorAll('img, video, canvas, picture').length)
      if (conImagen > 0) throw new Error('es pública y el elemento tiene una imagen o un video: no se guarda')
    }
    await el.scrollIntoViewIfNeeded()
    await el.screenshot({ path: destino, animations: 'disabled' })
  } finally {
    await p.close()
  }
}

let fallas = 0
for (const f of figuras) {
  const n = String(f.numero).padStart(2, '0')
  if (f.pendiente) {
    console.log(`${n} ${f.id}: pendiente — ${f.pendiente}`)
    continue
  }
  const destino = destinoPermitido(f)
  if (!destino) {
    console.log(`${n} ${f.id}: FALLA — el destino «${f.destino}» no es una de las dos carpetas de figuras`)
    fallas++
    continue
  }
  await mkdir(dirname(destino), { recursive: true })
  try {
    if (f.grafico) {
      await capturar(f, `/preguntas/${encodeURIComponent(f.preguntas[0])}`, `[data-figura='${f.id}']`, destino)
    } else if (f.fuente.pantalla) {
      await capturar(f, f.fuente.pantalla, f.fuente.selector, destino)
    } else if (f.fuente.archivo) {
      if (!f.privada) throw new Error('un archivo copiado va solo a la carpeta privada')
      const origen = resolve(repo, f.fuente.archivo)
      if (relative(repo, origen).startsWith('..')) throw new Error('el archivo de origen está fuera del repositorio')
      if (f.fuente.recorte_arriba) await copiarRecortada(origen, destino, Number(f.fuente.recorte_arriba))
      else await copyFile(origen, destino)
    } else {
      throw new Error('no tiene fuente')
    }
    console.log(`${n} ${f.id} → ${f.destino}`)
  } catch (e) {
    console.log(`${n} ${f.id}: FALLA — ${String(e.message ?? e).split('\n')[0]}`)
    fallas++
  }
}
await navegador?.close()
process.exit(fallas ? 1 : 0)
