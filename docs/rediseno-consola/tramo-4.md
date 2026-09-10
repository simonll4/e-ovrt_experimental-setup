# Tramo 4 — Resto de pantallas y armazón

Leé antes `01-reglas-codex.md`.

---

## Archivos, desde `3500923`

### Pantallas y armazón

```
webconsole/frontend/src/App.tsx
webconsole/frontend/src/components/Shell.tsx          ← con desviación, ver abajo
webconsole/frontend/src/pages/NotFoundPage.tsx        (nuevo)
webconsole/frontend/src/pages/CamerasPage.tsx
webconsole/frontend/src/pages/PlatformPage.tsx
webconsole/frontend/src/pages/ClipsPage.tsx
webconsole/frontend/src/pages/ComparePage.tsx
webconsole/frontend/src/pages/ExperimentsPage.tsx
webconsole/frontend/src/pages/ExperimentDetailPage.tsx
webconsole/frontend/src/pages/PromptSetsPage.tsx
webconsole/frontend/src/pages/CatalogPage.tsx
```

### Componentes y vistas

```
webconsole/frontend/src/experimentview.ts
webconsole/frontend/src/components/DeriveExperimentForm.tsx
webconsole/frontend/src/components/RecordPanel.tsx
```

### Tests

```
webconsole/frontend/src/__tests__/App.test.tsx
webconsole/frontend/src/__tests__/Shell.test.tsx
webconsole/frontend/src/__tests__/CamerasPage.test.tsx
webconsole/frontend/src/__tests__/PlatformPage.test.tsx
webconsole/frontend/src/__tests__/ClipsPage.test.tsx
webconsole/frontend/src/__tests__/ComparePage.test.tsx
webconsole/frontend/src/__tests__/ExperimentsPage.test.tsx
webconsole/frontend/src/__tests__/ExperimentsPage.new.test.tsx
webconsole/frontend/src/__tests__/ExperimentDetailPage.test.tsx
webconsole/frontend/src/__tests__/ExperimentDetailPageRiskBanner.test.tsx
webconsole/frontend/src/__tests__/PromptSetsPage.test.tsx
webconsole/frontend/src/__tests__/PromptSetEditor.test.tsx
webconsole/frontend/src/__tests__/DeriveExperimentForm.test.tsx
webconsole/frontend/src/__tests__/RecordPanel.test.tsx
webconsole/frontend/src/__tests__/PreviewWithBoxes.test.tsx
webconsole/frontend/src/__tests__/TrimDialog.test.tsx
webconsole/frontend/src/__tests__/spec44c_gate.test.tsx
webconsole/frontend/src/__tests__/useServiceHealth.test.ts
webconsole/frontend/src/__tests__/useSidebarCounts.test.ts
```

`useServiceHealth.test.ts` y `useSidebarCounts.test.ts` se adaptan en la
referencia para consultar las queries nuevas en vez de los hooks borrados. Si al
borrar los hooks esos tests quedan sin objeto, la referencia ya resolvió cómo
quedan: tomala.

---

## Desviación explícita: la píldora de corrida viva se repone

El `Shell.tsx` de la referencia **borra** la píldora, y lo documenta:

> Sin píldora de corrida viva: el banner del listado de Corridas ya anuncia la
> corrida en curso, y el prototipo lo diseñó así a propósito para no decir lo
> mismo en dos lugares.

**Decisión D-3: se conserva.** Traer `Shell.tsx` tal cual dejaría el contrato
rojo en este mismo corte, porque "corrida en vivo" es uno de los cuatro flujos
cubiertos y el contrato exige que el anuncio sea alcanzable **desde una ruta que
no es el listado**.

Ver que algo está corriendo sin tener que ir a buscarlo es capacidad, no
decoración — sobre todo en rodaje EBE.

**Qué hacer:**

- Traé `Shell.tsx` de la referencia y **reponé la píldora dentro**, con el
  lenguaje visual nuevo.
- Alimentala con **`useRunsEnCurso`** de `src/api/queries/runs.ts`. La referencia
  ya escribió esa consulta exactamente para esto — su docstring dice que de ahí
  salen «la píldora de la barra lateral, su contador y el banner del listado, con
  una sola petición liviana».
- El criterio del prototipo —no decir lo mismo en dos lugares— **se respeta con
  jerarquía visual**, no borrando la capacidad: la píldora es el aviso global
  discreto, el banner del listado es el detalle.
- `components/LiveRunPill.tsx` y su test: podés conservarlos re-maquetados o
  absorber la píldora dentro de `Shell.tsx`. Lo que **no** puede pasar es que la
  capacidad desaparezca.

---

## Borrado de hooks

Al cerrar este tramo **no debe quedar ninguno**. Misma regla mecánica del tramo 3:

```bash
grep -rn "useFullTrace\|useLiveRun\|usePreflight\|useServiceHealth\|useSidebarCounts\|useTarget" webconsole/frontend/src --include=*.ts --include=*.tsx
```

Sin resultados fuera de los tests que la referencia adaptó.

---

## Cierre

```bash
cd webconsole/frontend && npm test && npm run build
cd webconsole/backend && ./.venv/bin/python -m pytest -q
```

- **Contrato verde**, con especial atención al test que exige el anuncio de
  corrida viva fuera del listado.
- Suite completa verde. Comparado con la referencia debería haber **más** tests,
  no menos: los del contrato y los de distribución.
- Capturas de las doce rutas, antes y después.
- Ninguna ruta rota: `/` , `/compose`, `/catalog`, `/compare`, `/runs/:id`,
  `/platform`, `/experiments`, `/experiments/new`, `/experiments/:id`,
  `/prompts`, `/cameras`, `/clips`, más una URL inventada que tiene que caer en
  `NotFoundPage`.

Commit: `feat(webconsole): tramo 4 — resto de pantallas y armazón`
