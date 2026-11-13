#!/usr/bin/env node
// Mira la consola como la ve una persona: captura pantallas contra una consola que ya está corriendo y dice, para
// cada una, qué encabezados mostró y qué errores dejó en la consola del navegador. Sirve para revisar un cambio con
// datos reales antes de darlo por bueno. No inventa datos ni intercepta nada (para eso está `capture_console.mjs`).
//
//   node webconsole/tools/mirar_pantallas.mjs --out <carpeta> [--base http://localhost:5173] \
//        [--completa] [--tarjeta "Las tomas"] [--tecla e] <ruta>[=<nombre>] ...
//
//   --completa   la página entera, no solo lo que entra en la ventana
//   --tarjeta    captura solo la tarjeta que tiene ese título
//   --tecla      aprieta esa tecla antes de capturar (por ejemplo `e` abre la capa de evidencia de una toma)
//   --dialogo    captura solo el diálogo abierto (con --tecla e, la capa de evidencia: es texto, sin video)
//
// Las rutas son las de la consola, sin el `#`: `/`, `/resultados/ALR-13`, `/demo/resultado/<sesión>`.
//
// Playwright no es dependencia del proyecto. Se toma, en este orden, de `--playwright-module`, de
// `webconsole/tools/.capture-runtime` (npm install --prefix webconsole/tools/.capture-runtime playwright) o de la
// variable NODE_PATH. El navegador: `--chromium <ruta>` o el que Playwright tenga instalado.
import { existsSync } from 'node:fs'
import { mkdir } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { parseArgs } from 'node:util'

const aqui = dirname(fileURLToPath(import.meta.url))
const { values: o, positionals: rutas } = parseArgs({
  allowPositionals: true,
  options: {
    out: { type: 'string' }, base: { type: 'string', default: 'http://localhost:5173' },
    completa: { type: 'boolean', default: false }, tarjeta: { type: 'string' }, tecla: { type: 'string' },
    dialogo: { type: 'boolean', default: false }, ancho: { type: 'string', default: '1440' },
    alto: { type: 'string', default: '900' }, espera: { type: 'string', default: '2500' },
    'playwright-module': { type: 'string' }, chromium: { type: 'string' },
  },
})
if (!o.out || rutas.length === 0) {
  console.error('uso: mirar_pantallas.mjs --out <carpeta> <ruta>[=<nombre>] ...   (ver el encabezado del archivo)')
  process.exit(2)
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

const { chromium } = await cargarPlaywright()
await mkdir(o.out, { recursive: true })
const navegador = await chromium.launch(o.chromium ? { executablePath: o.chromium } : {})
const contexto = await navegador.newContext({
  viewport: { width: Number(o.ancho), height: Number(o.alto) }, deviceScaleFactor: 1, locale: 'es-AR',
})
let fallas = 0
for (const item of rutas) {
  const [ruta, nombre] = item.split('=')
  const pagina = await contexto.newPage()
  const errores = []
  pagina.on('console', (m) => { if (m.type() === 'error') errores.push(m.text().slice(0, 160)) })
  pagina.on('pageerror', (e) => errores.push(`pageerror: ${String(e).slice(0, 160)}`))
  // La consola sondea a los servicios sin parar: no hay «red en reposo» que esperar.
  await pagina.goto(`${o.base}/#${ruta}`, { waitUntil: 'domcontentloaded', timeout: 30000 })
    .catch((e) => errores.push(`goto: ${e.message.slice(0, 120)}`))
  await pagina.waitForTimeout(Number(o.espera))
  if (o.tecla) {
    await pagina.keyboard.press(o.tecla)
    await pagina.waitForTimeout(1500)
  }
  const archivo = join(o.out, `${nombre || ruta.replace(/[^a-zA-Z0-9]+/g, '_').replace(/^_|_$/g, '') || 'inicio'}.png`)
  try {
    if (o.dialogo) {
      await pagina.getByRole('dialog').first().screenshot({ path: archivo })
    } else if (o.tarjeta) {
      const tarjeta = pagina.locator('section, article, div')
        .filter({ has: pagina.getByRole('heading', { name: o.tarjeta, exact: true }) }).last()
      await tarjeta.scrollIntoViewIfNeeded()
      await tarjeta.screenshot({ path: archivo })
    } else {
      await pagina.screenshot({ path: archivo, fullPage: o.completa })
    }
  } catch (e) {
    errores.push(`captura: ${e.message.slice(0, 160)}`)
    fallas += 1
  }
  const info = await pagina.evaluate(() => ({
    encabezados: Array.from(document.querySelectorAll('h1, h2')).map((e) => e.innerText.trim().replace(/\s+/g, ' ')).filter(Boolean).slice(0, 14),
    alto: document.documentElement.scrollHeight,
    caracteres: document.body.innerText.length,
    medios: document.querySelectorAll('img, video').length,
  }))
  console.log(`\n== ${ruta} -> ${archivo}`)
  console.log(`   ${info.alto} px de alto · ${info.caracteres} caracteres · ${info.medios} imágenes o videos`)
  console.log(`   encabezados: ${info.encabezados.join(' | ').slice(0, 500)}`)
  if (errores.length) console.log(`   errores (${errores.length}): ${errores.slice(0, 4).join(' || ')}`)
  await pagina.close()
}
await navegador.close()
process.exit(fallas ? 1 : 0)
