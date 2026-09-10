#!/usr/bin/env node
// npm install --prefix webconsole/tools/.capture-runtime playwright@1.57.0
// webconsole/tools/.capture-runtime/node_modules/.bin/playwright install chromium
// node webconsole/tools/capture_console.mjs --synthetic --out tools/captures/antes
// Para un BFF con datos sembrados: --base-url http://127.0.0.1:8090
// --run-id <id> --experiment-id <id> (sin --synthetic).
import { createHash } from 'node:crypto'
import { spawn } from 'node:child_process'
import { once } from 'node:events'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { createServer } from 'node:net'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { parseArgs } from 'node:util'
import { experimentId, fixture, runId } from './capture_fixtures.mjs'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const { values } = parseArgs({ options: {
  synthetic: { type: 'boolean', default: false },
  out: { type: 'string', default: 'tools/captures/current' },
  'base-url': { type: 'string' },
  'run-id': { type: 'string' },
  'experiment-id': { type: 'string' },
  'playwright-module': { type: 'string', default: resolve(root, 'tools/.capture-runtime/node_modules/playwright/index.mjs') },
  chromium: { type: 'string' },
} })
if (!values.synthetic && (!values['base-url'] || !values['run-id'] || !values['experiment-id'])) {
  throw Error('Usá --synthetic, o --base-url junto con --run-id y --experiment-id de los datos sembrados.')
}
const output = resolve(root, values.out)
await mkdir(output, { recursive: true })
const source = await readFile(resolve(root, 'frontend/src/App.tsx'), 'utf8')
const routes = [...source.matchAll(/<Route\s+path="([^"]+)"/g)].map(m => m[1])
const { chromium } = await import(pathToFileURL(resolve(values['playwright-module'])).href)
let server, browser
let serverLog = ''
try {
  let base = values['base-url']
  if (!base) {
    const socket = createServer()
    socket.listen(0, '127.0.0.1')
    await once(socket, 'listening')
    const port = socket.address().port
    await new Promise(resolve => socket.close(resolve))
    server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', String(port), '--strictPort'], {
      cwd: resolve(root, 'frontend'), stdio: ['ignore', 'pipe', 'pipe'],
    })
    server.stdout.on('data', data => { serverLog += data })
    server.stderr.on('data', data => { serverLog += data })
    base = `http://127.0.0.1:${port}`
    let ready = false
    for (let i = 0; i < 100; i++) {
      try { if ((await fetch(base)).ok) { ready = true; break } } catch { /* arrancando */ }
      if (server.exitCode !== null) break
      await new Promise(resolve => setTimeout(resolve, 100))
    }
    if (!ready) throw Error(`Vite no arrancó: ${serverLog}`)
  }
  browser = await chromium.launch({ headless: true, ...(values.chromium ? { executablePath: values.chromium } : {}) })
  const results = []
  for (const [i, pattern] of routes.entries()) {
    const route = pattern === '*' ? '/ruta-inexistente' : pattern.replace(':id', encodeURIComponent(
      pattern.startsWith('/runs/') ? (values['run-id'] ?? runId) : (values['experiment-id'] ?? experimentId),
    ))
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'es-AR', timezoneId: 'UTC', colorScheme: 'light' })
    const page = await context.newPage()
    const errors = []
    page.on('pageerror', error => {
      errors.push(error.message)
      console.error(`${route}: ${error.message}`)
    })
    await page.clock.setFixedTime(new Date('2026-09-09T12:00:00Z'))
    if (values.synthetic) await page.route(url => url.pathname.startsWith('/api/'), async request => {
      const response = fixture(request.request().url(), request.request().method())
      if (!response) errors.push(`Sin fixture: ${request.request().method()} ${new URL(request.request().url()).pathname}`)
      await request.fulfill({
        status: response?.status ?? 500, contentType: 'application/json',
        body: JSON.stringify(response?.body ?? { detail: 'Petición inesperada' }),
        headers: { 'X-Total-Count': String(Array.isArray(response?.body) ? response.body.length : 0) },
      })
    })
    await page.goto(`${base.replace(/\/$/, '')}/#${route}`, { waitUntil: 'networkidle' })
    await page.evaluate(() => document.fonts.ready)
    try {
      await page.getByRole('heading', { level: 1 }).waitFor({ timeout: 10_000 })
    } catch {
      errors.push(`No apareció el título de la página: ${await page.locator('body').innerText()}`)
    }
    const png = `${String(i).padStart(2, '0')}-${pattern.replace(/[^a-z0-9]/gi, '-').replace(/^-|-$/g, '') || 'corridas'}.png`
    const bytes = await page.screenshot({ path: resolve(output, png), fullPage: true, animations: 'disabled', caret: 'hide' })
    results.push({ route, png, sha256: createHash('sha256').update(bytes).digest('hex'), errors })
    await context.close()
    console.log(`${route} -> ${png}${errors.length ? ` (${errors.length} errores)` : ''}`)
  }
  await writeFile(resolve(output, 'manifest.json'), JSON.stringify({
    mode: values.synthetic ? 'synthetic-http-fixtures' : 'seeded-bff',
    viewport: { width: 1440, height: 1000 }, fixedTime: '2026-09-09T12:00:00Z',
    browser: browser.version(), results,
  }, null, 2) + '\n')
  if (results.some(r => r.errors.length)) process.exitCode = 1
} finally {
  await browser?.close()
  if (server && server.exitCode === null) {
    const exited = once(server, 'exit')
    server.kill('SIGTERM')
    await exited
  }
}
