# Referencia del prototipo — 01: armazón y componentes compartidos

Extracción del **lenguaje de componentes transversal** del prototipo
`rediseno-consola-eovrt/prototipo.html` (134 KB, autónomo, ~182 clases CSS).
Este documento cubre el **armazón** (barra lateral, barra superior, encabezado de
página, migas) y los **componentes reutilizables**. Las pantallas concretas se
documentan aparte.

Todo lo que aparece acá está copiado del prototipo, no inventado. Los fragmentos
HTML son los reales (el prototipo genera HTML por concatenación de strings; acá se
muestran normalizados a JSX-able pero con las clases y atributos exactos).

Convención de este documento en cada ficha:
**Para qué sirve** · **Estructura** · **CSS** · **Comportamiento** · **⚠ Dato**
(dependencia de datos que puede no existir en la API — la implementación no toca el
backend).

---

## 0. Fundaciones: tokens, tipografía, reglas globales

### 0.1 Tokens de color y forma

Van tal cual a `src/styles/tokens.css`. Son la totalidad de `:root` del prototipo.

```css
:root{
  color-scheme: dark;
  /* superficies (5 niveles) */
  --bg:#121211;      /* lienzo de la página — el MÁS oscuro */
  --s1:#1a1a19;      /* tarjeta / barra lateral */
  --s2:#212120;      /* elevado: inputs, th, seg, chips neutros, hover de fila */
  --s3:#2a2a28;      /* emergente: popovers, tooltips, botón segmentado activo */
  --sunken:#0d0d0c;  /* hundido: fondo de medidor, visor, carril de línea de tiempo */
  /* bordes */
  --bd:rgba(255,255,255,.09);   /* borde normal */
  --bds:rgba(255,255,255,.17);  /* borde fuerte (botón secundario, popover) */
  /* texto */
  --tx:#f2f1ed; --tx2:#b3b1a8; --tx3:#82807a; --tx4:#5c5b56;
  /* acento = acción / selección / foco / navegación activa */
  --ac:#7d6ef2; --ac-tx:#a89df6; --ac-bg:rgba(125,110,242,.14); --ac-bd:rgba(125,110,242,.42);
  /* estados */
  --live:#4b95e8; --live-bg:rgba(75,149,232,.14); --live-bd:rgba(75,149,232,.4);
  --ok:#35b45a;   --ok-bg:rgba(53,180,90,.14);   --ok-bd:rgba(53,180,90,.4);
  --wn:#e0a217;   --wn-bg:rgba(224,162,23,.13);  --wn-bd:rgba(224,162,23,.38);
  --sr:#ee8a5c;   --sr-bg:rgba(238,138,92,.13);  --sr-bd:rgba(238,138,92,.38);
  --er:#f0625f;   --er-bg:rgba(240,98,95,.13);   --er-bd:rgba(240,98,95,.4);
  --nt:#8a8880;   /* sin dato — no tiene -bg ni -bd: usa --s2/--bd */
  /* tipografía */
  --fs:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --fm:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  /* forma */
  --r:6px;    /* radio chico: botones, inputs, filas */
  --rc:10px;  /* radio de contenedor: tarjetas, KPI, línea de tiempo */
  --row:32px; /* altura de fila de tabla y de lista densa */
}
```

Regla que atraviesa todo: **el violeta `--ac` es acción**; el azul `--live` es
"esto está corriendo ahora". Nunca se intercambian.

El texto sobre botón primario/acento **no es blanco**: es `#150f3d` (violeta muy
oscuro). Aparece en `.newrun`, `.btn.pri`, `.tb-new`, `.num.on`.

Hover del acento: `#8b7df4` (no hay token; está literal en el prototipo).

### 0.2 Reglas globales

```css
*{box-sizing:border-box}
.wrap{background:var(--bg);color:var(--tx);font-family:var(--fs);font-size:13px;
      line-height:1.45;font-variant-numeric:tabular-nums;min-height:100vh}
button{font:inherit;font-variant-numeric:inherit;cursor:pointer}
:focus-visible{outline:2px solid var(--ac);outline-offset:1px;border-radius:3px}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}
.mono{font-family:var(--fm)}
code{font-family:var(--fm);font-size:.92em}
```

- Tamaño base 13 px. **Cifras tabulares globales** (`font-variant-numeric:tabular-nums`
  heredado a los `button`) — es lo que hace que las columnas numéricas alineen.
- `.mono` para todo identificador literal (`run_20260725_143012`, `unit_id`, rutas,
  nombres de clase, nombres de archivo, métricas).
- Números en español: coma decimal. Helper del prototipo:
  `const dec=(n,d)=>n.toFixed(d).replace(".",",")`.
- Escape obligatorio antes de inyectar texto (`esc()` en el prototipo); en React esto
  es gratis, pero conservar el criterio para `dangerouslySetInnerHTML` de SVG.

### 0.3 Set de iconos inline (`ic`)

Todos son SVG 16×16 `viewBox="0 0 16 16"`, `aria-hidden="true"`, `stroke="currentColor"`
salvo los rellenos. Se renderizan a 11–14 px. Conviene un módulo `src/components/ui/icons.tsx`.

| clave | uso | trazo | path |
|---|---|---|---|
| `stop` | Detener corrida | fill | `<rect x="4" y="4" width="8" height="8" rx="1"/>` |
| `play` | Lanzar / Activar / Nueva corrida | fill | `<path d="M4 3l9 5-9 5z"/>` |
| `warn` | Advertencia, alerta | 1.5 | `<path d="M8 2.6L14.4 13.9h-12.8z"/><path d="M8 6.6v3.1M8 11.6v.1"/>` |
| `chk` | Completada / Operativa / Cumple | 2 | `<path d="M3.5 8.5l3 3 6-7"/>` |
| `dl` | Descargar | 1.6 | `<path d="M8 2.5v8M4.5 7.5L8 11l3.5-3.5M3 13.5h10"/>` |
| `x` | Fallida / cerrar aviso | 1.8 | `<path d="M4 4l8 8M12 4l-8 8"/>` |
| `info` | Nota informativa | 1.5 | `<circle cx="8" cy="8" r="6"/><path d="M8 7.4v3.6M8 5.2v.1"/>` |
| `chev` | Cursor del desplegable | 1.7 | `<path d="M4 6.5L8 10.5l4-4"/>` |
| lupa | buscador | 1.6 | `<circle cx="7" cy="7" r="4.6"/><path d="M10.4 10.4L14 14"/>` |
| círculo vacío | paso pendiente del carril | 1.6 | `<circle cx="8" cy="8" r="5.6"/>` |

Los iconos de navegación (Corridas, Experimentos, Comparar, Conjuntos, Catálogos,
Plataforma, Cámaras, Clips) están en el bloque de la barra lateral (§2.4) y se copian
literalmente desde el prototipo, líneas 477–488.

---

## 1. Armazón: grilla de la aplicación

**Para qué sirve.** Dos columnas: barra lateral fija de 214 px y contenido. En
pantallas chicas la lateral desaparece y aparece la barra superior.

**Estructura.**

```html
<div class="wrap">
  <div class="topbar" id="topbar">…</div>   <!-- solo ≤760px -->
  <div class="app" id="app">                <!-- +class "col" si S.collapsed -->
    <nav class="side" aria-label="Navegación principal">…</nav>
    <main class="main" id="main">…</main>
  </div>
</div>
```

**CSS.**

```css
.app{display:grid;grid-template-columns:214px minmax(0,1fr);min-height:100vh;
     transition:grid-template-columns .16s ease}
.app.col{grid-template-columns:54px minmax(0,1fr)}
.side{border-right:1px solid var(--bd);background:var(--s1);padding:12px 9px;
      display:flex;flex-direction:column;gap:14px;position:sticky;top:0;height:100vh;
      overflow-y:auto;overflow-x:visible;z-index:50}
.main{min-width:0;display:flex;flex-direction:column}
.pad{padding:16px 20px}
```

**Puntos de quiebre** (los tres del prototipo):

```css
@media (max-width:1100px){
  .pane{grid-template-columns:minmax(0,1fr)}   /* traza: dos paneles → uno */
  .hero{grid-template-columns:minmax(0,1fr)}   /* plataforma */
  .compose{grid-template-columns:minmax(0,1fr)}
  .rail{position:static}
  .two{grid-template-columns:minmax(0,1fr)}
}
@media (max-width:760px){
  .topbar{display:grid} .side{display:none}
  .app,.app.col{grid-template-columns:minmax(0,1fr)}
  .lanes{padding-left:0} .lane .ln{display:none} .axis{margin-left:0}
  .rh .acts{margin-left:0;width:100%}
  .crumbs{flex-wrap:wrap;gap:6px 8px} .protoc{margin-left:0}
  /* padding lateral 20px → 14px en .pad,.kpis,.kpihd,.tabs,.tl,.rh,.crumbs */
}
@media (max-width:420px){.tb-brand span{display:none}}
```

**Grillas de contenido reutilizadas** (todas con `align-items:start`):

| clase | columnas | padding | uso |
|---|---|---|---|
| `.pane` | `300px minmax(0,1fr)`, gap 12 | `12px 20px 20px` | lista de cuadros + detalle |
| `.two` | `308px minmax(0,1fr)`, gap 12 | `13px 20px 22px` | lista maestra + detalle (prompts, clips) |
| `.compose` | `minmax(0,1fr) 292px`, gap 12 | `14px 20px 24px` | pasos + carril de verificación |
| `.hero` | `minmax(0,1.25fr) minmax(0,1fr)`, gap 12 | — | Plataforma: instancia activa + motores |
| `.grid2` | `repeat(auto-fit,minmax(238px,1fr))`, gap 12 | — | pares de tarjetas |
| `.kpis` | `repeat(auto-fit,minmax(146px,1fr))`, gap 9 | `7px 20px 0` | fila de KPI |

---

## 2. Barra lateral (`.side`)

Es el componente con más estados. Cinco piezas apiladas: marca, acción primaria,
grupos de navegación, y al pie el estado de los motores (`margin-top:auto`).

### 2.1 Marca + botón de colapso

```html
<div class="brand">
  <b>E-OVRT</b><span class="sub">consola</span>
  <button class="clp" id="clp" aria-label="Colapsar barra lateral" title="Colapsar barra lateral">
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true">
      <rect x="1.8" y="2.8" width="12.4" height="10.4" rx="1.6"/><path d="M6.4 2.8v10.4"/>
    </svg>
  </button>
</div>
```

```css
.brand{display:flex;align-items:center;gap:8px;padding:0 4px;width:100%}
.brand b{font-weight:500;font-size:14px;letter-spacing:-.01em}
.brand .sub{font-size:10px;color:var(--tx3);font-family:var(--fm)}
.clp{margin-left:auto;background:none;border:none;color:var(--tx3);padding:3px;border-radius:4px;display:flex;flex:none}
.clp:hover{background:var(--s2);color:var(--tx)}
.app.col .brand b,.app.col .brand .sub{display:none}
.app.col .clp{margin:0 auto}
```

**Comportamiento.** El icono es un rectángulo con una divisoria vertical (metáfora de
panel). Un solo botón, sin variante "expandir": alterna. `aria-label` fijo en
"Colapsar barra lateral" (el prototipo no lo cambia al colapsar — mejorable: usar
`aria-expanded`).

### 2.2 Botón de acción primaria

```html
<button class="newrun" data-screen="compose">
  <svg width="13" height="13" …><path d="M8 3v10M3 8h10"/></svg>
  <span>Nueva corrida</span>
  <span class="tip">Nueva corrida</span>
</button>
```

```css
.newrun{width:100%;height:31px;border:none;border-radius:var(--r);background:var(--ac);
        color:#150f3d;font-weight:500;font-size:12.5px;display:flex;align-items:center;
        justify-content:center;gap:6px;flex:none}
.newrun:hover{background:#8b7df4}
.app.col .newrun{width:38px;padding:0;position:relative}
.app.col .newrun span{display:none}   /* oculta también .tip; se re-muestra al hover */
```

### 2.3 Grupo de navegación

```html
<div class="navg" role="group" aria-label="Trabajo">
  <h3>Trabajo</h3>
  …items…
</div>
```

```css
.navg{display:flex;flex-direction:column;gap:1px;width:100%}
.navg h3{font-size:10.5px;font-weight:400;color:var(--tx4);margin:0 0 4px;padding:0 8px;letter-spacing:.02em}
.app.col .navg h3{display:none}
.app.col .navg{align-items:center;padding-top:8px;border-top:1px solid var(--bd)}
.app.col .navg:first-of-type{border-top:none;padding-top:0}
```

Al colapsar, el título del grupo se reemplaza por una **línea divisoria superior**:
el agrupamiento sobrevive sin texto.

Los tres grupos y sus ítems (idénticos en la lateral y en la barra superior; el
prototipo los duplica en la constante `MENU`):

```js
const MENU=[
  {t:"Trabajo",      items:[{k:"runs",l:"Corridas",ct:"1"},{k:"exps",l:"Experimentos",ct:"5"},{k:"cmp",l:"Comparar"}]},
  {t:"Definiciones", items:[{k:"psets",l:"Conjuntos de prompts",ct:"3"},{k:"cat",l:"Catálogos"}]},
  {t:"Sistema",      items:[{k:"platform",l:"Plataforma"},{k:"cams",l:"Cámaras"},{k:"clips",l:"Clips"}]}
];
```

### 2.4 Ítem de navegación (`.nav`)

```html
<button class="nav" data-screen="runs" aria-current="page">
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true">…</svg>
  <span class="lb">Corridas</span>
  <span class="ct">1</span>
  <span class="tip">Corridas</span>
</button>
```

```css
.nav{display:flex;align-items:center;gap:9px;padding:6px 8px;border-radius:5px;color:var(--tx2);
     background:none;border:none;width:100%;text-align:left;font-size:12.5px;position:relative}
.nav svg{flex:none;opacity:.85}
.nav:hover{background:var(--s2);color:var(--tx)}
.nav:hover svg{opacity:1}
.nav[aria-current="page"]{background:var(--ac-bg);color:var(--ac-tx)}
.nav[aria-current="page"] svg{opacity:1}
.nav .ct{margin-left:auto;font-family:var(--fm);font-size:10.5px;color:var(--tx3)}
.nav[aria-current="page"] .ct{color:var(--ac-tx)}
.app.col .nav{width:38px;justify-content:center;padding:7px 0}
.app.col .nav .lb,.app.col .nav .ct{display:none}
```

**Contadores** (`.ct`): Corridas = corridas en curso; Experimentos = manifiestos;
Conjuntos de prompts = conjuntos. Comparar, Catálogos, Plataforma, Cámaras y Clips
**no llevan contador**. El contador se omite si no hay dato — no se muestra `0`.

**Ítem activo derivado.** El estado activo no es 1:1 con la pantalla: hay un mapa de
pantallas hijas a ítem padre.

```js
const mapa={run:"runs", compose:"runs", expd:"exps"};
const activo = mapa[S.screen] || S.screen;
document.querySelectorAll(".nav[data-screen]").forEach(b=>{
  if(b.dataset.screen===activo) b.setAttribute("aria-current","page");
  else b.removeAttribute("aria-current");
});
```

**Iconos por ítem** (SVG 16×16, trazo 1.4, tomados de las líneas 477–488 del prototipo):

- Corridas: `M2.5 4h11M2.5 8h6M2.5 12h6` + `M11.2 9.6l3 1.9-3 1.9z` (lista con play)
- Experimentos: matraz `M6.3 2v4.2L2.9 12a1.4 1.4 0 0 0 1.2 2.1h7.8A1.4 1.4 0 0 0 13.1 12L9.7 6.2V2` + `M5.4 2h5.2M4.7 10h6.6`
- Comparar: `M2.5 13.5h11` + tres `rect` (barras) `3.4/7/2.6/4.4`, `7.2/3.6/2.6/7.8`, `11/8.8/2.6/2.6`
- Conjuntos de prompts: globo de diálogo `M2.4 3.6a1.2 1.2 0 0 1 1.2-1.2h8.8a1.2 1.2 0 0 1 1.2 1.2v6a1.2 1.2 0 0 1-1.2 1.2H6.6L3.4 13.4v-2.6a1.2 1.2 0 0 1-1-1.2z` + `M5.2 5.6h5.6M5.2 7.8h3.4`
- Catálogos: capas `M8 3.4L2.4 6 8 8.6 13.6 6z` + `M2.4 9.2L8 11.8l5.6-2.6` + `M2.4 12.2L8 14.8l5.6-2.6`
- Plataforma: dos `rect` apilados `2.2/2.6/11.6/4.4 rx1.2` y `2.2/9/11.6/4.4 rx1.2` + `M4.8 4.8v.01M4.8 11.2v.01`
- Cámaras: `rect 1.8/4.4/12.4/8.2 rx1.4` + `circle 8,8.5 r2.4` + `M5.6 4.4l.9-1.6h3l.9 1.6`
- Clips: `rect 1.8/3.2/12.4/9.6 rx1.4` + `M5.2 3.2v9.6M10.8 3.2v9.6M1.8 8h12.4`

### 2.5 Tooltip de colapsado (`.tip`)

```css
.tip{display:none;position:absolute;left:calc(100% + 9px);top:50%;transform:translateY(-50%);
     background:var(--s3);border:1px solid var(--bds);color:var(--tx);font-size:11.5px;
     padding:3px 8px;border-radius:5px;white-space:nowrap;z-index:40;pointer-events:none;
     box-shadow:0 4px 14px rgba(0,0,0,.5)}
.app.col .nav:hover .tip,.app.col .newrun:hover .tip{display:block}
```

Solo aparece **con la barra colapsada**. Es CSS puro, no JS. `pointer-events:none`.
Depende de `.side{overflow-x:visible}` y `.app.col .side{overflow:visible}` para no
recortarse.

### 2.6 Estado de los motores al pie (`.svcs`)

```html
<div class="svcs" aria-label="Estado de los servicios">
  <div class="svc">
    <span class="dot" style="background:var(--ok)"></span>
    <span class="lb">Motor de detección</span><code>:8080</code>
    <span class="tip">Motor de detección — operativo</span>
  </div>
  <div class="svc" id="svcCtl">
    <span class="dot" style="background:var(--ok)"></span>
    <span class="lb">Motor de reglas</span><code>:8081</code>
    <span class="tip" id="tipCtl">Motor de reglas — operativo</span>
  </div>
</div>
```

```css
.svcs{margin-top:auto;border-top:1px solid var(--bd);padding-top:9px;
      display:flex;flex-direction:column;gap:5px;width:100%}
.svc{display:flex;align-items:center;gap:7px;padding:0 8px;font-size:11px;color:var(--tx3);position:relative}
.svc .dot{width:6px;height:6px;border-radius:50%;flex:none}
.svc code{font-size:10px;margin-left:auto;color:var(--tx4)}
.app.col .svc{justify-content:center;padding:2px 0}
.app.col .svc .lb,.app.col .svc code{display:none}   /* queda solo el punto */
```

**Comportamiento.** El punto es `var(--ok)` operativo / `var(--er)` sin respuesta, y
el tooltip cambia el texto en paralelo:

```js
document.querySelector("#svcCtl .dot").style.background = S.ctlDown?"var(--er)":"var(--ok)";
document.getElementById("tipCtl").textContent = "Motor de reglas — "+(S.ctlDown?"sin respuesta":"operativo");
```

Colapsado quedan solo dos puntos de color apilados — **acá el color va solo**; es la
única excepción a "nunca color sin texto", mitigada por el tooltip al hover.

⚠ **Dato.** Requiere un sondeo periódico de salud de ambos planos
(`GET :8080/healthz`, `:8081`). El puerto se muestra literal; si el BFF proxea, hay
que exponer la URL/puerto real de cada motor.

### 2.7 Estado de colapsado

`S.collapsed` es booleano en el estado global; se aplica con
`document.getElementById("app").classList.toggle("col", S.collapsed)`.
No se persiste en el prototipo (se pierde al recargar) — **en la implementación
conviene persistirlo en `localStorage`**. Transición de 160 ms sobre
`grid-template-columns`; ancho colapsado 54 px, ítems de 38 px centrados.

---

## 3. Barra superior (`.topbar`) — solo ≤760 px

**Para qué sirve.** Reemplaza la barra lateral en pantallas chicas. Grilla de tres
columnas con la marca a la izquierda y un grupo de botones-icono centrado, cada uno
abriendo un panel desplegable a ancho completo. **No lleva migas ni buscador**: las
migas viven en el contenido (§4).

```html
<div class="topbar" id="topbar">
  <div class="tb-brand"><b>E-OVRT</b><span>consola</span></div>
  <div class="tb-mid">
    <button class="tb-g" data-menu="0" aria-expanded="false" aria-label="Trabajo" title="Trabajo">…</button>
    <button class="tb-g" data-menu="1" aria-expanded="false" aria-label="Definiciones">…</button>
    <button class="tb-new" data-screen="compose" aria-label="Nueva corrida">…+…</button>
    <button class="tb-g" data-menu="2" aria-expanded="false" aria-label="Sistema">…</button>
    <button class="tb-g" data-menu="3" aria-expanded="false" aria-label="Estado de los servicios">
      <svg …><path d="M1.6 8h3.1l1.8-4.4 2.7 8.8 1.6-4.4h3.6"/></svg>   <!-- electrocardiograma -->
      <span class="sdot" id="tbdot" style="background:var(--ok)"></span>
    </button>
  </div>
  <div></div>
  <div class="tb-pop" id="tbpop"></div>
</div>
```

```css
.topbar{display:none;grid-template-columns:1fr auto 1fr;align-items:center;gap:10px;padding:8px 14px;
        background:var(--s1);border-bottom:1px solid var(--bd);position:sticky;top:0;z-index:60}
.tb-g{width:34px;height:32px;border-radius:7px;border:1px solid transparent;background:none;color:var(--tx2);
      display:flex;align-items:center;justify-content:center;position:relative}
.tb-g:hover{background:var(--s2);color:var(--tx)}
.tb-g[aria-expanded="true"]{background:var(--ac-bg);color:var(--ac-tx);border-color:var(--ac-bd)}
.tb-g .sdot{position:absolute;top:4px;right:4px;width:7px;height:7px;border-radius:50%;border:1.5px solid var(--s1)}
.tb-new{width:42px;height:32px;border-radius:8px;border:none;background:var(--ac);color:#150f3d;margin:0 4px;flex:none}
.tb-pop{grid-column:1/-1;display:none;margin:8px -14px -8px;padding:10px 14px;
        border-top:1px solid var(--bd);background:var(--s2)}
.tb-pop.open{display:block}
.tb-pop h4{margin:0 0 7px;font-size:10.5px;font-weight:400;color:var(--tx4)}
.tb-it{display:flex;align-items:center;gap:9px;width:100%;background:none;border:none;color:var(--tx2);
       padding:8px 9px;border-radius:6px;font-size:13px;text-align:left}
.tb-it:hover{background:var(--s3);color:var(--tx)}
.tb-it[aria-current="page"]{background:var(--ac-bg);color:var(--ac-tx)}
.tb-it .ct{margin-left:auto;font-family:var(--fm);font-size:10.5px;color:var(--tx3)}
.tb-sv{display:flex;align-items:center;gap:10px;padding:7px 9px}
.tb-sv .w b{font-weight:500;font-size:12.5px;display:block}
.tb-sv .w span{font-size:11px;color:var(--tx3);font-family:var(--fm)}
```

**Comportamiento** (`S.menu` = índice 0–3 o `null`):

```js
// clic en un [data-menu]: alterna y cierra el desplegable propio
S.menu = (S.menu===i ? null : i); S.dd = null;
// Escape cierra menú y desplegable
// clic en cualquier otro lado también cierra ambos
```

Los menús 0–2 se renderizan desde `MENU[S.menu]` (mismo catálogo que la lateral);
el menú 3 es el panel de servicios, con chip de estado + nombre + `localhost:puerto`:

```html
<h4>Estado de los servicios</h4>
<div class="tb-sv"><span class="chip c-ok">✓ Operativo</span>
  <span class="w"><b>Motor de detección</b><span>localhost:8080</span></span></div>
<div class="tb-sv"><span class="chip c-er">✕ Sin respuesta</span>
  <span class="w"><b>Motor de reglas</b><span>localhost:8081</span></span></div>
```

El `.sdot` del botón 3 refleja el peor estado de los dos motores
(`S.ctlDown ? var(--er) : var(--ok)`).

---

## 4. Migas de pan (`.crumbs`)

**Para qué sirve.** Primera línea de la zona de contenido, sobre el encabezado.
Siempre presente. Segmentos separados por `/`; el último es el actual (no navegable,
`color:var(--tx2)`, en `.mono` cuando es un identificador).

```html
<!-- estático: grupo / pantalla -->
<div class="crumbs"><span>Trabajo</span><span>/</span><span style="color:var(--tx2)">Corridas</span></div>

<!-- con vuelta atrás: el primer segmento es <button> -->
<div class="crumbs">
  <button data-screen="runs">Corridas</button><span>/</span>
  <span class="mono" style="color:var(--tx2)">run_20260725_143012</span>
  <span class="protoc">…interruptor del prototipo…</span>
</div>
```

```css
.crumbs{display:flex;align-items:center;gap:6px;padding:9px 20px;font-size:11.5px;
        color:var(--tx3);border-bottom:1px solid var(--bd)}
.crumbs button{background:none;border:none;color:var(--tx3);padding:0;font-size:11.5px}
.crumbs button:hover{color:var(--ac-tx)}
```

Migas por pantalla: `Trabajo / Corridas`, `Corridas / run_…`, `Corridas / Nueva corrida`,
`Trabajo / Experimentos`, `Experimentos / exp_…`, `Trabajo / Comparar`,
`Definiciones / Conjuntos de prompts`, `Definiciones / Catálogos`, `Sistema / Plataforma`,
`Sistema / Cámaras`, `Sistema / Clips`. El primer segmento coincide con el título del
grupo de la barra lateral.

**Lo demás que vive en la barra de migas: `.protoc`** — el interruptor "Estado del
prototipo" (Corridas y Detalle de corrida) y el botón "Simular caída" (Plataforma).

```css
.protoc{margin-left:auto;display:flex;align-items:center;gap:7px;font-size:10.5px;color:var(--tx4)}
.protoc .sw{display:flex;background:var(--s2);border:1px solid var(--bd);border-radius:5px;padding:2px}
.protoc .sw button{padding:2px 8px;border-radius:3px;font-size:10.5px;color:var(--tx3);border:none;background:none}
.protoc .sw button[aria-pressed="true"]{background:var(--s3);color:var(--tx2)}
```

> **NO IMPLEMENTAR.** `.protoc` es andamiaje del prototipo para ver los dos estados
> sin esperar; el README lo dice explícitamente. Se documenta solo para que nadie lo
> confunda con parte del diseño. La zona `margin-left:auto` de las migas queda libre.

---

## 5. Encabezado de página (`.rh`)

**Para qué sirve.** Título grande + línea de contexto + acciones a la derecha.
Es el mismo componente en las 11 pantallas; lo que cambia es el contenido de `.meta`
y de `.acts`.

```html
<header class="rh">
  <div>
    <h1>Ronda nocturna — cámara 04</h1>
    <div class="meta">…</div>
  </div>
  <div class="acts">…</div>
</header>
```

```css
.rh{display:flex;align-items:flex-start;gap:12px;padding:14px 20px 12px;
    border-bottom:1px solid var(--bd);flex-wrap:wrap}
.rh h1{margin:0;font-size:20px;font-weight:500;letter-spacing:-.015em;line-height:1.2}
.rh .meta{display:flex;align-items:center;gap:8px;margin-top:5px;flex-wrap:wrap;
          font-size:11.5px;color:var(--tx3)}
.rh .meta .sep{color:var(--tx4)}          /* el "·" entre datos */
.rh .acts{margin-left:auto;display:flex;gap:7px;align-items:center}
@media (max-width:760px){.rh .acts{margin-left:0;width:100%}}
```

### Variantes de `.meta` (todas reales)

**A. Listado con conteo — Corridas.** Texto plano, con el "en curso" en `--live`:

```html
<div class="meta">
  <span>9 en total</span>
  <span class="sep">·</span><span style="color:var(--live)">1 en curso</span>
</div>
<div class="acts"><button class="btn pri">▶ Nueva corrida</button></div>
```

El segundo tramo se omite entero si no hay corridas en curso.

**B. Frase explicativa — Nueva corrida, Comparar, Conjuntos, Catálogos, Cámaras.**
Un solo `<span>` con una oración en minúscula-descriptiva
("Elegí de dónde salen las imágenes y qué se busca en ellas",
"Solo se comparan corridas ya evaluadas contra un conjunto anotado",
"Todo lo que la consola puede usar, y por qué algo no está disponible").

**C. Recuento compuesto — Clips, Experimentos.**
`"3 materiales · 7 clips recortados"`, `"5 manifiestos versionados en el repositorio"`.

**D. Chips + identificadores — Detalle de corrida** (la más cargada):

```html
<div class="meta">
  <span class="chip c-live"><span class="pulse"></span>En curso</span>   <!-- o c-ok ✓ Completada -->
  <span class="chip c-nt">Un solo equipo</span>                          <!-- despliegue -->
  <span class="sep">·</span><span class="mono">run_20260725_143012</span>
  <span class="sep">·</span><span>Cámara cam-04</span>
  <span class="sep">·</span><span>24,8 s y contando</span>               <!-- o "Duró 24,8 s" -->
</div>
<div class="acts">
  <button class="btn dg">■ Detener</button>                              <!-- solo en curso -->
  <button class="btn" disabled title="Los archivos se generan al terminar">⤓ Archivos</button>
  <button class="btn gh" disabled title="No se puede borrar una corrida en curso">Borrar</button>
</div>
```

Reglas de la variante D:
- "Detener" **solo existe** si la corrida está en curso (no se deshabilita: desaparece).
- "Archivos" y "Borrar" están **deshabilitados con `title` que explica el motivo**
  mientras la corrida corre. El motivo siempre se dice, nunca se deja el botón mudo.
- Los chips de contexto no son de estado (`c-nt` neutro): "Un solo equipo" /
  "Dos equipos" es información de despliegue.

**E. Chips de resultado — Detalle de experimento:**

```html
<div class="meta">
  <span class="chip c-ok">✓ Todos los criterios cumplen</span>
  <!-- o: <span class="chip c-sr">⚠ 2 criterios sin cumplir</span> -->
  <span class="sep">·</span><span class="mono">exp_20260725_1120</span>
  <span class="sep">·</span><span>hace 3 h</span>
</div>
<div class="acts">
  <button class="btn">Ver la corrida</button>
  <button class="btn gh">Descargar reporte</button>
</div>
```

⚠ **Dato.** "hace 4 min / hace 3 h" requiere una fecha de creación explícita; hoy
solo se puede derivar parseando el `run_id` (frágil — punto 7 del README). Helper:

```js
function hace(m){ if(m<60) return "hace "+m+" min";
  const h=Math.floor(m/60); if(h<24) return "hace "+h+" h";
  return "hace "+Math.floor(h/24)+" d"; }
```

---

## 6. Botones (`.btn`)

**Para qué sirve.** Un único componente con cuatro jerarquías. Altura 28 px
(los del carril de lanzamiento suben a 32 px con `.launch .btn`).

```css
.btn{height:28px;padding:0 10px;border-radius:var(--r);border:1px solid var(--bds);
     background:transparent;color:var(--tx);display:inline-flex;align-items:center;gap:5px;font-size:12px}
.btn:hover{background:var(--s2)}
.btn.pri{background:var(--ac);border-color:var(--ac);color:#150f3d;font-weight:500}
.btn.pri:hover{background:#8b7df4}
.btn.dg{border-color:var(--er-bd);color:var(--er)}
.btn.dg:hover{background:var(--er-bg)}
.btn.gh{border-color:transparent;color:var(--tx3)}
.btn.gh:hover{color:var(--tx);background:var(--s2)}
.btn[disabled]{opacity:.42;cursor:not-allowed}
.btn[disabled]:hover{background:transparent}
```

| variante | uso | ejemplos |
|---|---|---|
| `.btn` (secundario) | acción neutra visible | Archivos, Ver en vivo, Ver la corrida, Activar |
| `.btn.pri` | acción primaria de la pantalla, **una sola** | Nueva corrida, Lanzar corrida, Agregar cámara, Nuevo conjunto |
| `.btn.dg` | destructiva/interruptora | Detener, Apagar, Sí borrar |
| `.btn.gh` (fantasma) | terciaria, aparece al hover de fila | Borrar, Descargar, Partir de este, `‹ ›` de navegación |

Convención: icono a la izquierda del texto (`ic.play`, `ic.stop`, `ic.dl`), gap 5 px.
Botón solo-icono: `aria-label` obligatorio.

**Botones fantasma en filas** — se ocultan hasta el hover, con excepciones para foco
de teclado y para el estado de confirmación:

```css
td.act .btn{opacity:0;transition:opacity .1s}
tr:hover td.act .btn, td.act .btn:focus-visible, td.act .btn.stay{opacity:1}
```

`.stay` es la clase que fuerza visibilidad durante la confirmación de borrado.

**Confirmación destructiva en dos pasos** (in-place, sin modal):

```html
<span class="delc">¿Borrar?
  <button class="btn dg stay" data-delok="run_…">Sí, borrar</button>
  <button class="btn gh stay" data-delno="1">No</button>
</span>
```
```css
.delc{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;color:var(--tx2)}
```
Estado: `S.del = <id o null>`. Se limpia al cambiar de filtro, de búsqueda o de pantalla.

**Enlace de texto (`.lnk`)** — usado para identificadores navegables dentro de tablas:

```css
.lnk{background:none;border:none;padding:0;font:inherit;font-family:var(--fm);
     color:var(--ac-tx);cursor:pointer;text-align:left}
.lnk:hover{text-decoration:underline}
```

---

## 7. Controles de filtro

### 7.1 Buscador (`.search`)

```html
<div class="search">
  <span class="mg"><svg width="13" height="13" …><circle cx="7" cy="7" r="4.6"/><path d="M10.4 10.4L14 14"/></svg></span>
  <input id="qsearch" placeholder="Buscar por nombre o identificador" value="…" aria-label="Buscar corridas">
</div>
```

```css
.search{position:relative;flex:1;min-width:180px;max-width:300px}
.search input{width:100%;height:30px;background:var(--s2);border:1px solid var(--bd);border-radius:var(--r);
              color:var(--tx);padding:0 9px 0 30px;font-size:12px;font-family:inherit}
.search input::placeholder{color:var(--tx4)}
.search .mg{position:absolute;left:9px;top:50%;transform:translateY(-50%);color:var(--tx3);display:flex}
```

Filtra en vivo (`input`), sin botón ni debounce en el prototipo. Sobre nombre **e**
identificador: `(r.nm+" "+r.id).toLowerCase().includes(q)`.
Placeholder por pantalla: "Buscar por nombre o identificador" (Corridas),
"Buscar en materiales y clips" (Clips).

⚠ **Dato / cuidado de implementación.** El prototipo re-renderiza todo en cada
pulsación y restaura foco y posición del cursor a mano
(`document.activeElement.id` + `setSelectionRange`). En React con estado controlado
esto es innecesario. Si se pasa a filtrado del lado del servidor (punto 5 del README:
`?estado=&q=&orden=&pagina=`), hace falta debounce.

### 7.2 Barra de herramientas (`.toolbar`)

Contenedor de buscador + segmentado + contador. Vive entre el encabezado y la tabla.

```css
.toolbar{display:flex;align-items:center;gap:9px;flex-wrap:wrap;padding:13px 20px 0}
.cnt{margin-left:auto;font-size:11px;color:var(--tx4);font-family:var(--fm)}
```

### 7.3 Segmentado de filtro (`.seg`)

```html
<div class="seg">
  <button data-fst="all" aria-pressed="true">Todas</button>
  <button data-fst="run" aria-pressed="false">En curso</button>
  <button data-fst="ok"  aria-pressed="false">Completadas</button>
  <button data-fst="err" aria-pressed="false">Fallidas</button>
</div>
```

```css
.seg{display:inline-flex;background:var(--s2);border:1px solid var(--bd);border-radius:var(--r);padding:2px}
.seg button{padding:3px 10px;border-radius:4px;font-size:12px;color:var(--tx3);border:none;background:none}
.seg button:hover{color:var(--tx2)}
.seg button[aria-pressed="true"]{background:var(--s3);color:var(--tx)}
```

Selección única, `aria-pressed`. **Sin contadores** — el conteo del resultado va en
`.cnt` ("9 de 9"). Elegir un filtro limpia la confirmación de borrado pendiente.

### 7.4 Pestañas subrayadas (`.tabs` / `.tab`)

Distinto componente del anterior: navega entre secciones de una misma pantalla
(Traza / Resumen / Evaluación / Archivos, en Detalle de corrida). Lleva contador.

```html
<div class="tabs" role="tablist">
  <button class="tab" role="tab" data-tab="traza" aria-selected="true">Traza<span class="n">60</span></button>
  <button class="tab" role="tab" data-tab="resumen" aria-selected="false">Resumen</button>
  <button class="tab" role="tab" data-tab="eval" aria-selected="false">Evaluación</button>
  <button class="tab" role="tab" data-tab="arch" aria-selected="false">Archivos<span class="n">4</span></button>
</div>
```

```css
.tabs{display:flex;gap:2px;padding:14px 20px 0;border-bottom:1px solid var(--bd);margin-top:14px}
.tab{background:none;border:none;border-bottom:2px solid transparent;color:var(--tx3);
     padding:6px 11px 8px;font-size:12.5px;margin-bottom:-1px;display:flex;align-items:center;gap:6px}
.tab:hover{color:var(--tx)}
.tab[aria-selected="true"]{color:var(--tx);border-bottom-color:var(--ac)}
.tab .n{font-family:var(--fm);font-size:10.5px;background:var(--s2);border-radius:999px;padding:0 5px;color:var(--tx3)}
```

El `margin-bottom:-1px` monta el subrayado sobre el borde del contenedor.
El contador se omite (`null`) cuando no aplica. Falta soportar navegación por flechas
(`role="tablist"` está, el manejo de teclado no).

### 7.5 Desplegable propio (`.dd`)

**Para qué sirve.** Reemplaza al `<select>` nativo, que se dibuja con el estilo del
sistema operativo. Aporta lo que el nativo no da bien: **opciones deshabilitadas con
su motivo visible en la etiqueta**.

```html
<div class="dd open">
  <button class="ddb" data-dd="cdataset" aria-haspopup="listbox" aria-expanded="true">
    <span class="ddv ph">Indicar una ruta a mano</span>   <!-- .ph = placeholder -->
    <span class="ddc">⌄</span>
  </button>
  <div class="ddp" role="listbox">
    <button class="ddo" role="option" aria-selected="true" data-ddpick="cdataset|seguridad_nocturno_v2">
      <span>seguridad_nocturno_v2</span><span class="k">✓</span>
    </button>
    <button class="ddo" role="option" aria-selected="false" data-ddpick="cdataset|perimetro_lluvia" disabled>
      <span>perimetro_lluvia — no montado</span>
    </button>
  </div>
</div>
```

```css
.dd{position:relative}
.ddb{width:100%;height:30px;background:var(--s2);border:1px solid var(--bd);border-radius:var(--r);
     color:var(--tx);padding:0 9px;font-size:12px;font-family:inherit;display:flex;align-items:center;gap:8px;text-align:left}
.ddb:hover:not([disabled]){border-color:var(--bds)}
.dd.open .ddb{border-color:var(--ac-bd)}
.ddb[disabled]{opacity:.45;cursor:not-allowed}
.ddb .ddv{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ddb .ddv.ph{color:var(--tx4)}
.ddb .ddc{color:var(--tx3);flex:none;display:flex;transition:transform .12s ease}
.dd.open .ddb .ddc{transform:rotate(180deg)}
.ddp{position:absolute;top:calc(100% + 4px);left:0;right:0;z-index:30;background:var(--s3);
     border:1px solid var(--bds);border-radius:8px;padding:4px;box-shadow:0 8px 26px rgba(0,0,0,.55);
     max-height:212px;overflow-y:auto}
.ddo{display:flex;align-items:center;gap:8px;width:100%;background:none;border:none;color:var(--tx2);
     padding:6px 8px;border-radius:5px;font-size:12px;text-align:left;font-family:inherit}
.ddo:hover:not([disabled]){background:var(--s2);color:var(--tx)}
.ddo[aria-selected="true"]{color:var(--ac-tx)}
.ddo[disabled]{opacity:.4;cursor:not-allowed}
.ddo .k{margin-left:auto;flex:none}
```

**API del prototipo.** `dd(id, opts, val, o)` donde:
- `id`: clave única, también es el identificador del estado abierto (`S.dd`) y la
  clave de despacho en `setDD`.
- `opts`: array de tuplas `[valor, etiqueta, deshabilitado?]`.
- `val`: valor actual.
- `o.ph`: placeholder (por defecto `"— Elegir —"`); `o.dis`: deshabilita el control entero.

**El motivo del deshabilitado va concatenado en la etiqueta**, con guion largo:

```js
DATASETS.map(d=>[d.id, d.id+(d.on?"":" — no montado"), !d.on])   // conjunto no montado
SETS.map(x=>[x.id, x.id+(x.cong?" — congelado":"")])              // informativo, no deshabilita
CAMS.map(c=>[c.id, c.nom])
```

**Comportamiento.**
- Un solo desplegable abierto a la vez: `S.dd` guarda el `id` o `null`.
- Abrir un desplegable cierra el menú de la barra superior (`S.menu=null`) y viceversa.
- Clic fuera cierra; `Escape` cierra.
- Al elegir: `setDD(id, valor)` aplica el efecto según `id` y hace `S.dd=null`.
  Nótese que `setDD` tiene efectos en cascada: elegir conjunto de prompts (`cset`)
  **reinicia las clases activas** a todas las del conjunto.
- El valor elegido lleva `✓` (`ic.chk`) alineado a la derecha (`.ddo .k`).

**Deuda de accesibilidad a cubrir en la implementación**: no hay navegación por
flechas, ni `aria-activedescendant`, ni retorno de foco al botón al cerrar. El
prototipo solo cubre clic + Escape.

⚠ **Dato.** El motivo del deshabilitado necesita venir del backend. Hoy los plugins
de ingesta exponen `enabled` booleano y la interfaz solo puede decir "no soportado";
el prototipo muestra "El motor de detección no tiene instalado el SDK DepthAI"
(punto 6 del README). Sin ese dato, la opción se deshabilita con un motivo genérico.

### 7.6 Casillas de verificación

Dos formas, ambas con `accent-color:var(--ac)`.

**`.tog`** — casilla inline en cabeceras de lista ("Solo con actividad", "Solo alertas"):

```html
<label class="tog"><input type="checkbox" id="fAct" checked>Solo con actividad</label>
```
```css
.tog{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;color:var(--tx2);cursor:pointer;user-select:none}
.tog input{accent-color:var(--ac);width:13px;height:13px;margin:0}
```

Los dos filtros de la traza son **mutuamente excluyentes de forma asimétrica**:
marcar "Solo alertas" desmarca y **deshabilita** "Solo con actividad".

```js
if(id==="fAct"){S.act=e.target.checked;}
if(id==="fAl"){S.onlyAlert=e.target.checked; if(e.target.checked)S.act=false;}
```

**`.pick`** — fila-casilla seleccionable de lista (Comparar):

```html
<label class="pick"><input type="checkbox" data-cmp="run_…" checked>
  <span class="w"><b>Barrido diurno — portón sur</b><span>owlv2-base-patch16 · seguridad/nocturno · hace 2 h</span></span>
</label>
```
```css
.pick{display:flex;align-items:center;gap:9px;padding:8px 11px;border-bottom:1px solid var(--bd);font-size:12px;cursor:pointer}
.pick:last-of-type{border-bottom:none}
.pick:hover{background:var(--s2)}
.pick input{accent-color:var(--ac);width:14px;height:14px;margin:0;flex:none}
.pick .w{flex:1;min-width:0}
.pick .w b{font-weight:400;color:var(--tx);display:block}
.pick .w span{font-size:10.5px;color:var(--tx4);font-family:var(--fm)}
```

### 7.7 Campos de formulario

```css
.fld{padding:0 12px 12px;display:flex;flex-direction:column;gap:5px}
.fld > label{font-size:11.5px;color:var(--tx2)}
.fld .hint{font-size:10.5px;color:var(--tx4);line-height:1.45}
.inp{height:30px;width:100%;background:var(--s2);border:1px solid var(--bd);border-radius:var(--r);
     color:var(--tx);padding:0 9px;font-size:12px;font-family:inherit}
.inp::placeholder{color:var(--tx4)}
.inp:focus{border-color:var(--ac-bd)}
.inp.bad{border-color:var(--er-bd)}
textarea.inp{height:auto;min-height:58px;padding:7px 9px;line-height:1.5;resize:vertical;font-size:12px}
.card > h3 + .fld,.card > h3 + .esec + .fld{padding-top:13px}
.rng{width:100%;accent-color:var(--ac);height:18px}
```

`.hint` cambia a `color:var(--wn)` cuando explica un problema recuperable
(p. ej. "Los manifiestos guardados ocultan la contraseña. Recompletala antes de lanzar.")
y a `var(--ok)` cuando confirma un guardado.

**Píldora conmutable (`.cls`)** — activar/desactivar clases:

```css
.clsw{padding:0 12px 12px;display:flex;flex-wrap:wrap;gap:6px}
.cls{border:1px solid var(--bd);background:var(--s2);color:var(--tx3);border-radius:999px;
     padding:3px 10px;font-size:11.5px;font-family:var(--fm)}
.cls:hover{color:var(--tx2)}
.cls[aria-pressed="true"]{border-color:var(--ac-bd);background:var(--ac-bg);color:var(--ac-tx)}
```

**Tarjeta seleccionable (`.src`)** — elegir la fuente en Nueva corrida:

```css
.srcgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(164px,1fr));gap:8px;padding:12px}
.src{border:1px solid var(--bd);background:var(--s2);border-radius:8px;padding:9px 11px;text-align:left;
     color:var(--tx2);display:flex;flex-direction:column;gap:3px}
.src:hover:not([disabled]){border-color:var(--bds);color:var(--tx)}
.src[aria-pressed="true"]{border-color:var(--ac-bd);background:var(--ac-bg);color:var(--tx)}
.src[disabled]{opacity:.45;cursor:not-allowed}
.src b{font-weight:500;font-size:12.5px}
.src span{font-size:10.5px;color:var(--tx3);line-height:1.4}
```

**Número de paso (`.num`)**, dentro del `<h3>` de la tarjeta:

```css
.num{width:18px;height:18px;border-radius:50%;background:var(--s3);color:var(--tx3);font-size:10.5px;
     display:inline-flex;align-items:center;justify-content:center;flex:none;font-family:var(--fm)}
.num.on{background:var(--ac);color:#150f3d}
```

**Detalle plegable (`.adv`)** — "Opciones avanzadas", con chevron propio:

```css
.adv{border-top:1px solid var(--bd)}
.adv summary{padding:9px 12px;font-size:12px;color:var(--tx2);cursor:pointer;list-style:none;
             display:flex;align-items:center;gap:6px}
.adv summary::-webkit-details-marker{display:none}
.adv summary::before{content:"›";color:var(--tx3);font-size:14px;line-height:1}
.adv[open] summary::before{content:"⌄";line-height:.8}
```
Su estado se guarda (`S.adv`) porque el prototipo re-renderiza todo; en React basta
con estado local del componente.

**Chip editable con borrado (`.frchip`) y campo de alta (`.frnew`)** — editor de frases:

```css
.frwrap{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.frchip{display:inline-flex;align-items:center;gap:4px;border:1px solid var(--bd);background:var(--s1);
        border-radius:999px;padding:2px 4px 2px 10px;font-size:11.5px;color:var(--tx2)}
.frchip button{background:none;border:none;color:var(--tx4);padding:1px 3px;line-height:1;display:flex;border-radius:50%}
.frchip button:hover{color:var(--er)}
.frnew{height:26px;background:var(--s1);border:1px dashed var(--bds);border-radius:999px;color:var(--tx);
       padding:0 11px;font-size:11.5px;font-family:inherit;min-width:150px;flex:1}
```
`.frnew` confirma con `Enter` (handler global sobre `.frnew`), no con botón.

---

## 8. Tiles KPI (`.kpi`)

**Para qué sirve.** Fila de métricas de una corrida/experimento. Cada tile se compone
por partes opcionales — hay una sola función `kpi(o)` y todo lo demás es presencia o
ausencia de campos.

**Estructura completa** (todas las partes presentes):

```html
<div class="kpihd">Variación comparada con los últimos 30 s</div>
<div class="kpis">
  <div class="kpi">
    <div class="l"><i style="background:#4b95e8"></i>Cuadros por segundo</div>
    <div class="vr">
      <span class="v">2,4</span>
      <span class="dl" style="color:var(--ok)"><svg …triángulo…/>0,3</span>
    </div>
    <div class="foot">
      <svg width="100%" height="24" viewBox="0 0 112 24" preserveAspectRatio="none" role="img" aria-label="Tendencia">…</svg>
      <div class="sub">…</div>
    </div>
  </div>
</div>
```

Con unidad y con barra en vez de sparkline (el tile de memoria de GPU):

```html
<div class="kpi">
  <div class="l">Memoria de GPU</div>
  <div class="vr"><span class="v">6 142<small>MB</small></span></div>
  <div class="foot">
    <div class="mtr"><i style="width:75%;background:var(--live)"></i></div>
    <div class="sub">75 % de 8 192 MB</div>
  </div>
</div>
```

**CSS.**

```css
.kpihd{display:flex;align-items:baseline;gap:7px;padding:16px 20px 0;font-size:11px;color:var(--tx4)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(146px,1fr));gap:9px;padding:7px 20px 0}
.kpi{background:var(--s1);border:1px solid var(--bd);border-radius:var(--rc);padding:11px 13px 12px;
     display:flex;flex-direction:column}
.kpi .l{font-size:10.5px;color:var(--tx3);display:flex;align-items:center;gap:5px;line-height:1.3}
.kpi .l i{width:6px;height:6px;border-radius:2px;flex:none;display:block}   /* punto de color, cuadrado redondeado */
.kpi .vr{display:flex;align-items:baseline;gap:7px;flex-wrap:wrap;margin-top:2px}
.kpi .v{font-size:24px;font-weight:500;letter-spacing:-.025em;font-family:var(--fm);line-height:1.1}
.kpi .v small{font-size:11px;color:var(--tx3);font-weight:400;margin-left:3px;letter-spacing:0}
.kpi .dl{font-size:10.5px;font-family:var(--fm);display:inline-flex;align-items:center;gap:3px;line-height:1}
.kpi .foot{margin-top:auto;padding-top:11px}     /* empuja el pie al fondo: todos los tiles alinean */
.kpi .sub{font-size:10.5px;color:var(--tx4);line-height:1.5;padding-top:8px}
.kpi svg{display:block}
```

**Contrato de la función** (traducir a props de un `<Kpi/>`):

| campo | tipo | efecto |
|---|---|---|
| `l` | string | etiqueta |
| `dot` | color | punto de color a la izquierda de la etiqueta; **se omite si la métrica no pertenece a una serie de la línea de tiempo** |
| `v` | string ya formateado | valor grande (coma decimal, espacio fino de miles) |
| `u` | string | unidad, en `<small>` dentro del valor |
| `col` | color | tiñe el valor (`var(--wn)` descartes, `var(--sr)` alertas, `var(--ok)` exhaustividad) |
| `delta` | string | indicador de variación |
| `dup` | bool | dirección del triángulo (`true` = ▲) |
| `dtone` | color | color del indicador — **independiente de la dirección** |
| `spk` | HTML SVG | sparkline (ver abajo) |
| `meter` | 0–100 | barra de progreso |
| `mcol` | color | color de la barra |
| `segs` | `[{p,c}]` | barra segmentada (varios tramos) |
| `sub` | string | pie explicativo |

El pie (`.foot`) se renderiza si hay **cualquiera** de `spk`, `meter`, `segs`, `sub`;
sparkline y barra pueden coexistir.

**Indicador de variación (`.dl`).** Triángulo SVG 7×7 + texto con la magnitud **y su
unidad** ("0,3", "56 ms", "1,8 pp", "12"). El texto **no lleva signo**: el signo es el
triángulo.

```js
function tri(up){
  return '<svg width="7" height="7" viewBox="0 0 8 8" fill="currentColor" aria-hidden="true">'+
   (up?'<path d="M4 1l3.2 5.4H.8z"/>':'<path d="M4 7L.8 1.6h6.4z"/>')+'</svg>';
}
```

**Dirección y color son ortogonales, a propósito**: latencia con ▼ (bajó) se pinta
`var(--ok)` porque bajar es bueno; descartes con ▲ se pintan `var(--wn)`;
detecciones con ▲ se pintan `var(--tx3)` (neutro: más detecciones no es mejor ni
peor). **No inferir el color del signo.** Quien implemente debe declarar, por métrica,
si la dirección es buena, mala o neutra.

**Encabezado de la fila (`.kpihd`)** dice contra qué se compara y cambia con el estado:
"Variación comparada con **los últimos 30 s**" (en curso) /
"…con **la corrida anterior**" (terminada) /
"Resultado frente a los criterios definidos en el manifiesto" (experimento).

**Sparkline.** SVG de 112×24 en el `viewBox`, ancho 100 % con
`preserveAspectRatio="none"`: se estira horizontalmente y la línea se mantiene de
grosor constante gracias a `vector-effect="non-scaling-stroke"`. Tres elementos:
área rellena, línea, y un cuadradito de 4×4 en el último punto. La curva se suaviza
con cuadráticas entre puntos medios.

```js
function spark(vals,color,fill){
  const w=112,h=24,mx=Math.max(...vals),mn=Math.min(...vals),rg=(mx-mn)||1;
  const pts=vals.map((v,i)=>[(i/(vals.length-1))*w, h-3-((v-mn)/rg)*(h-7)]);
  let d="M "+pts[0][0].toFixed(1)+" "+pts[0][1].toFixed(1);
  for(let i=0;i<pts.length-1;i++){const a=pts[i],b=pts[i+1];
    d+=" Q "+a[0].toFixed(1)+" "+a[1].toFixed(1)+" "+((a[0]+b[0])/2).toFixed(1)+" "+((a[1]+b[1])/2).toFixed(1);}
  const l=pts[pts.length-1];
  d+=" L "+l[0].toFixed(1)+" "+l[1].toFixed(1);
  return '<svg width="100%" height="'+h+'" viewBox="0 0 '+w+' '+h+'" preserveAspectRatio="none" role="img" aria-label="Tendencia">'+
   '<path d="'+d+' L '+w+' '+h+' L 0 '+h+' Z" fill="'+fill+'"/>'+
   '<path d="'+d+'" fill="none" stroke="'+color+'" stroke-width="1.3" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>'+
   '<rect x="'+(l[0]-2).toFixed(1)+'" y="'+(l[1]-2).toFixed(1)+'" width="4" height="4" rx="1.2" fill="'+color+'"/></svg>';
}
```

Relleno = el color de la línea al 14–15 % de opacidad
(`rgba(75,149,232,.15)`, `rgba(125,110,242,.15)`, `rgba(224,162,23,.14)`).
El prototipo alimenta el sparkline con **series acumuladas de 8 puntos** calculadas
sobre los cuadros de la corrida (`acum()`), no con una serie temporal del backend.

**Medidor (`.mtr`)** — componente independiente, se reusa en tablas y en el progreso
de condiciones:

```css
.mtr{height:4px;border-radius:2px;background:var(--sunken);overflow:hidden;flex:1;display:flex;gap:2px}
.mtr i{display:block;height:100%;border-radius:2px}
```
```html
<div class="mtr"><i style="width:75%;background:var(--live)"></i></div>
<!-- segmentado -->
<div class="mtr"><i style="width:60%;background:var(--ok)"></i><i style="width:25%;background:var(--wn)"></i></div>
```

**Batería de KPI del Detalle de corrida** (para reproducirla):

| en curso | terminada |
|---|---|
| Cuadros por segundo (punto `--live`, ▲0,3 ok, sparkline) | ídem |
| Latencia (mediana) ms (punto `--live`, ▼56 ms ok, sparkline) | ídem |
| **Memoria de GPU** MB (sin punto, barra 75 %, sub "75 % de 8 192 MB") | **Latencia (percentil 95)** ms (▲41 ms en `--wn`, sub "Máximo observado 1 204 ms") |
| Detecciones (punto violeta, ▲12 neutro, sparkline) | ídem |
| Descartes de entrega % (punto ámbar, valor en `--wn`, ▲1,8 pp, sparkline) | ídem |
| Alertas confirmadas (punto coral, valor en `--sr`, sub "Última hace 21,4 s") | ídem |
| — | **Duración** s (sub "60 unidades procesadas") |

⚠ **Datos.**
1. **El indicador de variación necesita una "corrida anterior comparable"** (misma
   cámara, mismo conjunto de prompts, mismo modelo). Ese concepto **no existe** en el
   backend (punto 4 del README). Sin él: o se omite `.dl` por completo, o se
   restringe a la variante "últimos 30 s", que sí se puede calcular en el cliente
   con la traza en vivo.
2. **El sparkline necesita una serie temporal.** En el prototipo se deriva de la traza
   completa de la corrida; con la API real solo hay página actual (mismo bloqueo que
   la línea de tiempo, punto 1 del README).
3. **Memoria de GPU** requiere que el motor de detección la exponga (total y usada)
   por corrida o por instancia.
4. **Latencia p95, duración total y detecciones por clase** el prototipo las declara
   como "se calculan cuando termina": si el backend no las da en vivo, mostrar
   `— en curso` es el patrón aceptado.

---

## 9. Tarjetas (`.card`) y secciones

**Para qué sirve.** Contenedor estándar de todo bloque de contenido. Fondo `--s1`
sobre lienzo `--bg` más oscuro: la tarjeta se lee como objeto.

```html
<div class="card">
  <h3>Detecciones<span class="r">3</span></h3>
  …contenido…
  <p class="cap">Los nombres de clase los define el conjunto de prompts.</p>
</div>
```

```css
.card{background:var(--s1);border:1px solid var(--bd);border-radius:var(--rc)}
.card > h3{margin:0;padding:9px 12px;font-size:12px;font-weight:500;color:var(--tx2);
           border-bottom:1px solid var(--bd);display:flex;align-items:center;gap:8px}
.card > h3 .r{margin-left:auto;font-weight:400;color:var(--tx3);font-size:11px}
.cap{padding:0 12px 10px;font-size:11px;color:var(--tx4);line-height:1.5}
```

`.r` es la zona derecha del encabezado: contador ("3"), aclaración
("Solo una puede estar activa", "Mejor valor por fila en verde", "Conjunto seguridad / nocturno")
o un chip de estado.
`.cap` es el pie explicativo — el prototipo lo usa sistemáticamente para decir de
dónde salen los datos y qué **no** significan.

**Sección interna (`.esec`)** — separador con fondo elevado dentro de una tarjeta:

```css
.esec{display:flex;align-items:center;gap:8px;padding:9px 12px;background:var(--s2);
      border-top:1px solid var(--bd);border-bottom:1px solid var(--bd);font-size:11.5px;color:var(--tx2)}
.esec b{font-weight:500}
.esec .r{margin-left:auto;font-size:11px;color:var(--tx4);font-family:var(--fm)}
```

**Lista de definiciones (`.kv`)** — pares clave/valor (Configuración, Rendimiento):

```css
.kv{display:grid;grid-template-columns:auto 1fr;gap:5px 14px;padding:11px 12px;font-size:12px;margin:0}
.kv dt{color:var(--tx3);white-space:nowrap}
.kv dd{margin:0;color:var(--tx);font-family:var(--fm);font-size:11.5px;overflow:hidden;text-overflow:ellipsis}
```
Los valores van siempre en monoespaciada, incluso cuando son palabras
("un solo equipo") — refuerzan que son valores de configuración.

---

## 10. Tablas

**Para qué sirve.** El componente central de la consola: densidad de 32 px por fila,
borde inferior, **no** una tarjeta por fila.

```html
<div class="pad"><div class="card"><div class="tw"><table>
  <thead><tr>
    <th class="s" data-sort="nm">Corrida<span class="ar">↑</span></th>
    <th class="s" data-sort="st">Estado</th>
    <th class="s n" data-sort="fps">Cuadros/s</th>
    <th></th>
  </tr></thead>
  <tbody>
    <tr class="rw" data-run="run_…">
      <td><span class="rowname"><b>Ronda nocturna — cámara 04</b><span>run_20260725_143012</span></span></td>
      <td><span class="chip c-live"><span class="pulse"></span>En curso</span></td>
      <td class="n">2,4</td>
      <td class="act"><button class="btn gh" data-del="run_…">Borrar</button></td>
    </tr>
  </tbody>
</table></div></div></div>
```

```css
.tw{overflow-x:auto}                         /* envoltorio de desbordamiento horizontal */
table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;font-weight:500;color:var(--tx3);font-size:11px;padding:7px 11px;
   background:var(--s2);border-bottom:1px solid var(--bd);white-space:nowrap}
td{padding:0 11px;height:var(--row);border-bottom:1px solid var(--bd);color:var(--tx2);white-space:nowrap}
tbody tr:last-child td{border-bottom:none}
td.n{text-align:right;font-family:var(--fm);color:var(--tx)}   /* celda numérica */
th.n{text-align:right}
tbody tr:hover{background:var(--s2)}
th.s{cursor:pointer;user-select:none}                          /* encabezado ordenable */
th.s:hover{color:var(--tx2)}
th .ar{margin-left:4px;color:var(--ac-tx)}                     /* ↑ / ↓ */
tr.rw{cursor:pointer}                                          /* fila navegable */
td.act{text-align:right}
.rowname{display:flex;flex-direction:column;gap:1px;min-width:0;padding:5px 0}
.rowname b{font-weight:400;color:var(--tx);font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rowname span{font-size:10.5px;color:var(--tx4);font-family:var(--fm)}
td.best{color:var(--ok);position:relative}                     /* mejor valor por fila (Comparar) */
td.best::after{content:"";position:absolute;left:0;right:0;bottom:0;height:1px;background:var(--ok-bd)}
```

**Reglas.**
- **Celda de nombre (`.rowname`)**: dos líneas. Título en `--tx` peso 400; debajo, en
  monoespaciada `--tx4`, el identificador. **Si la corrida no tiene nombre**, el
  identificador sube a título y la segunda línea pasa a ser la antigüedad
  ("hace 4 h"): `r.nm||r.id` arriba, `r.nm ? r.id : hace(r.min)` abajo.
- **Celdas numéricas** siempre `td.n` (derecha + monoespaciada + `--tx`), y su
  encabezado `th.n`. Valor ausente = `—` (guion largo), nunca `0` ni vacío. Unidad
  pegada al número ("24,8 s").
- **Ordenamiento**: estado `S.sort={k,d}`; clic sobre la misma clave invierte `d`.
  La flecha se pinta con el acento y solo aparece en la columna activa.
- **Última columna sin encabezado** (`<th></th>`) para acciones (`td.act`), con botones
  fantasma ocultos hasta el hover (§6).
- **Fila vacía**: `<tr><td colspan="9"><div class="empty">…</div></td></tr>`.

**Contador "N de M" (`.cnt`).** Vive en `.toolbar`, no en la tabla:
`rows.length + " de " + RUNS.length` — filtradas de total. Monoespaciada, `--tx4`.
La lista de cuadros usa el mismo patrón adentro de su cabecera (`"60 de 60"`).

⚠ **Dato.** Filtrado, ordenamiento y paginación son **del lado del cliente** en el
prototipo. `listRuns()` trae todo. Funciona, pero no escala (punto 5 del README). El
componente de tabla debería aceptar tanto orden local como orden delegado al servidor.

---

## 11. Chips y badges de estado (`.chip`)

**Para qué sirve.** Todo estado. **Regla no negociable del diseño: el color nunca va
solo — siempre icono + texto.**

```css
.chip{display:inline-flex;align-items:center;gap:4px;padding:1px 7px;border-radius:999px;
      font-size:11px;border:1px solid;white-space:nowrap;line-height:1.6}
.c-live{background:var(--live-bg);border-color:var(--live-bd);color:var(--live)}
.c-ok  {background:var(--ok-bg);  border-color:var(--ok-bd);  color:var(--ok)}
.c-wn  {background:var(--wn-bg);  border-color:var(--wn-bd);  color:var(--wn)}
.c-sr  {background:var(--sr-bg);  border-color:var(--sr-bd);  color:var(--sr)}
.c-er  {background:var(--er-bg);  border-color:var(--er-bd);  color:var(--er)}
.c-nt  {background:var(--s2);     border-color:var(--bd);     color:var(--tx3)}
```

Los seis estados, con su marca visual:

| clase | color | marca | significados en el prototipo |
|---|---|---|---|
| `c-live` | `#4b95e8` | `<span class="pulse">` (punto que late) | En curso · 1 corrida en curso |
| `c-ok` | `#35b45a` | `ic.chk` ✓ | Completada · Operativa · Operativo · Completado · Cumple · Recibido |
| `c-wn` | `#e0a217` | `ic.warn` ⚠ | Degradado · Límite de tasa · Sobrecarga |
| `c-sr` | `#ee8a5c` | `ic.warn` ⚠ | Alerta · Alerta confirmada · "2 criterios sin cumplir" |
| `c-er` | `#f0625f` | `ic.x` ✕ | Fallida · Sin respuesta · No cumple · No recibido |
| `c-nt` | `--nt`/`--tx3` | sin icono | Sin dato · Detenida · Sin ejecutar · "Un solo equipo" · "hace 4 min" · "Ver cuadro" |

`c-nt` cumple doble función: **estado sin dato** y **chip de contexto neutro** (metadatos
del encabezado, etiqueta de acción secundaria en una fila). No lleva icono.

**Punto que late (`.pulse`)** — el único elemento animado del sistema:

```css
.pulse{width:6px;height:6px;border-radius:50%;background:var(--live);animation:p 2s ease-in-out infinite}
@keyframes p{0%,100%{opacity:1}50%{opacity:.35}}
```
Se usa suelto (dentro del chip "En curso", como icono de la banda en vivo) y con
`background:var(--er)` + `animation:p 1.3s` en `.recdot` (grabación en curso).
Respeta `prefers-reduced-motion` por la regla global.

**Constructores de chip a portar** (son la capa de etiquetas del glosario):

```js
const runChip = st =>
  st==="run" ? '<span class="chip c-live"><span class="pulse"></span>En curso</span>' :
  st==="ok"  ? '<span class="chip c-ok">'+ic.chk+'Completada</span>' :
               '<span class="chip c-er">'+ic.x+'Fallida</span>';

// estado de entrega al motor de reglas (vocabulario del control-plane)
const ctlShort = c => c==="received"?"Recibido" : c==="dropped:rate_gate"?"Límite de tasa"
  : c==="dropped:overload"?"Sobrecarga" : c==="not_received"?"No recibido" : c;
const ctlLong  = c => c==="received"?"Entregado al motor de reglas"
  : c==="dropped:rate_gate"?"Descartado por límite de tasa"
  : c==="dropped:overload"?"Descartado por sobrecarga"
  : c==="not_received"?"No llegó al motor de reglas" : c;
const ctlCls = c => c==="received"?"c-ok" : c.startsWith("dropped:")?"c-wn"
  : c==="not_received"?"c-er" : "c-nt";
const ctlDot = c => c==="received"?"var(--ok)" : c.startsWith("dropped:")?"var(--wn)"
  : c==="not_received"?"var(--er)" : "var(--nt)";
```

Patrón: **etiqueta corta en el chip, etiqueta larga en el `title`**
(`<span class="chip c-wn" title="Descartado por límite de tasa">Límite de tasa</span>`).

⚠ **Dato.** El vocabulario de `control` **debe ser cerrado**. Hoy `traceview.ts`
devuelve la cadena cruda cuando no la reconoce, así que un motivo nuevo del backend
(`dropped:lo_que_sea`) se filtra a la pantalla en inglés (punto 2 del README). El
fallback correcto para la implementación es el chip `c-nt` con el texto "sin dato" y
el valor crudo en el `title`, nunca la cadena cruda como etiqueta.

⚠ **Dato.** Los nombres legibles de las condiciones (`CR-01 — Presencia de persona`)
están hardcodeados en el prototipo (`const COND={"CR-01":"Presencia de persona",
"CR-02":"Permanencia en zona"}`) y **tienen que viajar desde el backend** (punto 3).
Mientras no lleguen, se muestra solo el código en `.mono`.

**Flujo de ciclo de vida (`.fstep`)** — variante de chip encadenado (Conjuntos de prompts):

```html
<div class="flow">
  <span class="fstep done">En exploración</span><span class="farrow">→</span>
  <span class="fstep on">Pendiente de revisión</span><span class="farrow">→</span>
  <span class="fstep">Congelado</span>
</div>
```
```css
.flow{display:flex;align-items:center;gap:7px;padding:11px 12px;flex-wrap:wrap}
.fstep{display:flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;
       border:1px solid var(--bd);background:var(--s2);font-size:11.5px;color:var(--tx4)}
.fstep.on{border-color:var(--ac-bd);background:var(--ac-bg);color:var(--ac-tx)}
.fstep.done{border-color:var(--ok-bd);color:var(--ok)}
.farrow{color:var(--tx4);font-size:12px}
```

---

## 12. Gráfico de línea de tiempo (`.tl`)

**Para qué sirve.** Vista de la corrida completa en una tira: dónde hubo detecciones,
dónde se perdió la entrega al motor de reglas, dónde se confirmaron alertas, y qué
cuadro se está mirando. Es **navegación** además de gráfico: clic = selección de cuadro.
Es el componente más complejo del prototipo y el que más trabajo va a costar.

### 12.1 Estructura

```html
<div class="tl">
  <div class="hd">
    <b>Línea de tiempo</b><span>60 cuadros · 24,8 s</span>
    <span class="lg">
      <span><i style="background:rgba(75,149,232,.55)"></i>Detecciones</span>
      <span><i style="background:rgba(224,162,23,.8)"></i>Descartado</span>
      <span><i style="background:rgba(240,98,95,.85)"></i>No recibido</span>
      <span><i style="background:var(--sr)"></i>Alerta</span>
    </span>
  </div>

  <div class="lanes" id="lanes">
    <!-- carril 1: área de densidad de detecciones -->
    <div class="lane lane-det">
      <span class="ln">Detecciones<br>por cuadro</span>
      <svg viewBox="0 0 59 10" preserveAspectRatio="none" role="img"
           aria-label="Densidad de detecciones a lo largo de la corrida">
        <path d="…area…" fill="rgba(75,149,232,.16)"/>
        <path d="…línea…" fill="none" stroke="rgba(75,149,232,.75)" stroke-width="1.1"
              stroke-linejoin="round" vector-effect="non-scaling-stroke"/>
      </svg>
    </div>

    <!-- carril 2: tira de estado de entrega, un <i> por cuadro -->
    <div class="lane">
      <span class="ln">Entrega al<br>motor de reglas</span>
      <div class="strip" role="img" aria-label="Estado de entrega por cuadro">
        <i style="background:rgba(255,255,255,.055)"></i>…
      </div>
    </div>

    <!-- carril 3: marcadores de alerta -->
    <div class="lane lane-al">
      <span class="ln">Alertas</span>
      <span class="almk" style="left:31.03%"></span>…
    </div>

    <!-- cabezal de reproducción, atraviesa los tres carriles -->
    <div class="head" style="left:calc(32.20% + 82px)"></div>
  </div>

  <div class="axis"><span>0,0 s</span><span>12,4 s</span><span>24,8 s</span></div>
  <div class="ttip" id="ttip"></div>
</div>
```

### 12.2 CSS

```css
.tl{margin:14px 20px 0;background:var(--s1);border:1px solid var(--bd);border-radius:var(--rc);
    padding:10px 13px 9px;position:relative}
.tl .hd{display:flex;align-items:center;gap:9px;font-size:11px;color:var(--tx3);margin-bottom:9px;flex-wrap:wrap}
.tl .hd b{color:var(--tx2);font-weight:500;font-size:12px}
.tl .lg{margin-left:auto;display:flex;gap:11px;align-items:center}
.tl .lg span{display:inline-flex;align-items:center;gap:5px}
.tl .lg i{width:7px;height:7px;border-radius:2px;display:block;flex:none}

.lanes{position:relative;cursor:crosshair;padding-left:82px}   /* 82px = canaleta de etiquetas */
.lane{position:relative;margin-bottom:5px}
.lane .ln{position:absolute;left:-82px;top:50%;transform:translateY(-50%);width:76px;
          text-align:right;font-size:10px;color:var(--tx4);line-height:1.25}
.lane-det{height:42px;background:var(--sunken);border-radius:4px;overflow:hidden}
.lane-det svg{display:block;width:100%;height:100%}
.strip{display:flex;height:7px;border-radius:3px;overflow:hidden;background:var(--sunken)}
.strip i{flex:1;display:block}
.lane-al{height:12px}
.almk{position:absolute;top:1px;transform:translateX(-50%);width:0;height:0;
      border-left:4px solid transparent;border-right:4px solid transparent;border-bottom:7px solid var(--sr)}
.head{position:absolute;top:0;bottom:0;width:1px;background:var(--ac);pointer-events:none;z-index:3}
.head::before{content:"";position:absolute;top:-3px;left:-3px;width:7px;height:7px;
              background:var(--ac);border-radius:2px}
.axis{display:flex;justify-content:space-between;font-size:10px;color:var(--tx4);
      font-family:var(--fm);margin:3px 0 0 82px}
.ttip{position:absolute;z-index:20;background:var(--s3);border:1px solid var(--bds);border-radius:6px;
      padding:5px 9px;font-size:11px;pointer-events:none;white-space:nowrap;
      box-shadow:0 5px 18px rgba(0,0,0,.55);display:none;line-height:1.6}
.ttip b{font-weight:500;font-family:var(--fm)}
.ttip .d{color:var(--tx3)}
```

En ≤760 px la canaleta desaparece: `.lanes{padding-left:0}`, `.lane .ln{display:none}`,
`.axis{margin-left:0}` — y el `+82px` del cabezal debe volverse `+0`.

### 12.3 Cómo se dibuja

**Sistema de coordenadas.** `viewBox="0 0 W H"` con `W = F-1` (índice del último cuadro,
59 con 60 cuadros) y `H = 10`, con `preserveAspectRatio="none"`: **una unidad del
viewBox = un cuadro**, y el SVG se estira al ancho disponible. Es lo que permite
posicionar todo con el índice de cuadro directamente. El trazo no se deforma gracias a
`vector-effect="non-scaling-stroke"`.

**Carril 1 — área de densidad.** Igual criterio que el sparkline: normaliza contra el
máximo de detecciones por cuadro y suaviza con cuadráticas a puntos medios.

```js
const mx = Math.max(...FR.map(f=>f.dets.length)) || 1, W=F-1, H=10;
const pts = FR.map((f,i)=>[i, H-0.5-(f.dets.length/mx)*(H-1.2)]);
let d = "M "+pts[0][0]+" "+pts[0][1].toFixed(2);
for(let i=0;i<pts.length-1;i++){
  const a=pts[i], b=pts[i+1];
  d += " Q "+a[0].toFixed(2)+" "+a[1].toFixed(2)+" "+((a[0]+b[0])/2).toFixed(2)+" "+((a[1]+b[1])/2).toFixed(2);
}
d += " L "+W+" "+pts[pts.length-1][1].toFixed(2);
const area = d+" L "+W+" "+H+" L 0 "+H+" Z";
```

**Carril 2 — tira de entrega.** **No es SVG**: es un flexbox con un `<i class="flex:1">`
por cuadro. Con 60 cuadros son 60 nodos; con una corrida real de miles esto hay que
sustituirlo (canvas, o agregación por cubetas — ver ⚠ abajo).

```js
const bg = f.ctl==="received"      ? "rgba(255,255,255,.055)"   /* casi invisible: lo normal no grita */
         : f.ctl.startsWith("dropped:") ? "rgba(224,162,23,.8)"
         : "rgba(240,98,95,.85)";
```

**Carril 3 — marcadores de alerta.** Triángulos hechos con bordes CSS, posicionados en
porcentaje sobre el índice del cuadro:

```js
ALERTS.map(i=>'<span class="almk" style="left:'+((i/W)*100).toFixed(2)+'%"></span>').join("")
```

**Cabezal.** Línea vertical de 1 px del color de acento, con un cuadradito de 7×7 arriba
(`::before`). Se posiciona con `calc(<porcentaje> + 82px)` para compensar la canaleta:

```js
const hp = ((S.sel/W)*100).toFixed(2);
'<div class="head" style="left:calc('+hp+'% + 82px)"></div>'
```

**Eje temporal.** Tres marcas fijas (`0,0 s`, mitad, total) en `space-between`, con el
mismo desplazamiento de 82 px. No hay escalado de ticks.

**Leyenda.** Cuatro entradas fijas con cuadraditos de 7×7 (`border-radius:2px`) que usan
**los mismos colores exactos** que el dibujo, no los tokens planos (el azul de detecciones
en la leyenda es `.55` de opacidad; en el área `.16`/`.75`).

### 12.4 Comportamiento (`bindLanes`)

Un solo `mousemove`/`click` sobre `#lanes`, con conversión de píxel a índice de cuadro:

```js
const idx = e => {
  const r = L.getBoundingClientRect(), x = e.clientX - r.left - 82, w = r.width - 82;
  return Math.max(0, Math.min(F-1, Math.round((x/w)*(F-1))));
};
L.addEventListener("mousemove", e=>{
  const f = FR[idx(e)], r = L.getBoundingClientRect();
  T.innerHTML = '<b>Cuadro '+f.i+'</b> <span class="d">· '+f.t+' s</span><br>'+
    f.dets.length+' detecc'+(f.dets.length===1?"ión":"iones")+' <span class="d">· '+ctlLong(f.ctl)+'</span>'+
    (f.alert.length?'<br><span style="color:var(--sr)">Alerta '+f.alert[0].id+' · '+COND[f.alert[0].id]+'</span>':'');
  T.style.display="block";
  const w = T.offsetWidth, x = e.clientX - r.left;
  T.style.left = Math.max(4, Math.min(r.width - w - 4, x - w/2))+"px";   // no se sale de la caja
  T.style.top  = (e.clientY - r.top - T.offsetHeight - 12)+"px";
});
L.addEventListener("mouseleave", ()=>{ T.style.display="none"; });
L.addEventListener("click", e=>{ S.sel = idx(e); S.err=null; render(); });
```

Detalles a conservar:
- El tooltip se **fija por dentro** de la caja (`Math.max(4, Math.min(r.width-w-4, …))`).
- Se posiciona por encima del cursor (`-altura -12`).
- El cursor es `crosshair` sobre todo el bloque de carriles.
- El binding se rehace en cada render porque el prototipo reescribe el DOM; en React
  son handlers normales del componente.
- La selección está sincronizada con la lista de cuadros y con las flechas ←/→ del
  teclado (`nav(±1)`, ignoradas si el foco está en un `INPUT`), y con el
  `scrollIntoView({block:"nearest"})` de la fila seleccionada.

**Accesibilidad.** Cada carril tiene `role="img"` + `aria-label` descriptivo, pero
**no hay alternativa de teclado para el gráfico** (el clic es lo único). Las flechas
sobre la lista de cuadros cumplen esa función; conviene hacer el bloque enfocable y
mapear las flechas también ahí.

⚠ **Dato — este es el bloqueo más duro.** El componente necesita **un índice de
actividad de la corrida completa**, independiente de la paginación: por cuadro,
cantidad de detecciones, estado de entrega y si hubo alerta. Hoy
`GET /api/runs/{id}/trace` solo conoce la página actual (punto 1 del README).
Sin ese endpoint, la línea de tiempo **no puede existir tal como está diseñada**.
Alternativas si no se toca el backend: (a) dibujarla solo sobre la página cargada,
rotulando el eje con el rango real de esa página; (b) traer la traza completa en
corridas cortas y degradar a (a) por encima de N cuadros. Cualquiera de las dos
cambia el significado del eje y **hay que decirlo en la interfaz**.

⚠ **Escala.** 60 cuadros son 60 nodos DOM en la tira y ~60 comandos de path. Una
corrida de miles de cuadros exige agregar por cubeta (una cubeta por píxel disponible,
tomando el peor estado de entrega de la cubeta) antes de dibujar.

---

## 13. Bandas y avisos

Tres componentes distintos, con jerarquías distintas.

### 13.1 Banda (`.banner`)

**Para qué sirve.** Aviso de bloque, ancho completo, dentro de un `.pad`. Siempre:
icono + texto en negrita con la causa + explicación en `--tx2`, y opcionalmente un
botón de cerrar o una acción.

```css
.banner{display:flex;align-items:flex-start;gap:9px;border-radius:8px;padding:8px 11px;font-size:12px;border:1px solid}
.banner.wn{background:var(--wn-bg);border-color:var(--wn-bd)}
.banner.er{background:var(--er-bg);border-color:var(--er-bd)}
.banner .ic{flex:none;margin-top:1px}
.banner b{font-weight:500}
```

Ejemplos reales:

```html
<!-- advertencia con cierre -->
<div class="banner wn">
  <span class="ic" style="color:var(--wn)">⚠</span>
  <div><b>El motor de reglas no responde.</b>
    <span style="color:var(--tx2)">Los descartes de entrega y las alertas se muestran como
    <code>sin dato</code>. La detección sobre el video sigue funcionando.</span></div>
  <button class="btn gh" aria-label="Cerrar aviso">✕</button>
</div>

<!-- error de operación -->
<div class="banner er"><span class="ic" style="color:var(--er)">⚠</span>
  <div style="flex:1">Hay una corrida en curso (run_20260725_143012). Esperá a que
  termine o detenela antes de cambiar de instancia.</div>
  <button class="btn gh" aria-label="Cerrar aviso">✕</button></div>

<!-- alerta confirmada (banda ámbar con contenido coral) -->
<div class="banner wn"><span class="ic" style="color:var(--sr)">⚠</span>
  <div><b style="color:var(--sr)">Alerta confirmada — <span class="mono">CR-01</span> · Presencia de persona</b><br>
  <span style="color:var(--tx2)">Se disparó en el cuadro 19 (8.0 s), cuando la condición llegó al 100 %.</span></div></div>
```

### 13.2 Aviso de corrida en vivo (variante `live`, sin clase propia)

La banda azul del listado de Corridas — la única que lleva **acción** y `.pulse` como
icono. No tiene modificador CSS: se pinta con estilos inline.

```html
<div class="pad" style="padding-bottom:0">
  <div class="banner" style="background:var(--live-bg);border-color:var(--live-bd)">
    <span class="ic"><span class="pulse" style="display:block;margin-top:5px"></span></span>
    <div style="flex:1">
      <b style="color:var(--live)">Ronda nocturna — cámara 04</b>
      <span style="color:var(--tx2)">está procesando ahora — 67 detecciones, 3 alertas confirmadas.</span>
    </div>
    <button class="btn" data-run="run_20260725_143012">Ver en vivo</button>
  </div>
</div>
```

Se renderiza **solo si hay al menos una corrida en curso**. Recomendación para la
implementación: agregar un modificador `.banner.live` en vez de estilos inline.

⚠ **Dato.** El resumen de la banda ("67 detecciones, 3 alertas confirmadas") requiere
contadores agregados de la corrida activa en vivo; si no están, el texto se recorta a
"está procesando ahora."

### 13.3 Nota al pie (`.note`)

**Para qué sirve.** Aclaración de menor jerarquía, sin caja: icono `info` o `warn` +
párrafo. Va suelta, al final de una sección.

```css
.note{font-size:11.5px;color:var(--tx3);display:flex;align-items:flex-start;gap:7px;margin:0;line-height:1.55}
.note svg{flex:none;margin-top:1px}
```
```html
<p class="note">ⓘ<span>Activar otra instancia apaga la actual y espera a que el modelo
cargue, lo que puede tardar varios minutos. No se puede cambiar de instancia mientras
haya una corrida en curso.</span></p>
```

### 13.4 Banda de grabación (`.rec`)

Franja de estado de una operación en curso o recién terminada. Sin colores propios:
se le pasan `background`/`border-color` del par `-bg`/`-bd` que corresponda
(`wn` preparando, `er` grabando, `ok` terminada).

```css
.rec{display:flex;align-items:center;gap:9px;padding:9px 12px;border-radius:8px;font-size:12px;border:1px solid}
.recdot{width:8px;height:8px;border-radius:50%;background:var(--er);flex:none;animation:p 1.3s ease-in-out infinite}
```

---

## 14. Listas y filas seleccionables

Tres variantes del mismo patrón "fila de lista maestra", todas `<button>` con
`border-left:2px solid transparent` que se pinta al seleccionar.

### 14.1 Fila de lista maestra (`.lrow`)

```html
<button class="lrow" data-pset="ps_perimetro_v3" aria-current="true">
  <span class="w"><b>ps_perimetro_v3</b><span>Perímetro · 4 clases · 11 frases</span></span>
  <span class="chip c-nt">En exploración</span>
</button>
```

```css
.lrow{display:flex;align-items:center;gap:9px;padding:8px 11px;border-bottom:1px solid var(--bd);width:100%;
      background:none;border-left:2px solid transparent;border-top:none;border-right:none;
      color:inherit;text-align:left;font-size:12px}
.lrow:last-child{border-bottom:none}
.lrow:hover{background:var(--s2)}
.lrow[aria-current="true"]{background:var(--ac-bg);border-left-color:var(--ac)}
.lrow .w{flex:1;min-width:0}
.lrow .w b{font-weight:400;color:var(--tx);display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.lrow .w span{font-size:10.5px;color:var(--tx4);font-family:var(--fm);display:block;
              overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.lrow .ac{display:flex;gap:4px;flex:none}
.lrow .ac .btn{opacity:0}
.lrow:hover .ac .btn,.lrow .ac .btn:focus-visible,.lrow .ac .btn.stay{opacity:1}
```

### 14.2 Fila de cuadro (`.fr`) — lista de la traza

Grilla de tres columnas de altura `--row`, con indicadores compactos a la derecha.

```html
<button class="fr" data-fr="19" data-sel="1" title="Entregado al motor de reglas">
  <span class="ix">19</span>
  <span class="id">4a91c019</span>
  <span class="rt">
    <span class="chip c-sr">Alerta</span>
    <span class="dc">3</span>
    <span class="st" style="background:var(--ok)"></span>
  </span>
</button>
```

```css
.flist{background:var(--s1);border:1px solid var(--bd);border-radius:var(--rc);overflow:hidden}
.flist .ft{display:flex;align-items:center;gap:10px;padding:8px 10px;border-bottom:1px solid var(--bd);
           flex-wrap:wrap;background:var(--s2)}                  /* cabecera con los .tog y el "60 de 60" */
.rows{max-height:492px;overflow-y:auto}
.fr{display:grid;grid-template-columns:46px 1fr auto;align-items:center;gap:8px;height:var(--row);
    padding:0 10px;border-bottom:1px solid var(--bd);cursor:pointer;background:none;
    border-left:2px solid transparent;width:100%;text-align:left;border-right:none;border-top:none;color:inherit}
.fr:hover{background:var(--s2)}
.fr[data-sel="1"]{background:var(--ac-bg);border-left-color:var(--ac)}
.fr .ix{font-family:var(--fm);font-size:11px;color:var(--tx3)}
.fr[data-sel="1"] .ix{color:var(--ac-tx)}
.fr .id{font-family:var(--fm);font-size:11px;color:var(--tx2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fr .rt{display:flex;align-items:center;gap:6px}
.fr .dc{font-family:var(--fm);font-size:10.5px;color:var(--tx3);min-width:12px;text-align:right}
.fr .st{width:6px;height:6px;border-radius:50%;flex:none}        /* punto de estado de entrega */
```

Sin detecciones se muestra `—`, nunca `0`. El punto `.st` usa `ctlDot()` y el `title`
de la fila lleva `ctlLong()` — el color solo, con explicación al hover.
`max-height:492px` = ~15 filas antes de scrollear.

### 14.3 Fila de alerta (`.al`)

Lista con banda coral permanente a la izquierda.

```css
.alist{display:flex;flex-direction:column}
.al{display:flex;align-items:center;gap:9px;padding:8px 12px;border-bottom:1px solid var(--bd);
    background:none;border-left:2px solid var(--sr);width:100%;text-align:left;
    border-top:none;border-right:none;color:inherit;font-size:12px}
.al:last-child{border-bottom:none}
.al:hover{background:var(--s2)}
.al .w{flex:1;min-width:0}
.al .w b{font-weight:500;display:block}
.al .w span{color:var(--tx3);font-size:11px;font-family:var(--fm)}
```

### 14.4 Listas de datos menores

```css
/* detecciones: muestra de color + etiqueta mono + confianza */
.dets{padding:11px 12px;display:flex;flex-direction:column;gap:7px}
.det{display:flex;align-items:center;gap:8px;font-size:11.5px}
.det .sw{width:8px;height:8px;border-radius:2px;flex:none}
.det .lb{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-family:var(--fm)}
.det .cf{font-family:var(--fm);color:var(--tx2)}

/* progreso de condiciones: código + nombre + % + medidor */
.plist{padding:11px 12px;display:flex;flex-direction:column;gap:12px}
.prow{display:flex;flex-direction:column;gap:5px;font-size:11.5px}
.prow .ph{display:flex;align-items:baseline;gap:7px}
.prow .pcd{font-family:var(--fm);color:var(--tx);flex:none}
.prow .pnm{color:var(--tx2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.prow .ppc{font-family:var(--fm);color:var(--tx2);margin-left:auto;flex:none}

/* frases de una clase */
.phr{display:flex;flex-direction:column;gap:3px;padding:8px 12px;border-bottom:1px solid var(--bd)}
.phr b{font-weight:400;font-size:12px;color:var(--tx);font-family:var(--fm)}
.phr span{font-size:11px;color:var(--tx3);line-height:1.5}
```

Color de la barra de progreso de condición:
`alerta disparada → var(--sr)`, `p>=1 → var(--ok)`, resto `var(--wn)`.

---

## 15. Estados vacíos

Dos tamaños, y la diferencia importa.

### 15.1 Vacío inline (`.empty`)

Dentro de una tarjeta, una lista o una celda `colspan`. Dos líneas: qué pasó, y qué
hacer (la segunda en `--tx4`).

```css
.empty{padding:22px 12px;text-align:center;color:var(--tx3);font-size:12px;line-height:1.7}
```
```html
<div class="empty">Ninguna corrida coincide con el filtro.<br>
  <span style="color:var(--tx4)">Probá con otro texto o volvé a «Todas».</span></div>
```

El texto **cambia según la causa**: filtro sin resultados vs. lista realmente vacía.

```js
q||S.fst!=="all"
  ? 'Ninguna corrida coincide con el filtro.<br><span…>Probá con otro texto o volvé a «Todas».</span>'
  : 'Todavía no lanzaste ninguna corrida.<br><span…>Empezá por elegir una fuente y un conjunto de prompts.</span>'
```

Otros: "Ningún cuadro coincide con el filtro. / Destildá las casillas para ver la corrida
completa.", "Sin detecciones en este cuadro.", "Todavía no se acumuló progreso en este cuadro.",
"La evaluación se corre sobre una corrida terminada. / Cuando esta corrida finalice vas a
poder compararla contra el conjunto anotado."

### 15.2 Vacío grande (`.bigempty`)

Primera visita de una pantalla entera: icono grande opcional, título, párrafo
explicativo de por qué existe la pantalla, y acción primaria.

```css
.bigempty{display:flex;flex-direction:column;align-items:center;gap:10px;padding:40px 20px;text-align:center}
.bigempty h4{margin:0;font-size:15px;font-weight:500}
.bigempty p{margin:0;font-size:12.5px;color:var(--tx3);max-width:430px;line-height:1.65}
```
```html
<div class="card"><div class="bigempty">
  <svg width="30" height="30" viewBox="0 0 16 16" fill="none" stroke="var(--tx4)" stroke-width="1.2" aria-hidden="true">…</svg>
  <h4>Todavía no guardaste ninguna cámara</h4>
  <p>Una cámara guardada te deja verificar el encuadre antes de lanzar una corrida, y
     después elegirla desde Nueva corrida sin volver a escribir la dirección.</p>
  <button class="btn pri" data-camform="1">Agregar la primera cámara</button>
</div></div>
```

Sin acción cuando el vacío es "elegí algo del panel de al lado"
("Elegí un material o un clip", "Elegí al menos dos corridas").
El icono es el mismo de la barra lateral, a 30 px con `stroke:var(--tx4)`.

---

## 16. Carril de verificación previa (`.chk` + `.launch`)

**Para qué sirve.** Columna derecha de Nueva corrida: lista de precondiciones con
estado, y el botón de lanzar con el **motivo del bloqueo** debajo. Es el patrón que la
consola usa para no dejar nunca un botón deshabilitado sin explicación.

```html
<div class="rail"><div class="card"><h3>Antes de lanzar</h3>
  <div class="chk"><span class="m" style="color:var(--ok)">✓</span>
    <span class="w"><b>El motor de detección está listo</b><span>owlv2-cuda · modelo cargado</span></span></div>
  <div class="chk no"><span class="m" style="color:var(--tx4)"><circle…/></span>
    <span class="w"><b>Elegiste un origen</b><span>Ni conjunto del catálogo ni ruta</span></span></div>
  …
  <div class="launch">
    <button class="btn pri" data-launch="1" disabled>▶ Lanzar corrida</button>
    <span class="why">Falta: elegiste un origen</span>
  </div>
</div></div>
```

```css
.rail{position:sticky;top:14px;display:flex;flex-direction:column;gap:10px}
.chk{display:flex;gap:9px;padding:9px 12px;border-bottom:1px solid var(--bd);font-size:12px;align-items:flex-start}
.chk:last-of-type{border-bottom:none}
.chk .m{flex:none;margin-top:2px}
.chk .w b{font-weight:400;display:block;color:var(--tx)}
.chk.no .w b{color:var(--tx3)}                       /* pendiente: título atenuado */
.chk .w span{font-size:10.5px;color:var(--tx4);display:block;line-height:1.45;margin-top:1px}
.launch{padding:11px 12px;border-top:1px solid var(--bd);display:flex;flex-direction:column;gap:7px}
.launch .btn{width:100%;justify-content:center;height:32px}
.launch .why{font-size:10.5px;color:var(--tx4);line-height:1.45;text-align:center}
```

**Comportamiento.** Cada paso es `{ok, l, sub}`. Marca: `ic.chk` en `var(--ok)` si
cumple, círculo vacío en `var(--tx4)` si no. El **subtítulo siempre dice el estado
concreto**, incluso cuando cumple ("4 de 6 activas", "Congelado, no se puede editar").
El botón se deshabilita si hay algún paso pendiente, y `.why` muestra
`"Falta: " + primer paso pendiente en minúscula`, o
`"Todo listo. La corrida arranca en cuanto confirmes."`.
Al pulsar con todo listo, todavía puede fallar por conflicto de estado global (ya hay
otra corrida activa) — eso se comunica con un `.banner wn` debajo del formulario.

`.rail` es `position:sticky` y pasa a `static` en ≤1100 px.

---

## 17. Componentes de plataforma

Transversales solo en apariencia, pero conviene tenerlos fichados porque reaparecen
como patrón "recurso con estado".

**Tarjeta de instancia activa (`.tgt`)** — la única tarjeta con borde de acento:

```css
.tgt{background:var(--s1);border:1px solid var(--ac-bd);border-radius:var(--rc);padding:13px 15px}
.tgt .lbl{font-size:11px;color:var(--ac-tx);letter-spacing:.02em}   /* "Instancia activa" */
.tgt .nm{font-size:20px;font-weight:500;margin:3px 0 1px;letter-spacing:-.015em;font-family:var(--fm)}
```

**Fila de motor (`.plane`)**:

```css
.planes{display:flex;flex-direction:column;gap:8px}
.plane{background:var(--s1);border:1px solid var(--bd);border-radius:var(--rc);padding:10px 12px;
       display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.plane .w{flex:1;min-width:0}
.plane .w b{font-weight:500;font-size:12.5px;display:block}
.plane .w span{font-size:11px;color:var(--tx3);font-family:var(--fm)}   /* localhost:8080 */
```
Orden: chip de estado a la izquierda, nombre + dirección al medio, acción a la derecha.

---

## 18. Visor de cuadro (`.viewer` / `.stage`)

Transversal porque la vista previa de cámara lo reusa. Contenedor hundido con cabecera
y escena 16:9; las cajas se dibujan en SVG con coordenadas **en porcentaje**, así el
overlay escala con la imagen.

```css
.viewer{background:var(--sunken);border:1px solid var(--bd);border-radius:var(--rc);overflow:hidden}
.viewer .vh{display:flex;align-items:center;gap:8px;padding:7px 11px;border-bottom:1px solid var(--bd);
            background:var(--s1);font-size:11.5px;color:var(--tx2);flex-wrap:wrap}
.viewer .vh .r{margin-left:auto;display:flex;gap:6px;align-items:center}
.stage{position:relative;width:100%;aspect-ratio:16/9;max-height:326px}
.stage svg{position:absolute;inset:0;width:100%;height:100%}
```

Caja de detección (patrón a conservar: rectángulo + banda de etiqueta pegada arriba,
texto en el color hundido `#0d0d0c` sobre el color de la clase):

```html
<g>
  <rect x="12%" y="18%" width="16%" height="22%" fill="none" stroke="#3987e5" stroke-width="1.4"/>
  <rect x="12%" y="12.6%" width="18%" height="5.4%" fill="#3987e5"/>
  <text x="12.8%" y="16.6%" font-size="6.6" font-family="ui-monospace,monospace" fill="#0d0d0c">person 0.85</text>
</g>
```

Cabecera del visor: `Cuadro 19 · unidad 4a91c019 · 8.0 s` a la izquierda, y a la
derecha el chip de entrega + los botones `‹ ›` (`.btn.gh`, con `aria-label`).

⚠ **Dato.** Los colores por clase son fijos en el prototipo
(`person #3987e5`, `vehicle #d95926`, `backpack #199e70`). Con vocabulario abierto la
paleta tiene que asignarse determinísticamente (hash del nombre de clase) para que la
misma clase tenga el mismo color entre cuadros y entre corridas.

---

## 19. Estado global y ciclo de render (referencia, no a copiar)

El prototipo es un render completo del `<main>` en cada interacción, con estado en un
objeto plano. **En React nada de esto se copia**, pero la forma del estado documenta
qué es global y qué es local:

```js
let S = {
  screen:"runs",            // pantalla actual (router)
  tab:"traza",              // pestaña del detalle de corrida
  sel:19,                   // cuadro seleccionado (compartido: lista + línea de tiempo + visor)
  act:false, onlyAlert:false,  // filtros de la traza
  ctlDown:false,            // salud del motor de reglas → degradación global
  fin:false,                // (andamiaje del prototipo)
  collapsed:false,          // barra lateral colapsada   ← persistir en localStorage
  menu:null,                // índice de menú abierto en barra superior
  err:null,                 // aviso global de la pantalla
  q:"", fst:"all",          // búsqueda y filtro segmentado del listado
  sort:{k:"min",d:1},       // orden de tabla
  del:null,                 // id en confirmación de borrado
  adv:false,                // <details> de opciones avanzadas
  cmp:[…], dd:null          // selección de comparación; desplegable abierto
};
```

Reglas de higiene que sí conviene portar:
- Navegar entre pantallas limpia `S.err`, `S.del`, `S.q` y cierra editores abiertos.
- Abrir un desplegable cierra el menú de la barra superior y viceversa; `Escape` cierra ambos.
- Cambiar de filtro o de texto de búsqueda cancela la confirmación de borrado pendiente.
- Las flechas ←/→ navegan cuadros solo en la pestaña Traza y solo si el foco no está
  en un `INPUT`.

---

## 20. Resumen de dependencias de datos

Lo que un componente **no puede renderizar** sin cambios/agregados en la API. Ninguno
requiere tocar el backend para existir: todos tienen degradación indicada.

| Componente | Dato faltante | Degradación aceptable |
|---|---|---|
| KPI · indicador de variación `.dl` | "corrida anterior comparable" (misma cámara/conjunto/modelo) — no existe (README 4) | omitir `.dl`, o limitarlo a "últimos 30 s" calculado en el cliente |
| KPI · sparkline | serie temporal de la métrica | omitir el sparkline; el tile queda igualmente válido |
| KPI · Memoria de GPU | uso/total de VRAM del motor | reemplazar por Latencia p95 o Duración |
| **Línea de tiempo** | índice de actividad de la corrida completa (README 1) | dibujar solo la página cargada y rotular el eje con su rango real |
| Chip de entrega | vocabulario cerrado de `control` (README 2) | valor no reconocido → chip `c-nt` "sin dato" + crudo en `title` |
| Alerta / progreso de condiciones | nombre legible de la condición (README 3) | mostrar solo `CR-01` en `.mono` |
| `.rowname` segunda línea, "hace 4 min" | fecha de creación explícita (README 7) | ocultar la antigüedad; no parsear el `run_id` |
| Desplegable · opción deshabilitada | motivo de deshabilitado de los plugins (README 6) | "— no disponible" genérico |
| Tabla · `.cnt` "N de M" y orden | filtrado/orden/paginación en servidor (README 5) | seguir en cliente; aceptar el techo de escala |
| Banda de corrida en vivo | contadores agregados en vivo | recortar a "está procesando ahora." |
| Contadores de la barra lateral (`.ct`) | conteos por sección | omitir el `.ct` (nunca mostrar `0`) |
| Tabla de evaluación / KPI de criterios | esquema estable del reporte con umbral (README 9) | — |
| Visor · color por clase | paleta de clases | asignar color por hash del nombre de clase |
