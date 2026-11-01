import { useId, useRef, useState, type CSSProperties, type ReactElement, type ReactNode } from 'react'

/** Lo que `Ayuda` le pasa a un hijo interactivo para describirlo. */
export interface AyudaProps {
  'aria-describedby': string
}

/** Ancho máximo de la descripción (`44ch` ≈ 340 px) y alto que se reserva para decidir
 *  si cabe debajo. Con el margen, la descripción no toca el borde de la ventana. */
const ANCHO = 340
const ALTO = 170
const MARGEN = 8

/** Dónde poner la descripción, en coordenadas de la ventana. `position: fixed` y no
 *  `absolute`: una tabla o una tarjeta con scroll recorta lo que flota dentro de
 *  ella, y las tablas del catálogo son justo ahí donde más nombres hay. */
function ubicar(el: HTMLElement): CSSProperties {
  const r = el.getBoundingClientRect()
  const izquierda = Math.max(MARGEN, Math.min(r.left, window.innerWidth - ANCHO - MARGEN))
  const arriba = r.bottom + ALTO > window.innerHeight && r.top > ALTO
  return arriba
    ? { position: 'fixed', left: izquierda, bottom: window.innerHeight - r.top }
    : { position: 'fixed', left: izquierda, top: r.bottom }
}

/**
 * Descripción breve de un nombre técnico, al pasar el cursor o al enfocarlo con
 * el teclado.
 *
 * Para los ids que viven en los datos (clases y conjuntos de prompts, slugs): la
 * explicación se arma con lo que el propio dato declara, no con una tabla
 * escrita a mano que envejece. El vocabulario fijo del proyecto (CR-01, E-DIR…)
 * sigue en el glosario, con `Termino`. Los dos se ven igual.
 *
 * - `children` interactivo (un botón, un enlace): se pasa una función que recibe
 *   `aria-describedby`; la envoltura no suma otra parada de tabulación.
 * - `children` que no lo es (una etiqueta, una celda): la envoltura se vuelve
 *   enfocable, para que el teclado llegue.
 * - Escape la cierra sin mover el foco (WCAG 1.4.13); el cursor puede pasar sobre
 *   ella sin que desaparezca.
 * - Sin hover (pantalla táctil) la ayuda aparece al enfocar. Lo que no se pueda
 *   perder en una pantalla táctil no debe vivir solo acá: ver `Toggletip`.
 */
export default function Ayuda({
  titulo, texto, ejemplo, nota, children,
}: {
  titulo?: string
  texto?: string
  /** Una frase literal, en monoespaciada: lo que de verdad se le manda al modelo. */
  ejemplo?: string
  /** Un renglón aparte, más tenue: estados y advertencias. */
  nota?: string
  children: ReactNode | ((props: AyudaProps) => ReactElement)
}) {
  const id = useId()
  const raiz = useRef<HTMLSpanElement>(null)
  const [oculto, setOculto] = useState(false)
  const [lugar, setLugar] = useState<CSSProperties>({ position: 'fixed' })
  const medir = () => { if (raiz.current) setLugar(ubicar(raiz.current)) }
  const interactivo = typeof children === 'function'
  const hayAyuda = Boolean(titulo || texto || ejemplo || nota)
  // Sin nada que decir no se ofrece ayuda: ni se marca ni se anuncia.
  if (!hayAyuda) return <>{interactivo ? children({} as AyudaProps) : children}</>

  return (
    <span
      className="eo-ayuda"
      ref={raiz}
      data-oculto={oculto ? '' : undefined}
      tabIndex={interactivo ? undefined : 0}
      aria-describedby={interactivo ? undefined : id}
      onKeyDown={(e) => {
        if (e.key === 'Escape') setOculto(true)
      }}
      onMouseEnter={medir}
      onFocus={medir}
      onMouseLeave={() => setOculto(false)}
      onBlur={() => setOculto(false)}
    >
      {interactivo ? children({ 'aria-describedby': id }) : children}
      <span className="eo-ayuda__def" id={id} role="tooltip" style={lugar}>
        <span className="eo-ayuda__caja">
          {titulo && <b className="eo-ayuda__tit">{titulo}</b>}
          {texto && <span className="eo-ayuda__txt">{texto}</span>}
          {ejemplo && <code className="eo-ayuda__ej">{ejemplo}</code>}
          {nota && <span className="eo-ayuda__nota">{nota}</span>}
        </span>
      </span>
    </span>
  )
}
