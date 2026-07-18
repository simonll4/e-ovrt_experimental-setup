> **SUPERSEDED por `2026-07-03-webconsole-mvp.md` — no refleja lo implementado.** Este plan
> es hermano de `2026-07-01-webconsole-backend.md` (paquete `eovrt_console` vs. el real
> `eovrt_webconsole`; BFF síncrono vs. el async implementado) y describe pantallas/rutas que
> no coinciden con las del MVP ejecutado. Se conserva solo como referencia histórica del
> diseño inicial.

# Webconsole Frontend (SPA) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir la SPA (`webconsole/frontend`) de la consola web: React + Vite + TypeScript, cliente del BFF planificado en `2026-07-01-webconsole-backend.md`. Cuatro pantallas — lista de corridas, compositor de corrida nueva, detalle en vivo, catálogos — sin ejecutar nada del lado del cliente más que llamar a la API del BFF.

**Architecture:** `fetch` nativo envuelto en un cliente HTTP mínimo (`api/client.ts`) y `WebSocket` nativo del navegador para telemetría en vivo — sin librería de data-fetching ni de estado global (React Query, Redux, etc.): el volumen de datos y la cantidad de pantallas del MVP no lo justifican, y mantiene el stack liviano. Cada página hace sus propias llamadas vía hooks pequeños (`useEffect`/`useState`) y funciones tipadas de `api/runs.ts`. El único hook no trivial es `useRunStream`, que envuelve el WebSocket.

**Tech Stack:** React 18, TypeScript, Vite, `react-router-dom`, Vitest + `@testing-library/react` (jsdom), sin CSS framework (estilos mínimos inline, fuera de alcance del MVP).

## Global Constraints

- Sin librería de data-fetching ni de estado global — `fetch`/`WebSocket` nativos.
- La SPA es **puro cliente HTTP/WS del BFF** (`webconsole/backend`, plan hermano) — nunca llama directo al servicio media-plane ni conoce su URL.
- El compositor (`NewRunPage`) en Fase 1 solo permite lanzar corridas con `image_folder`/`video_file` (fuentes bounded, con `path` inline) — `rtsp`/`oak_d` se muestran en el selector pero deshabilitados, con badge de "no disponible en el compositor todavía" — consistente con la decisión "datasets/video ahora, vivo como plugin-slot" del Spec B.
- El compositor no ofrece selección de dataset por `ref` en Fase 1 (solo `path` inline) — el backend ya soporta `ref`, es una simplificación de UI, no una limitación de API.
- Todos los tests mockean `fetch`/`WebSocket`/el módulo `api/runs.ts` — ninguno requiere el BFF ni el servicio media-plane corriendo de verdad.
- `npm run build` (`tsc -b && vite build`) debe compilar sin errores de tipos al cierre del plan.

---

## File Structure

```
webconsole/
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── App.test.tsx
        ├── api/
        │   ├── types.ts
        │   ├── client.ts
        │   ├── client.test.ts
        │   ├── runs.ts
        │   └── runs.test.ts
        ├── hooks/
        │   ├── useRunStream.ts
        │   └── useRunStream.test.ts
        ├── pages/
        │   ├── RunsListPage.tsx
        │   ├── RunsListPage.test.tsx
        │   ├── NewRunPage.tsx
        │   ├── NewRunPage.test.tsx
        │   ├── RunDetailPage.tsx
        │   ├── RunDetailPage.test.tsx
        │   ├── CatalogPage.tsx
        │   └── CatalogPage.test.tsx
        └── test/
            ├── setup.ts
            └── fakeWebSocket.ts
```

---

### Task 1: Bootstrap del proyecto Vite + React + TS + Vitest

**Files:**
- Create: `webconsole/frontend/package.json`
- Create: `webconsole/frontend/tsconfig.json`
- Create: `webconsole/frontend/vite.config.ts`
- Create: `webconsole/frontend/index.html`
- Create: `webconsole/frontend/src/main.tsx`
- Create: `webconsole/frontend/src/App.tsx`
- Create: `webconsole/frontend/src/test/setup.ts`
- Test: Create `webconsole/frontend/src/App.test.tsx`

**Interfaces:**
- Produces: `App` (componente raíz, placeholder mínimo en este task — se completa en Task 9).

- [ ] **Step 1: Crear `package.json`**

Create `webconsole/frontend/package.json`:

```json
{
  "name": "eovrt-console-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "test": "vitest run",
    "lint": "eslint ."
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.8",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.5.2",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "eslint": "^9.9.0",
    "jsdom": "^25.0.0",
    "typescript": "^5.5.4",
    "vite": "^5.4.1",
    "vitest": "^2.0.5"
  }
}
```

- [ ] **Step 2: Crear `tsconfig.json`**

Create `webconsole/frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
```

- [ ] **Step 3: Crear `vite.config.ts`**

Create `webconsole/frontend/vite.config.ts`:

```typescript
/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
  },
});
```

- [ ] **Step 4: Crear `index.html` y `main.tsx`**

Create `webconsole/frontend/index.html`:

```html
<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <title>E-OVRT Webconsole</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create `webconsole/frontend/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

Create `webconsole/frontend/src/test/setup.ts`:

```typescript
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

// `test.globals` no está activado (los tests importan describe/it/expect
// explícitamente) — el auto-cleanup de @testing-library/react depende de
// detectar `afterEach` como global, así que se registra a mano acá para que
// corra antes de cada test de cualquier archivo (setupFiles se ejecuta por
// archivo de test) y no queden nodos del DOM de un test filtrándose al siguiente.
afterEach(() => {
  cleanup();
});
```

- [ ] **Step 5: Escribir el test que falla**

Create `webconsole/frontend/src/App.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { App } from "./App";

describe("App", () => {
  it("renders the console title", () => {
    render(<App />);
    expect(screen.getByText("E-OVRT Webconsole")).toBeInTheDocument();
  });
});
```

- [ ] **Step 6: Instalar dependencias y correr el test (debe fallar)**

Run:
```bash
cd webconsole/frontend
npm install
npm run test
```
Expected: falla porque `./App` no existe todavía (`Cannot find module './App'`).

- [ ] **Step 7: Implementar el placeholder mínimo**

Create `webconsole/frontend/src/App.tsx`:

```tsx
export function App() {
  return <h1>E-OVRT Webconsole</h1>;
}
```

- [ ] **Step 8: Correr el test y verificar que pasa**

Run: `npm run test`
Expected: 1 passed

- [ ] **Step 9: Commit**

```bash
git add webconsole/frontend
git commit -m "chore(webconsole-frontend): bootstrap Vite + React + TS + Vitest"
```

---

### Task 2: Cliente HTTP mínimo (`api/client.ts`)

**Files:**
- Create: `webconsole/frontend/src/api/client.ts`
- Test: Create `webconsole/frontend/src/api/client.test.ts`

**Interfaces:**
- Produces: `ApiError` (clase: `status: number`, `detail: unknown`), `apiFetch<T>(path: string, options?: RequestInit) -> Promise<T>`, `wsUrl(path: string) -> string`.

- [ ] **Step 1: Escribir el test que falla**

Create `webconsole/frontend/src/api/client.test.ts`:

```typescript
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiFetch, wsUrl } from "./client";

function mockFetch(body: unknown, status = 200): void {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      json: async () => body,
    } as Response)
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("apiFetch", () => {
  it("returns parsed JSON on success", async () => {
    mockFetch({ hello: "world" });
    const result = await apiFetch<{ hello: string }>("/api/whatever");
    expect(result).toEqual({ hello: "world" });
  });

  it("sends JSON content-type header and body", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({}),
    } as Response);
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/api/runs", { method: "POST", body: JSON.stringify({ a: 1 }) });

    const [, options] = fetchMock.mock.calls[0];
    expect(options.method).toBe("POST");
    expect(options.headers["Content-Type"]).toBe("application/json");
    expect(options.body).toBe(JSON.stringify({ a: 1 }));
  });

  it("throws ApiError with parsed detail on non-2xx", async () => {
    mockFetch({ detail: "algo salió mal" }, 422);
    await expect(apiFetch("/api/runs")).rejects.toMatchObject({
      status: 422,
      detail: { detail: "algo salió mal" },
    });
  });

  it("throws ApiError with null detail when body is not JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error("not json");
        },
      } as unknown as Response)
    );
    const error = await apiFetch("/api/runs").catch((e) => e as ApiError);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(500);
    expect(error.detail).toBeNull();
  });

  it("returns undefined for 204 No Content", async () => {
    mockFetch(null, 204);
    const result = await apiFetch("/api/runs/x/stop", { method: "POST" });
    expect(result).toBeUndefined();
  });
});

describe("wsUrl", () => {
  it("converts http origin to ws", () => {
    const url = wsUrl("/api/runs/abc/stream");
    expect(url.startsWith("ws://") || url.startsWith("wss://")).toBe(true);
    expect(url.endsWith("/api/runs/abc/stream")).toBe(true);
  });
});
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `npm run test -- client.test.ts`
Expected: falla porque `./client` no existe.

- [ ] **Step 3: Implementar**

Create `webconsole/frontend/src/api/client.ts`:

```typescript
const BASE_URL = (import.meta.env.VITE_BFF_URL as string | undefined) ?? "";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(`Error de API (status ${status})`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
  });

  if (!response.ok) {
    let detail: unknown = null;
    try {
      detail = await response.json();
    } catch {
      detail = null;
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function wsUrl(path: string): string {
  const base = BASE_URL || window.location.origin;
  return base.replace(/^http/, "ws") + path;
}
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `npm run test -- client.test.ts`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add webconsole/frontend/src/api/client.ts webconsole/frontend/src/api/client.test.ts
git commit -m "feat(webconsole-frontend): cliente HTTP mínimo (apiFetch, wsUrl)"
```

---

### Task 3: Tipos y funciones de la API (`api/types.ts`, `api/runs.ts`)

**Files:**
- Create: `webconsole/frontend/src/api/types.ts`
- Create: `webconsole/frontend/src/api/runs.ts`
- Test: Create `webconsole/frontend/src/api/runs.test.ts`

**Interfaces:**
- Consumes: `apiFetch`, `wsUrl` (Task 2, mockeados vía `vi.mock("./client")` en este task).
- Produces: tipos `IngestPluginInfo`, `DatasetCatalogEntry`, `PromptSetSummary`, `ModelInfo`, `ComposeRequest` (+ subtipos), `ComposeValidationResponse`, `RunStatusResponse`, `SaveManifestRequest`, `RunStreamEvent`; funciones `validateCompose`, `createRun`, `stopRun`, `getRun`, `listRuns`, `saveManifest`, `getModel`, `getIngestPlugins`, `getDatasets`, `getPromptSets`, `runStreamUrl`.

No se incluye `getManifests()` / `ManifestSummary`: el BFF expone `GET /api/catalog/manifests`, pero ninguna pantalla de este plan lo consume — Spec B no pide listar manifiestos en Catálogos, y "partir de un manifiesto existente como plantilla" en el compositor queda fuera del alcance de este MVP (ver Self-Review Notes). Agregarlo sin un consumidor sería código muerto.

Estos tipos son el espejo TypeScript de los schemas Pydantic del BFF (`webconsole/backend/src/eovrt_console/schemas.py`) — misma forma, sin compartir código (son procesos distintos).

- [ ] **Step 1: Crear los tipos (sin test — son solo declaraciones)**

Create `webconsole/frontend/src/api/types.ts`:

```typescript
export interface IngestPluginInfo {
  id: string;
  kind: "bounded" | "live";
  available: boolean;
  reason: string | null;
}

export interface DatasetCatalogEntry {
  id: string;
  type: string;
  description: string | null;
}

export interface PromptSetSummary {
  id: string;
  description: string | null;
  classes: string[];
  frozen: boolean;
}

export interface ModelInfo {
  ref: string;
  adapter: string | null;
  device: string;
  prompt_backend: string;
}

export interface ComposeIngestRequest {
  plugin: string;
  ref: string | null;
  config: Record<string, unknown>;
}

export interface ComposePromptsRequest {
  prompt_set_id: string;
  active_ids: string[] | null;
}

export interface ComposeRunParams {
  stride: number;
  max_units: number | null;
  save_annotated_video: boolean;
  min_confidence: number;
}

export interface ComposeRequest {
  ingest: ComposeIngestRequest;
  prompts: ComposePromptsRequest;
  run: ComposeRunParams;
}

export interface ComposeValidationResponse {
  valid: boolean;
  errors: string[];
}

export interface RunStatusResponse {
  run_id: string;
  status: "running" | "succeeded" | "failed" | "stopped";
  error: string | null;
  summary: Record<string, unknown> | null;
}

export interface SaveManifestRequest {
  name: string;
  description?: string | null;
  compose: ComposeRequest;
}

export interface RunStreamEvent {
  type: string;
  run_id?: string;
  total_units?: number | null;
  model_name?: string;
  source_type?: string;
  units_processed?: number;
  units_failed?: number;
  total_detections?: number;
  detections_by_label?: Record<string, number>;
  fps_effective?: number;
  latency_p95_ms?: number;
  gpu_memory_allocated_mb?: number;
  status?: string;
}
```

- [ ] **Step 2: Escribir el test que falla**

Create `webconsole/frontend/src/api/runs.test.ts`:

```typescript
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch, wsUrl } from "./client";

vi.mock("./client", () => ({
  apiFetch: vi.fn(),
  wsUrl: vi.fn(),
}));

import {
  createRun,
  getDatasets,
  getIngestPlugins,
  getModel,
  getPromptSets,
  getRun,
  listRuns,
  runStreamUrl,
  saveManifest,
  stopRun,
  validateCompose,
} from "./runs";
import type { ComposeRequest, SaveManifestRequest } from "./types";

const mockedApiFetch = vi.mocked(apiFetch);
const mockedWsUrl = vi.mocked(wsUrl);

const COMPOSE: ComposeRequest = {
  ingest: { plugin: "image_folder", ref: null, config: { path: "/tmp/imgs" } },
  prompts: { prompt_set_id: "cr01_cr02_v2_short", active_ids: ["person"] },
  run: { stride: 1, max_units: null, save_annotated_video: false, min_confidence: 0.25 },
};

beforeEach(() => {
  mockedApiFetch.mockReset();
  mockedWsUrl.mockReset();
});

describe("api/runs", () => {
  it("validateCompose posts to /api/compose/validate", async () => {
    mockedApiFetch.mockResolvedValue({ valid: true, errors: [] });
    await validateCompose(COMPOSE);
    expect(mockedApiFetch).toHaveBeenCalledWith("/api/compose/validate", {
      method: "POST",
      body: JSON.stringify(COMPOSE),
    });
  });

  it("createRun posts to /api/runs", async () => {
    mockedApiFetch.mockResolvedValue({ run_id: "run_1" });
    const result = await createRun(COMPOSE);
    expect(mockedApiFetch).toHaveBeenCalledWith("/api/runs", {
      method: "POST",
      body: JSON.stringify(COMPOSE),
    });
    expect(result).toEqual({ run_id: "run_1" });
  });

  it("stopRun posts to /api/runs/{id}/stop", async () => {
    mockedApiFetch.mockResolvedValue(undefined);
    await stopRun("run_1");
    expect(mockedApiFetch).toHaveBeenCalledWith("/api/runs/run_1/stop", { method: "POST" });
  });

  it("getRun fetches /api/runs/{id}", async () => {
    mockedApiFetch.mockResolvedValue({ run_id: "run_1", status: "running", error: null, summary: null });
    await getRun("run_1");
    expect(mockedApiFetch).toHaveBeenCalledWith("/api/runs/run_1");
  });

  it("listRuns fetches /api/runs", async () => {
    mockedApiFetch.mockResolvedValue([]);
    await listRuns();
    expect(mockedApiFetch).toHaveBeenCalledWith("/api/runs");
  });

  it("saveManifest posts to /api/manifests", async () => {
    mockedApiFetch.mockResolvedValue({ path: "experiments/x.yaml" });
    const payload: SaveManifestRequest = { name: "x", compose: COMPOSE };
    await saveManifest(payload);
    expect(mockedApiFetch).toHaveBeenCalledWith("/api/manifests", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  });

  it("getModel fetches /api/model", async () => {
    mockedApiFetch.mockResolvedValue({ ref: "mock", adapter: "mock", device: "cpu", prompt_backend: "default" });
    await getModel();
    expect(mockedApiFetch).toHaveBeenCalledWith("/api/model");
  });

  it("getIngestPlugins fetches /api/catalog/ingest-plugins", async () => {
    mockedApiFetch.mockResolvedValue([]);
    await getIngestPlugins();
    expect(mockedApiFetch).toHaveBeenCalledWith("/api/catalog/ingest-plugins");
  });

  it("getDatasets fetches /api/catalog/datasets", async () => {
    mockedApiFetch.mockResolvedValue([]);
    await getDatasets();
    expect(mockedApiFetch).toHaveBeenCalledWith("/api/catalog/datasets");
  });

  it("getPromptSets fetches /api/catalog/prompt-sets", async () => {
    mockedApiFetch.mockResolvedValue([]);
    await getPromptSets();
    expect(mockedApiFetch).toHaveBeenCalledWith("/api/catalog/prompt-sets");
  });

  it("runStreamUrl delegates to wsUrl", () => {
    mockedWsUrl.mockReturnValue("ws://localhost/api/runs/run_1/stream");
    const url = runStreamUrl("run_1");
    expect(mockedWsUrl).toHaveBeenCalledWith("/api/runs/run_1/stream");
    expect(url).toBe("ws://localhost/api/runs/run_1/stream");
  });
});
```

- [ ] **Step 3: Correr el test y verificar que falla**

Run: `npm run test -- runs.test.ts`
Expected: falla porque `./runs` no existe.

- [ ] **Step 4: Implementar**

Create `webconsole/frontend/src/api/runs.ts`:

```typescript
import { apiFetch, wsUrl } from "./client";
import type {
  ComposeRequest,
  ComposeValidationResponse,
  DatasetCatalogEntry,
  IngestPluginInfo,
  ModelInfo,
  PromptSetSummary,
  RunStatusResponse,
  SaveManifestRequest,
} from "./types";

export function validateCompose(payload: ComposeRequest): Promise<ComposeValidationResponse> {
  return apiFetch("/api/compose/validate", { method: "POST", body: JSON.stringify(payload) });
}

export function createRun(payload: ComposeRequest): Promise<{ run_id: string }> {
  return apiFetch("/api/runs", { method: "POST", body: JSON.stringify(payload) });
}

export function stopRun(runId: string): Promise<void> {
  return apiFetch(`/api/runs/${runId}/stop`, { method: "POST" });
}

export function getRun(runId: string): Promise<RunStatusResponse> {
  return apiFetch(`/api/runs/${runId}`);
}

export function listRuns(): Promise<RunStatusResponse[]> {
  return apiFetch("/api/runs");
}

export function saveManifest(payload: SaveManifestRequest): Promise<{ path: string }> {
  return apiFetch("/api/manifests", { method: "POST", body: JSON.stringify(payload) });
}

export function getModel(): Promise<ModelInfo> {
  return apiFetch("/api/model");
}

export function getIngestPlugins(): Promise<IngestPluginInfo[]> {
  return apiFetch("/api/catalog/ingest-plugins");
}

export function getDatasets(): Promise<DatasetCatalogEntry[]> {
  return apiFetch("/api/catalog/datasets");
}

export function getPromptSets(): Promise<PromptSetSummary[]> {
  return apiFetch("/api/catalog/prompt-sets");
}

export function runStreamUrl(runId: string): string {
  return wsUrl(`/api/runs/${runId}/stream`);
}
```

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `npm run test -- runs.test.ts`
Expected: 10 passed

- [ ] **Step 6: Commit**

```bash
git add webconsole/frontend/src/api/types.ts webconsole/frontend/src/api/runs.ts webconsole/frontend/src/api/runs.test.ts
git commit -m "feat(webconsole-frontend): tipos y funciones tipadas de la API del BFF"
```

---

### Task 4: `useRunStream` — hook de telemetría en vivo

**Files:**
- Create: `webconsole/frontend/src/test/fakeWebSocket.ts`
- Create: `webconsole/frontend/src/hooks/useRunStream.ts`
- Test: Create `webconsole/frontend/src/hooks/useRunStream.test.ts`

**Interfaces:**
- Consumes: `runStreamUrl` (Task 3, mockeado en este test).
- Produces: `RunStreamState` (`events: RunStreamEvent[]`, `latest: RunStreamEvent | null`, `connectionState: "connecting" | "open" | "closed"`), `useRunStream(runId: string | null) -> RunStreamState`.

- [ ] **Step 1: Crear el fake de `WebSocket`**

Create `webconsole/frontend/src/test/fakeWebSocket.ts`:

```typescript
export class FakeWebSocket {
  static instances: FakeWebSocket[] = [];

  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  closed = false;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  emitOpen(): void {
    this.onopen?.();
  }

  emitMessage(payload: unknown): void {
    this.onmessage?.({ data: JSON.stringify(payload) });
  }

  close(): void {
    this.closed = true;
    this.onclose?.();
  }

  static reset(): void {
    FakeWebSocket.instances = [];
  }
}
```

- [ ] **Step 2: Escribir el test que falla**

Create `webconsole/frontend/src/hooks/useRunStream.test.ts`:

```typescript
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FakeWebSocket } from "../test/fakeWebSocket";

vi.mock("../api/runs", () => ({
  runStreamUrl: vi.fn((runId: string) => `ws://localhost/api/runs/${runId}/stream`),
}));

import { useRunStream } from "./useRunStream";

beforeEach(() => {
  FakeWebSocket.reset();
  vi.stubGlobal("WebSocket", FakeWebSocket);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useRunStream", () => {
  it("starts in connecting state and does nothing for a null runId", () => {
    const { result } = renderHook(() => useRunStream(null));
    expect(result.current.events).toEqual([]);
    expect(FakeWebSocket.instances).toHaveLength(0);
  });

  it("transitions to open and accumulates events", async () => {
    const { result } = renderHook(() => useRunStream("run_1"));
    expect(FakeWebSocket.instances).toHaveLength(1);
    const socket = FakeWebSocket.instances[0];
    expect(socket.url).toBe("ws://localhost/api/runs/run_1/stream");

    act(() => socket.emitOpen());
    await waitFor(() => expect(result.current.connectionState).toBe("open"));

    act(() => socket.emitMessage({ type: "started", run_id: "run_1" }));
    act(() => socket.emitMessage({ type: "progress", units_processed: 1 }));

    await waitFor(() => expect(result.current.events).toHaveLength(2));
    expect(result.current.latest).toEqual({ type: "progress", units_processed: 1 });
  });

  it("moves to closed state when the socket closes", async () => {
    const { result } = renderHook(() => useRunStream("run_1"));
    const socket = FakeWebSocket.instances[0];

    act(() => socket.close());

    await waitFor(() => expect(result.current.connectionState).toBe("closed"));
  });

  it("closes the previous socket and resets events when runId changes", () => {
    const { result, rerender } = renderHook(({ runId }) => useRunStream(runId), {
      initialProps: { runId: "run_1" },
    });
    const firstSocket = FakeWebSocket.instances[0];
    act(() => firstSocket.emitMessage({ type: "started" }));

    rerender({ runId: "run_2" });

    expect(firstSocket.closed).toBe(true);
    expect(result.current.events).toEqual([]);
    expect(FakeWebSocket.instances).toHaveLength(2);
  });
});
```

- [ ] **Step 3: Correr el test y verificar que falla**

Run: `npm run test -- useRunStream.test.ts`
Expected: falla porque `./useRunStream` no existe.

- [ ] **Step 4: Implementar**

Create `webconsole/frontend/src/hooks/useRunStream.ts`:

```typescript
import { useEffect, useState } from "react";
import { runStreamUrl } from "../api/runs";
import type { RunStreamEvent } from "../api/types";

export interface RunStreamState {
  events: RunStreamEvent[];
  latest: RunStreamEvent | null;
  connectionState: "connecting" | "open" | "closed";
}

export function useRunStream(runId: string | null): RunStreamState {
  const [events, setEvents] = useState<RunStreamEvent[]>([]);
  const [connectionState, setConnectionState] = useState<"connecting" | "open" | "closed">(
    "connecting"
  );

  useEffect(() => {
    if (!runId) {
      return undefined;
    }

    setEvents([]);
    setConnectionState("connecting");

    const socket = new WebSocket(runStreamUrl(runId));
    socket.onopen = () => setConnectionState("open");
    socket.onmessage = (event: MessageEvent<string>) => {
      const parsed = JSON.parse(event.data) as RunStreamEvent;
      setEvents((prev) => [...prev, parsed]);
    };
    socket.onclose = () => setConnectionState("closed");

    return () => {
      socket.close();
    };
  }, [runId]);

  return {
    events,
    latest: events.length > 0 ? events[events.length - 1] : null,
    connectionState,
  };
}
```

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `npm run test -- useRunStream.test.ts`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add webconsole/frontend/src/test/fakeWebSocket.ts webconsole/frontend/src/hooks/useRunStream.ts webconsole/frontend/src/hooks/useRunStream.test.ts
git commit -m "feat(webconsole-frontend): hook useRunStream para telemetría en vivo"
```

---

### Task 5: `RunsListPage`

**Files:**
- Create: `webconsole/frontend/src/pages/RunsListPage.tsx`
- Test: Create `webconsole/frontend/src/pages/RunsListPage.test.tsx`

**Interfaces:**
- Consumes: `listRuns` (Task 3, mockeado vía `vi.mock("../api/runs")`).
- Produces: `RunsListPage` (componente, sin props).

- [ ] **Step 1: Escribir el test que falla**

Create `webconsole/frontend/src/pages/RunsListPage.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/runs", () => ({
  listRuns: vi.fn(),
}));

import { listRuns } from "../api/runs";
import { RunsListPage } from "./RunsListPage";

const mockedListRuns = vi.mocked(listRuns);

beforeEach(() => {
  mockedListRuns.mockReset();
});

describe("RunsListPage", () => {
  it("renders runs returned by listRuns", async () => {
    mockedListRuns.mockResolvedValue([
      { run_id: "run_1", status: "succeeded", error: null, summary: null },
    ]);

    render(
      <MemoryRouter>
        <RunsListPage />
      </MemoryRouter>
    );

    expect(await screen.findByText("run_1")).toBeInTheDocument();
    expect(screen.getByText("succeeded")).toBeInTheDocument();
  });

  it("shows a link to create a new run", () => {
    mockedListRuns.mockResolvedValue([]);
    render(
      <MemoryRouter>
        <RunsListPage />
      </MemoryRouter>
    );
    expect(screen.getByRole("link", { name: "Nueva corrida" })).toHaveAttribute(
      "href",
      "/runs/new"
    );
  });

  it("shows an error message when listRuns fails", async () => {
    mockedListRuns.mockRejectedValue(new Error("no se pudo conectar"));
    render(
      <MemoryRouter>
        <RunsListPage />
      </MemoryRouter>
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("no se pudo conectar");
  });
});
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `npm run test -- RunsListPage.test.tsx`
Expected: falla porque `./RunsListPage` no existe.

- [ ] **Step 3: Implementar**

Create `webconsole/frontend/src/pages/RunsListPage.tsx`:

```tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listRuns } from "../api/runs";
import type { RunStatusResponse } from "../api/types";

export function RunsListPage() {
  const [runs, setRuns] = useState<RunStatusResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await listRuns();
        if (!cancelled) {
          setRuns(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Error desconocido");
        }
      }
    }

    load();
    const interval = setInterval(load, 3000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return (
    <div>
      <h1>Corridas</h1>
      <Link to="/runs/new">Nueva corrida</Link>
      {error && <p role="alert">{error}</p>}
      <table>
        <thead>
          <tr>
            <th>Run ID</th>
            <th>Estado</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.run_id}>
              <td>
                <Link to={`/runs/${run.run_id}`}>{run.run_id}</Link>
              </td>
              <td>{run.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `npm run test -- RunsListPage.test.tsx`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add webconsole/frontend/src/pages/RunsListPage.tsx webconsole/frontend/src/pages/RunsListPage.test.tsx
git commit -m "feat(webconsole-frontend): página de lista de corridas"
```

---

### Task 6: `NewRunPage` — compositor

**Files:**
- Create: `webconsole/frontend/src/pages/NewRunPage.tsx`
- Test: Create `webconsole/frontend/src/pages/NewRunPage.test.tsx`

**Interfaces:**
- Consumes: `getIngestPlugins`, `getPromptSets`, `validateCompose`, `createRun`, `saveManifest` (Task 3, mockeados).
- Produces: `NewRunPage` (componente, sin props). Requiere `react-router-dom`'s `useNavigate` (mockeado en el test).

- [ ] **Step 1: Escribir el test que falla**

Create `webconsole/frontend/src/pages/NewRunPage.test.tsx`:

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { navigateMock } = vi.hoisted(() => ({ navigateMock: vi.fn() }));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => navigateMock };
});

vi.mock("../api/runs", () => ({
  getIngestPlugins: vi.fn(),
  getPromptSets: vi.fn(),
  validateCompose: vi.fn(),
  createRun: vi.fn(),
  saveManifest: vi.fn(),
}));

import {
  createRun,
  getIngestPlugins,
  getPromptSets,
  saveManifest,
  validateCompose,
} from "../api/runs";
import { NewRunPage } from "./NewRunPage";

const PLUGINS = [
  { id: "image_folder", kind: "bounded" as const, available: true, reason: null },
  { id: "video_file", kind: "bounded" as const, available: true, reason: null },
  { id: "rtsp", kind: "live" as const, available: true, reason: null },
  { id: "oak_d", kind: "live" as const, available: false, reason: "sin hardware" },
];

const PROMPT_SETS = [
  { id: "cr01_cr02_v2_short", description: null, classes: ["person", "helmet"], frozen: true },
];

function renderPage() {
  render(
    <MemoryRouter>
      <NewRunPage />
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.mocked(getIngestPlugins).mockResolvedValue(PLUGINS);
  vi.mocked(getPromptSets).mockResolvedValue(PROMPT_SETS);
  vi.mocked(validateCompose).mockReset();
  vi.mocked(createRun).mockReset();
  vi.mocked(saveManifest).mockReset();
  navigateMock.mockReset();
});

describe("NewRunPage", () => {
  it("disables live plugins in the source selector", async () => {
    renderPage();
    const rtspOption = await screen.findByRole("option", { name: /rtsp/ });
    const oakDOption = screen.getByRole("option", { name: /oak_d/ });
    expect(rtspOption).toBeDisabled();
    expect(oakDOption).toBeDisabled();
  });

  it("shows class checkboxes once a prompt set is selected", async () => {
    renderPage();
    const select = await screen.findByLabelText("Prompt set");
    fireEvent.change(select, { target: { value: "cr01_cr02_v2_short" } });

    expect(await screen.findByLabelText("person")).toBeInTheDocument();
    expect(screen.getByLabelText("helmet")).toBeInTheDocument();
  });

  it("shows validation errors and does not launch when invalid", async () => {
    vi.mocked(validateCompose).mockResolvedValue({ valid: false, errors: ["path es requerido"] });
    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: "Lanzar" }));

    expect(await screen.findByText("path es requerido")).toBeInTheDocument();
    expect(createRun).not.toHaveBeenCalled();
    expect(navigateMock).not.toHaveBeenCalled();
  });

  it("launches and navigates to the run detail on success", async () => {
    vi.mocked(validateCompose).mockResolvedValue({ valid: true, errors: [] });
    vi.mocked(createRun).mockResolvedValue({ run_id: "run_42" });
    renderPage();

    fireEvent.change(await screen.findByLabelText("Ruta"), { target: { value: "/tmp/imgs" } });
    fireEvent.click(screen.getByRole("button", { name: "Lanzar" }));

    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith("/runs/run_42"));
  });
});
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `npm run test -- NewRunPage.test.tsx`
Expected: falla porque `./NewRunPage` no existe.

- [ ] **Step 3: Implementar**

Create `webconsole/frontend/src/pages/NewRunPage.tsx`:

```tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createRun, getIngestPlugins, getPromptSets, saveManifest, validateCompose } from "../api/runs";
import type { ComposeRequest, IngestPluginInfo, PromptSetSummary } from "../api/types";

export function NewRunPage() {
  const navigate = useNavigate();
  const [plugins, setPlugins] = useState<IngestPluginInfo[]>([]);
  const [promptSets, setPromptSets] = useState<PromptSetSummary[]>([]);
  const [pluginId, setPluginId] = useState("image_folder");
  const [path, setPath] = useState("");
  const [promptSetId, setPromptSetId] = useState("");
  const [activeIds, setActiveIds] = useState<string[]>([]);
  const [stride, setStride] = useState(1);
  const [errors, setErrors] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getIngestPlugins().then(setPlugins).catch(() => setPlugins([]));
    getPromptSets().then(setPromptSets).catch(() => setPromptSets([]));
  }, []);

  function buildRequest(): ComposeRequest {
    return {
      ingest: { plugin: pluginId, ref: null, config: path ? { path } : {} },
      prompts: { prompt_set_id: promptSetId, active_ids: activeIds.length > 0 ? activeIds : null },
      run: { stride, max_units: null, save_annotated_video: false, min_confidence: 0.25 },
    };
  }

  async function handleLaunch() {
    setSubmitting(true);
    try {
      const validation = await validateCompose(buildRequest());
      if (!validation.valid) {
        setErrors(validation.errors);
        return;
      }
      setErrors([]);
      const { run_id } = await createRun(buildRequest());
      navigate(`/runs/${run_id}`);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSaveManifest() {
    const name = window.prompt("Nombre del manifiesto:");
    if (!name) {
      return;
    }
    await saveManifest({ name, compose: buildRequest() });
  }

  const selectedPromptSet = promptSets.find((p) => p.id === promptSetId);

  return (
    <div>
      <h1>Nueva corrida</h1>

      <label htmlFor="plugin-select">Fuente</label>
      <select id="plugin-select" value={pluginId} onChange={(e) => setPluginId(e.target.value)}>
        {plugins.map((plugin) => (
          <option
            key={plugin.id}
            value={plugin.id}
            disabled={!plugin.available || plugin.kind === "live"}
          >
            {plugin.id}
            {plugin.kind === "live" ? " (vivo — próximamente)" : ""}
            {!plugin.available ? ` (no disponible: ${plugin.reason ?? "sin detalle"})` : ""}
          </option>
        ))}
      </select>

      <label htmlFor="path-input">Ruta</label>
      <input id="path-input" value={path} onChange={(e) => setPath(e.target.value)} />

      <label htmlFor="prompt-set-select">Prompt set</label>
      <select
        id="prompt-set-select"
        value={promptSetId}
        onChange={(e) => {
          setPromptSetId(e.target.value);
          setActiveIds([]);
        }}
      >
        <option value="">-- elegir --</option>
        {promptSets.map((promptSet) => (
          <option key={promptSet.id} value={promptSet.id}>
            {promptSet.id}
          </option>
        ))}
      </select>

      {selectedPromptSet && (
        <fieldset>
          <legend>Clases activas</legend>
          {selectedPromptSet.classes.map((classId) => (
            <label key={classId} htmlFor={`class-${classId}`}>
              <input
                id={`class-${classId}`}
                type="checkbox"
                checked={activeIds.includes(classId)}
                onChange={(e) => {
                  setActiveIds((prev) =>
                    e.target.checked ? [...prev, classId] : prev.filter((id) => id !== classId)
                  );
                }}
              />
              {classId}
            </label>
          ))}
        </fieldset>
      )}

      <label htmlFor="stride-input">Stride</label>
      <input
        id="stride-input"
        type="number"
        min={1}
        value={stride}
        onChange={(e) => setStride(Number(e.target.value))}
      />

      {errors.length > 0 && (
        <ul role="alert">
          {errors.map((err) => (
            <li key={err}>{err}</li>
          ))}
        </ul>
      )}

      <button type="button" onClick={handleLaunch} disabled={submitting}>
        Lanzar
      </button>
      <button type="button" onClick={handleSaveManifest}>
        Guardar como manifiesto
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `npm run test -- NewRunPage.test.tsx`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add webconsole/frontend/src/pages/NewRunPage.tsx webconsole/frontend/src/pages/NewRunPage.test.tsx
git commit -m "feat(webconsole-frontend): compositor de corridas (NewRunPage)"
```

---

### Task 7: `RunDetailPage`

**Files:**
- Create: `webconsole/frontend/src/pages/RunDetailPage.tsx`
- Test: Create `webconsole/frontend/src/pages/RunDetailPage.test.tsx`

**Interfaces:**
- Consumes: `useRunStream` (Task 4), `getRun`, `stopRun` (Task 3, mockeados).
- Produces: `RunDetailPage` (componente, sin props — lee `runId` de la URL vía `useParams`).

- [ ] **Step 1: Escribir el test que falla**

Create `webconsole/frontend/src/pages/RunDetailPage.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FakeWebSocket } from "../test/fakeWebSocket";

vi.mock("../api/runs", () => ({
  runStreamUrl: vi.fn((runId: string) => `ws://localhost/api/runs/${runId}/stream`),
  getRun: vi.fn(),
  stopRun: vi.fn(),
}));

import { getRun, stopRun } from "../api/runs";
import { RunDetailPage } from "./RunDetailPage";

function renderPage(runId = "run_1") {
  render(
    <MemoryRouter initialEntries={[`/runs/${runId}`]}>
      <Routes>
        <Route path="/runs/:runId" element={<RunDetailPage />} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  FakeWebSocket.reset();
  vi.stubGlobal("WebSocket", FakeWebSocket);
  vi.mocked(getRun).mockReset();
  vi.mocked(stopRun).mockReset();
});

describe("RunDetailPage", () => {
  it("shows live progress from stream events", async () => {
    renderPage();
    const socket = FakeWebSocket.instances[0];

    socket.emitMessage({ type: "started", total_units: 10 });
    socket.emitMessage({
      type: "progress",
      units_processed: 3,
      units_failed: 0,
      total_detections: 5,
      fps_effective: 2.1,
    });

    expect(await screen.findByText(/Total de unidades: 10/)).toBeInTheDocument();
    expect(await screen.findByText(/Procesadas: 3/)).toBeInTheDocument();
  });

  it("fetches the final status when the stream reports finished", async () => {
    vi.mocked(getRun).mockResolvedValue({
      run_id: "run_1",
      status: "succeeded",
      error: null,
      summary: { units_processed: 10 },
    });
    renderPage();
    const socket = FakeWebSocket.instances[0];

    socket.emitMessage({ type: "finished", status: "succeeded" });

    await waitFor(() => expect(getRun).toHaveBeenCalledWith("run_1"));
    expect(await screen.findByText(/Resultado: succeeded/)).toBeInTheDocument();
  });

  it("calls stopRun when the stop button is clicked", async () => {
    vi.mocked(stopRun).mockResolvedValue(undefined);
    renderPage();

    (await screen.findByRole("button", { name: "Detener" })).click();

    await waitFor(() => expect(stopRun).toHaveBeenCalledWith("run_1"));
  });
});
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `npm run test -- RunDetailPage.test.tsx`
Expected: falla porque `./RunDetailPage` no existe.

- [ ] **Step 3: Implementar**

Create `webconsole/frontend/src/pages/RunDetailPage.tsx`:

```tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getRun, stopRun } from "../api/runs";
import { useRunStream } from "../hooks/useRunStream";
import type { RunStatusResponse } from "../api/types";

export function RunDetailPage() {
  const { runId = "" } = useParams();
  const { events, latest, connectionState } = useRunStream(runId || null);
  const [finalStatus, setFinalStatus] = useState<RunStatusResponse | null>(null);

  useEffect(() => {
    if (latest?.type === "finished" && runId) {
      getRun(runId).then(setFinalStatus);
    }
  }, [latest, runId]);

  const startedEvent = events.find((event) => event.type === "started");
  const progressEvent = [...events].reverse().find((event) => event.type === "progress");

  return (
    <div>
      <h1>Corrida {runId}</h1>
      <p>Conexión: {connectionState}</p>

      {startedEvent && <p>Total de unidades: {startedEvent.total_units ?? "indefinido"}</p>}

      {progressEvent && (
        <ul>
          <li>Procesadas: {progressEvent.units_processed}</li>
          <li>Fallidas: {progressEvent.units_failed}</li>
          <li>Detecciones: {progressEvent.total_detections}</li>
          <li>FPS: {progressEvent.fps_effective}</li>
          <li>Latencia p95: {progressEvent.latency_p95_ms} ms</li>
          <li>GPU mem: {progressEvent.gpu_memory_allocated_mb} MB</li>
        </ul>
      )}

      {finalStatus && (
        <div>
          <h2>Resultado: {finalStatus.status}</h2>
          <pre>{JSON.stringify(finalStatus.summary, null, 2)}</pre>
        </div>
      )}

      <button type="button" onClick={() => stopRun(runId)}>
        Detener
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `npm run test -- RunDetailPage.test.tsx`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add webconsole/frontend/src/pages/RunDetailPage.tsx webconsole/frontend/src/pages/RunDetailPage.test.tsx
git commit -m "feat(webconsole-frontend): página de detalle de corrida en vivo"
```

---

### Task 8: `CatalogPage`

**Files:**
- Create: `webconsole/frontend/src/pages/CatalogPage.tsx`
- Test: Create `webconsole/frontend/src/pages/CatalogPage.test.tsx`

**Interfaces:**
- Consumes: `getModel`, `getIngestPlugins`, `getDatasets`, `getPromptSets` (Task 3, mockeados).
- Produces: `CatalogPage` (componente, sin props).

- [ ] **Step 1: Escribir el test que falla**

Create `webconsole/frontend/src/pages/CatalogPage.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/runs", () => ({
  getModel: vi.fn(),
  getIngestPlugins: vi.fn(),
  getDatasets: vi.fn(),
  getPromptSets: vi.fn(),
}));

import { getDatasets, getIngestPlugins, getModel, getPromptSets } from "../api/runs";
import { CatalogPage } from "./CatalogPage";

beforeEach(() => {
  vi.mocked(getModel).mockResolvedValue({
    ref: "mock",
    adapter: "mock",
    device: "cpu",
    prompt_backend: "default",
  });
  vi.mocked(getIngestPlugins).mockResolvedValue([
    { id: "oak_d", kind: "live", available: false, reason: "sin hardware" },
  ]);
  vi.mocked(getDatasets).mockResolvedValue([{ id: "demo_v2", type: "image_folder", description: null }]);
  vi.mocked(getPromptSets).mockResolvedValue([
    { id: "cr01_cr02_v2_short", description: null, classes: ["person", "helmet"], frozen: true },
  ]);
});

describe("CatalogPage", () => {
  it("renders the active model", async () => {
    render(<CatalogPage />);
    expect(await screen.findByText(/mock/)).toBeInTheDocument();
  });

  it("renders unavailable ingest plugins with their reason", async () => {
    render(<CatalogPage />);
    expect(await screen.findByText(/oak_d/)).toBeInTheDocument();
    expect(await screen.findByText(/sin hardware/)).toBeInTheDocument();
  });

  it("renders datasets and prompt sets", async () => {
    render(<CatalogPage />);
    expect(await screen.findByText(/demo_v2/)).toBeInTheDocument();
    expect(await screen.findByText(/cr01_cr02_v2_short/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `npm run test -- CatalogPage.test.tsx`
Expected: falla porque `./CatalogPage` no existe.

- [ ] **Step 3: Implementar**

Create `webconsole/frontend/src/pages/CatalogPage.tsx`:

```tsx
import { useEffect, useState } from "react";
import { getDatasets, getIngestPlugins, getModel, getPromptSets } from "../api/runs";
import type { DatasetCatalogEntry, IngestPluginInfo, ModelInfo, PromptSetSummary } from "../api/types";

export function CatalogPage() {
  const [model, setModel] = useState<ModelInfo | null>(null);
  const [plugins, setPlugins] = useState<IngestPluginInfo[]>([]);
  const [datasets, setDatasets] = useState<DatasetCatalogEntry[]>([]);
  const [promptSets, setPromptSets] = useState<PromptSetSummary[]>([]);

  useEffect(() => {
    getModel().then(setModel);
    getIngestPlugins().then(setPlugins);
    getDatasets().then(setDatasets);
    getPromptSets().then(setPromptSets);
  }, []);

  return (
    <div>
      <h1>Catálogos</h1>

      <h2>Modelo activo</h2>
      {model && (
        <p>
          {model.ref} ({model.device})
        </p>
      )}

      <h2>Plugins de ingesta</h2>
      <ul>
        {plugins.map((plugin) => (
          <li key={plugin.id}>
            {plugin.id} — {plugin.available ? "disponible" : `no disponible (${plugin.reason})`}
          </li>
        ))}
      </ul>

      <h2>Datasets</h2>
      <ul>
        {datasets.map((dataset) => (
          <li key={dataset.id}>
            {dataset.id} ({dataset.type})
          </li>
        ))}
      </ul>

      <h2>Prompt sets</h2>
      <ul>
        {promptSets.map((promptSet) => (
          <li key={promptSet.id}>
            {promptSet.id}: {promptSet.classes.join(", ")}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `npm run test -- CatalogPage.test.tsx`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add webconsole/frontend/src/pages/CatalogPage.tsx webconsole/frontend/src/pages/CatalogPage.test.tsx
git commit -m "feat(webconsole-frontend): página de catálogos"
```

---

### Task 9: `App.tsx` — routing y navegación

**Files:**
- Modify: `webconsole/frontend/src/App.tsx`
- Modify: `webconsole/frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: `RunsListPage` (Task 5), `NewRunPage` (Task 6), `RunDetailPage` (Task 7), `CatalogPage` (Task 8).
- Produces: `App` completo con routing.

- [ ] **Step 1: Escribir el test que falla**

Modificar `webconsole/frontend/src/App.test.tsx` (reemplazar el contenido del Task 1):

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api/runs", () => ({
  listRuns: vi.fn().mockResolvedValue([]),
  getIngestPlugins: vi.fn().mockResolvedValue([]),
  getPromptSets: vi.fn().mockResolvedValue([]),
  getModel: vi.fn().mockResolvedValue({ ref: "mock", adapter: "mock", device: "cpu", prompt_backend: "default" }),
  getDatasets: vi.fn().mockResolvedValue([]),
}));

import { App } from "./App";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("App", () => {
  it("renders the runs list at the root route", async () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>
    );
    expect(await screen.findByText("Corridas")).toBeInTheDocument();
  });

  it("renders the catalog page at /catalog", async () => {
    render(
      <MemoryRouter initialEntries={["/catalog"]}>
        <App />
      </MemoryRouter>
    );
    expect(await screen.findByText("Catálogos")).toBeInTheDocument();
  });

  it("has navigation links to runs and catalog", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByRole("link", { name: "Corridas" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Catálogos" })).toHaveAttribute("href", "/catalog");
  });
});
```

**Nota:** `App` ya no acepta un `Router` propio en este test — el test envuelve `App` en `MemoryRouter` desde afuera, así que `App.tsx` no debe declarar su propio `BrowserRouter` (se agrega en `main.tsx`, Step 3).

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `npm run test -- App.test.tsx`
Expected: falla — el `App` actual es solo el placeholder `<h1>E-OVRT Webconsole</h1>` sin rutas.

- [ ] **Step 3: Implementar**

Create (reemplazar) `webconsole/frontend/src/App.tsx`:

```tsx
import { Link, Route, Routes } from "react-router-dom";
import { CatalogPage } from "./pages/CatalogPage";
import { NewRunPage } from "./pages/NewRunPage";
import { RunDetailPage } from "./pages/RunDetailPage";
import { RunsListPage } from "./pages/RunsListPage";

export function App() {
  return (
    <div>
      <nav>
        <Link to="/">Corridas</Link>
        <Link to="/catalog">Catálogos</Link>
      </nav>
      <Routes>
        <Route path="/" element={<RunsListPage />} />
        <Route path="/runs/new" element={<NewRunPage />} />
        <Route path="/runs/:runId" element={<RunDetailPage />} />
        <Route path="/catalog" element={<CatalogPage />} />
      </Routes>
    </div>
  );
}
```

Modificar `webconsole/frontend/src/main.tsx` para envolver `App` en `BrowserRouter` (antes no existía routing, ahora `App` lo requiere):

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `npm run test -- App.test.tsx`
Expected: 3 passed

- [ ] **Step 5: Correr toda la suite**

Run: `npm run test`
Expected: todos los tests de los Tasks 1-9 en verde (34 tests aproximadamente).

- [ ] **Step 6: Commit**

```bash
git add webconsole/frontend/src/App.tsx webconsole/frontend/src/App.test.tsx webconsole/frontend/src/main.tsx
git commit -m "feat(webconsole-frontend): routing completo entre las 4 pantallas"
```

---

### Task 10: Verificación final — build y lint

**Files:**
- No crea archivos nuevos — solo verificación.

- [ ] **Step 1: Type-check y build de producción**

Run: `npm run build`
Expected: `tsc -b` compila sin errores de tipos y `vite build` genera `dist/` sin fallos.

- [ ] **Step 2: Lint**

Si no existe `.eslintrc`/config de ESLint todavía, crear `webconsole/frontend/eslint.config.js` mínimo:

```javascript
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import react from "eslint-plugin-react";

export default tseslint.config(
  { ignores: ["dist"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    plugins: { react },
    rules: {
      ...react.configs.recommended.rules,
    },
    settings: { react: { version: "detect" } },
  }
);
```

Agregar las dependencias necesarias a `package.json` (`devDependencies`): `"@eslint/js": "^9.9.0"`, `"typescript-eslint": "^8.0.0"`, `"eslint-plugin-react": "^7.35.0"`.

Run:
```bash
npm install
npm run lint
```
Expected: sin errores (warnings menores aceptables).

- [ ] **Step 3: Smoke test manual contra el BFF**

Con el BFF corriendo (`cd webconsole/backend && SERVICE_URL=http://localhost:8000 uvicorn eovrt_console.app:app --port 8100`) y el servicio media-plane corriendo con `MODEL_REF=mock` en `:8000`:

Run: `npm run dev`
Expected: `http://localhost:5173` sirve la SPA; la página de Catálogos muestra el modelo `mock` y los 4 plugins de ingesta; se puede componer y lanzar una corrida contra un directorio de imágenes local y ver la telemetría en vivo en el detalle.

(Si `VITE_BFF_URL` no está seteada, `api/client.ts` usa rutas relativas — requiere servir la SPA detrás del mismo origen que el BFF, o setear `VITE_BFF_URL=http://localhost:8100` en un `.env.local` para desarrollo separado.)

- [ ] **Step 4: Commit**

```bash
git add webconsole/frontend/eslint.config.js webconsole/frontend/package.json webconsole/frontend/package-lock.json
git commit -m "chore(webconsole-frontend): configuración de lint y verificación final"
```

---

## Self-Review Notes

- **Cobertura del spec (Spec B, §6 Frontend)**: "Runs (home)" → Task 5; "Nueva corrida (compositor)" → Task 6; "Detalle de corrida (vivo)" → Task 7; "Catálogos (read-only)" → Task 8; navegación entre las 4 → Task 9.
- **Decisiones de alcance tomadas en este plan** (no explícitas en Spec B, documentadas para no fabricar comportamiento): (1) sin librería de data-fetching/estado global — justificado en Global Constraints por el tamaño del MVP; (2) el compositor deshabilita `rtsp`/`oak_d` en el selector aunque el backend ya los liste — consistente con "datasets/video ahora, vivo como plugin-slot" de Spec B; (3) sin selector de dataset por `ref` en el compositor (solo `path` inline) — el backend ya soporta `ref`, es puramente una simplificación de UI para el primer corte; (4) no se lista `GET /api/catalog/manifests` en ninguna pantalla ni se ofrece "partir de un manifiesto existente como plantilla" en el compositor — sin consumidor en este MVP, se agrega cuando se implemente esa feature (evita código muerto: `getManifests`/`ManifestSummary` no se declaran).
- **Placeholder scan**: sin TBD/TODO; todo el código de cada step es completo y compilable.
- **Bugs encontrados y corregidos durante la auto-revisión**: (a) Task 6 referenciaba `navigateMock` dentro de un factory `vi.mock` hoisteado sin usar `vi.hoisted()` — hubiera fallado en runtime con `ReferenceError`; (b) `test.globals` no está activo pero ningún test llamaba `cleanup()` explícitamente — sin eso, el DOM de un test podía filtrarse al siguiente dentro del mismo archivo; se agregó `afterEach(cleanup)` a `src/test/setup.ts` (Task 1); (c) Task 5 usaba `vi.useFakeTimers` innecesariamente para "proteger" el `setInterval` del polling — se simplificó, ya que `cleanup()` dispara el `useEffect` de limpieza (`clearInterval`) al desmontar.
- **Consistencia de tipos**: los tipos de `api/types.ts` (Task 3) son el único punto de definición — reusados sin redeclarar en `useRunStream` (Task 4) y en las 4 páginas (Tasks 5-8). Las funciones mockeadas en cada test de página (`vi.mock("../api/runs")`) exponen exactamente los nombres exportados por `api/runs.ts` (Task 3) — ninguna página importa una función no definida allí.
- **Dependencia con el plan del BFF**: este plan asume que `webconsole/backend` (plan hermano `2026-07-01-webconsole-backend.md`) expone exactamente las rutas usadas en `api/runs.ts` — mismos paths y formas de payload verificados campo a campo contra los schemas de ese plan (`ComposeRequest`, `RunStatusResponse`, etc.).
