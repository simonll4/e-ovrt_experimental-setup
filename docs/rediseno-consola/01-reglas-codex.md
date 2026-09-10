# Reglas del trabajo — leer antes de cada tramo

Se trabaja **un tramo por tarea**. No empieces el siguiente aunque sobre tiempo.

---

## 1. El árbol de referencia manda

Existe un worktree con el estado destino **ya verificado**:

```
.worktrees/front-design        commit 3500923
```

Es `d042ad1` (la rama `front-design`) aplicado sobre la rama operativa. Se midió:
742 tests de backend y 426 de frontend en verde, con dos defectos conocidos y
documentados en `00-diseno.md` §5.

**Tu trabajo en cada tramo es traer un subconjunto de archivos desde ese árbol.**
No es reescribir, no es reinterpretar, no es "portar el diseño". Cuando un tramo
lista un archivo, la versión correcta es la de `3500923`:

```bash
git show 3500923:<ruta> > <ruta>
```

Las únicas excepciones son las **desviaciones explícitas**, que están marcadas
como tales en el tramo que las contiene y tienen una decisión de `00-diseno.md`
§4 detrás. No inventes otras.

---

## 2. El contrato es de sólo lectura

Los archivos bajo `webconsole/frontend/src/__tests__/contrato/` **no se editan, no
se renombran, no se borran, no se marcan `skip` ni `xfail`, no se les cambia un
`expect`.**

Del lado del backend no hay carpeta de contrato aparte: **los 668 tests que ya
existen son el contrato**, y los protege la misma regla.

Si un test del contrato se pone rojo: **el trabajo está mal, no el test.**
Entendé la causa y arreglá el código. Si creés que el contrato está equivocado,
**pará y preguntá** — no lo toques.

Esto vale también para los tests que ya existían antes del trabajo. La única
modificación autorizada a un test preexistente es la de `00-diseno.md` §5.1, que
está decidida y es explícita.

---

## 3. Cierre de dependencias

Los tramos listan un conjunto de archivos que se calculó cerrado. Si aun así
`tsc` o `pytest` fallan porque falta un módulo o un tipo no encaja:

- **Sí:** traé ese módulo del árbol de referencia y anotalo en el reporte.
- **No:** parchear a mano, agregar un `any`, un `@ts-ignore`, un `# type: ignore`
  o un cast para que compile.

---

## 4. No expandas el alcance

- No refactorices nada que no esté en la lista del tramo.
- No renombres archivos, variables ni funciones por gusto.
- No actualices dependencias que el tramo no nombre.
- No arregles cosas que veas de paso: anotalas en el reporte y seguí.
- No toques `media-plane`, `control-plane` ni `alert-distribution`. Este trabajo
  vive entero en `webconsole/`.

---

## 5. Verificación — comandos exactos

Backend:

```bash
cd webconsole/backend && ./.venv/bin/python -m pytest -q
```

Frontend:

```bash
cd webconsole/frontend && npm test
```

Compilación del frontend:

```bash
cd webconsole/frontend && npm run build
```

**Línea de base al arrancar:** backend 668 verdes, frontend 387 verdes. Cada
tramo dice cuántos tiene que haber al cerrar.

---

## 6. Capturas

Desde el tramo 2 en adelante, además de los tests hay que mirar la pantalla.

- `webconsole/tools/seed_dev_data.py` (llega en el tramo 1) puebla la consola con
  corridas mock marcadas `[seed]`, **sin hardware**. `--purge` borra sólo eso.
- **No hay herramienta de capturas en el repo.** La instala el tramo 2: un script
  chico en `webconsole/tools/`, que levante la consola, recorra las doce rutas y
  escriba PNG a un directorio **gitignorado**.
- Antes y después de cada pantalla tocada, mismo ancho de ventana, mismos datos
  sembrados.
- Las capturas **no se commitean**.

---

## 7. Cómo se reporta

Al cerrar un tramo, el reporte tiene que traer:

1. La **salida real** de los comandos de verificación, pegada. No un resumen, no
   "todo verde": la salida.
2. La lista de archivos efectivamente tocados.
3. Cualquier archivo que hayas tenido que traer de más por §3.
4. Lo que viste y no arreglaste (§4).
5. Si algo quedó rojo: cuál, con la salida, y **no cierres el tramo**.

Un tramo con un test rojo no está cerrado, aunque el resto ande.

---

## 8. Git

- **Un commit por tramo**, al final, con el contrato verde.
- Mensaje: `feat(webconsole): tramo N — <qué>`.
- **No hagas merge. No hagas push. No toques `main`.** Eso lo hace el usuario.
- No agregues `Co-Authored-By`.
