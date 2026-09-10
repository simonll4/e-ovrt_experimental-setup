# Tramo 0 — Contrato congelado

Leé antes `01-reglas-codex.md`. Este tramo **no toca una sola línea de
`src/` de producción**: sólo agrega tests.

---

## Objetivo

Escribir una suite que describa **lo que la consola hace hoy**, para poder
afirmar más adelante que sigue haciendo lo mismo con otro aspecto.

Es un test de caracterización: no inventa comportamiento deseado, **congela el
observado**. Por eso el criterio de cierre es que pase contra la rama sin tocar.

---

## Dónde va

```
webconsole/frontend/src/__tests__/contrato/
```

Un archivo por flujo:

| Archivo | Flujo |
|---|---|
| `nueva-corrida.contrato.test.tsx` | Nueva corrida → lanzar |
| `corrida-viva.contrato.test.tsx` | Corrida en vivo |
| `detalle-traza-evaluacion.contrato.test.tsx` | Detalle, traza y evaluación |
| `experimentos-distribucion.contrato.test.tsx` | Experimentos y distribución |

---

## La regla que hace que esto funcione: mockeá `fetch`, no el módulo

Los tests que ya existen en el repo hacen `vi.mock('../api', ...)`. **El contrato
no puede hacer eso.** En el tramo 2 `src/api.ts` se convierte en
`src/api/endpoints.ts` + `src/api/index.ts`, y un mock por ruta de módulo se
rompería — y arreglarlo significaría editar el contrato, que está prohibido.

El contrato mockea **`globalThis.fetch`**. Se verificó que tanto la capa de API de
hoy (`src/api.ts:20`) como la del árbol de referencia
(`src/api/endpoints.ts:21,237`) usan `fetch` global, así que el mismo mock sirve
antes y después.

Mockear `fetch` además es lo que hace que el contrato afirme lo que tiene que
afirmar: **qué peticiones HTTP sale a hacer la consola**.

Patrón:

```tsx
const llamadas: Array<{ url: string; method: string; body: unknown }> = []

beforeEach(() => {
  llamadas.length = 0
  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    llamadas.push({
      url: String(url),
      method: init?.method ?? 'GET',
      body: init?.body ? JSON.parse(String(init.body)) : null,
    })
    return respuestaPara(String(url))   // fixtures del flujo
  }) as unknown as typeof fetch
})
```

---

## Qué afirmar

**1. Las peticiones.** Para cada acción del flujo: método, ruta y forma del
payload. No el payload entero byte a byte — las claves que importan.

**2. Las capacidades.** Que la persona puede hacer cada paso, buscado **por rol y
nombre accesible**:

```tsx
screen.getByRole('button', { name: /lanzar/i })
```

## Qué NO afirmar — esto es lo que más importa

**Nunca** clases CSS (`.eo-card`, `.eo-flow`, …), jerarquía de DOM, `container.
querySelector`, orden de columnas de una tabla, posición en pantalla, número de
elementos de una lista de presentación, ni textos de rótulo que sean decorativos.

Todo eso va a cambiar a propósito en los tramos 3 y 4. Un contrato que lo
afirme bloquea el trabajo en vez de protegerlo, y termina siendo editado — que es
exactamente el fallo que este contrato existe para impedir.

Si dudás si algo es capacidad o maquetación, preguntate: **¿si esto cambia, la
persona pierde algo que podía hacer?** Si la respuesta es no, no va al contrato.

---

## Los cuatro flujos

No inventes las rutas ni los payloads: **leelos del código de hoy** y congelá lo
que encuentres.

### Nueva corrida → lanzar (`ComposePage`)
- El preflight de los servicios se consulta al entrar.
- Con bloqueos presentes, el control de lanzar no está disponible y los bloqueos
  se le muestran a la persona.
- Sin bloqueos, se puede elegir fuente, modelo/destino y conjunto de prompts, y
  lanzar.
- Al lanzar sale la petición de creación de corrida, con la composición armada.
- Después de lanzar se navega al detalle de la corrida creada.

### Corrida en vivo (`Shell`, `RunDetailPage`)
- Con una corrida en curso, **el anuncio de corrida viva es alcanzable desde una
  ruta que no sea el listado** — este es el punto que protege la decisión D-3.
- Mientras la corrida está en curso, la consola vuelve a consultar el estado
  (hay más de una petición al recurso a lo largo del tiempo).
- Cuando ninguna corrida está en curso, **deja** de re-consultar.
- Existe el control de detener, y dispara su petición.

### Detalle, traza y evaluación (`RunDetailPage`)
- Se piden el detalle y la traza de la corrida.
- La línea de tiempo y el inspector de cuadros están disponibles cuando hay
  traza.
- Se puede disparar la evaluación, y sale su petición.
- El resultado de la evaluación se le muestra a la persona.

### Experimentos y distribución (`ExperimentsPage`, `ExperimentDetailPage`)
- Se lista y se puede abrir un experimento.
- Se puede derivar un experimento.
- Los **outcomes de distribución** se le muestran a la persona cuando el
  experimento los tiene. Esta es la feature que no existe en el árbol de
  referencia: sin este test, el rediseño puede borrarla sin que nadie se entere.
- Comparar corridas dispara su petición.

---

## Cierre

```bash
cd webconsole/frontend && npm test
```

- Los **387** tests que ya existían siguen verdes, sin editar ninguno.
- Los del contrato, verdes.
- `git status` muestra **sólo** archivos nuevos bajo `__tests__/contrato/`.
  Si aparece cualquier archivo de `src/` modificado, el tramo está mal.

Commit: `feat(webconsole): tramo 0 — contrato congelado del flujo troncal`
