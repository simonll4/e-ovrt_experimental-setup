import {
  useCallback, useEffect, useId, useLayoutEffect, useRef, useState,
  type KeyboardEvent as ReactKeyboardEvent,
} from 'react'
import { createPortal } from 'react-dom'
import { joinIds, useField } from './Field'
import { IconCheck, IconChevron } from './icons'

export interface SelectOption {
  value: string
  label: string
  disabled?: boolean
  disabledReason?: string
}

/** Posición de la lista flotante, en coordenadas de la ventana. */
interface Lugar {
  top?: number
  bottom?: number
  left: number
  width: number
  maxHeight: number
}

const ALTO_MAXIMO = 280
const MARGEN = 8

/** Dónde se monta la lista. Fuera de cualquier contenedor con overflow (una
 *  tabla con scroll, una tarjeta), pero dentro del diálogo modal si el control
 *  vive en uno: lo que queda fuera de un `<dialog>` modal es inerte. */
function destinoDelPortal(boton: HTMLElement | null): Element {
  return boton?.closest('dialog') ?? document.body
}

/**
 * Selector propio con el comportamiento de un listbox completo.
 *
 * El `<select>` del sistema rompía el lenguaje visual; el reemplazo anterior
 * copiaba su aspecto pero no su teclado (no se podía elegir sin mouse). Éste:
 *
 * - Enter / Espacio / flechas abren; el foco pasa a la lista y la opción activa
 *   se anuncia con `aria-activedescendant`.
 * - Flechas, Inicio/Fin y escribir las primeras letras recorren sólo las
 *   opciones habilitadas; Enter o Espacio confirman UNA vez.
 * - Escape cierra sin cambiar el valor y devuelve el foco al botón; Tab cierra
 *   y sigue el recorrido normal desde el botón.
 * - La lista se monta en un portal con posición fija: no la recorta una tabla o
 *   una tarjeta con overflow.
 * - Una opción deshabilitada sigue visible con su motivo.
 */
export default function Select({
  value,
  options,
  onChange,
  placeholder,
  ariaLabel,
  id,
  disabled,
  'aria-labelledby': ariaLabelledBy,
  'aria-describedby': ariaDescribedBy,
  'aria-invalid': ariaInvalid,
}: {
  value: string
  options: SelectOption[]
  onChange: (value: string) => void
  placeholder?: string
  /** Nombre accesible del control. Dentro de un `Field` no hace falta: el
   *  botón toma el rótulo del campo por `aria-labelledby`. */
  ariaLabel?: string
  id?: string
  disabled?: boolean
  'aria-labelledby'?: string
  'aria-describedby'?: string
  'aria-invalid'?: boolean
}) {
  const field = useField()
  const auto = useId()
  const botonId = id ?? field?.controlId ?? `${auto}boton`
  const listaId = `${auto}lista`
  const opcionId = (i: number) => `${auto}op${i}`

  const [abierta, setAbierta] = useState(false)
  const [activa, setActiva] = useState(-1)
  const [lugar, setLugar] = useState<Lugar | null>(null)
  const botonRef = useRef<HTMLButtonElement>(null)
  const listaRef = useRef<HTMLUListElement>(null)
  // Escribir para buscar: lo tecleado en el último medio segundo.
  const tecleo = useRef({ texto: '', hasta: 0 })
  // Confirmar con Espacio cierra la lista y devuelve el foco al botón; el
  // `keyup` de esa misma tecla llega al botón y lo activaría de nuevo.
  const ignorarClick = useRef(false)

  const seleccionada = options.findIndex((o) => o.value === value)
  const habilitadas = options.flatMap((o, i) => (o.disabled ? [] : [i]))

  const medir = useCallback(() => {
    const boton = botonRef.current
    if (!boton) return
    const r = boton.getBoundingClientRect()
    const abajo = window.innerHeight - r.bottom - MARGEN
    const arriba = r.top - MARGEN
    const width = Math.max(r.width, 160)
    const left = Math.max(MARGEN, Math.min(r.left, window.innerWidth - width - MARGEN))
    if (abajo >= Math.min(ALTO_MAXIMO, 160) || abajo >= arriba) {
      setLugar({ top: r.bottom + 4, left, width, maxHeight: Math.max(120, Math.min(ALTO_MAXIMO, abajo)) })
    } else {
      setLugar({
        bottom: window.innerHeight - r.top + 4,
        left,
        width,
        maxHeight: Math.max(120, Math.min(ALTO_MAXIMO, arriba)),
      })
    }
  }, [])

  const abrir = (desde: 'seleccionada' | 'primera' | 'ultima' = 'seleccionada') => {
    if (disabled) return
    let inicio = seleccionada >= 0 && !options[seleccionada]?.disabled ? seleccionada : habilitadas[0] ?? -1
    if (desde === 'primera') inicio = habilitadas[0] ?? -1
    if (desde === 'ultima') inicio = habilitadas[habilitadas.length - 1] ?? -1
    setActiva(inicio)
    medir()
    setAbierta(true)
  }

  const cerrar = useCallback((devolverFoco: boolean) => {
    setAbierta(false)
    setActiva(-1)
    if (devolverFoco) botonRef.current?.focus()
  }, [])

  const ignorarProximoClick = () => {
    ignorarClick.current = true
    // Si la tecla se suelta en otro lado, el siguiente click real no se pierde.
    window.setTimeout(() => { ignorarClick.current = false }, 1000)
  }

  const confirmar = (i: number, porTeclado: boolean) => {
    const opcion = options[i]
    if (!opcion || opcion.disabled) return
    if (porTeclado) ignorarProximoClick()
    cerrar(true)
    onChange(opcion.value)
  }

  // Al abrir, el foco pasa a la lista: es ella la que recibe el teclado y la
  // que anuncia la opción activa.
  useLayoutEffect(() => {
    if (abierta) listaRef.current?.focus()
  }, [abierta])

  // La opción activa siempre a la vista dentro de la lista con scroll.
  useEffect(() => {
    if (!abierta || activa < 0) return
    const el = document.getElementById(opcionId(activa))
    el?.scrollIntoView?.({ block: 'nearest' })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [abierta, activa])

  // Click afuera, Escape global y reposicionamiento mientras está abierta.
  useEffect(() => {
    if (!abierta) return
    const afuera = (e: MouseEvent) => {
      const t = e.target as Node
      if (botonRef.current?.contains(t) || listaRef.current?.contains(t)) return
      cerrar(false)
    }
    const escape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') cerrar(true)
    }
    const reubicar = () => medir()
    document.addEventListener('mousedown', afuera)
    document.addEventListener('keydown', escape)
    window.addEventListener('resize', reubicar)
    window.addEventListener('scroll', reubicar, true)
    return () => {
      document.removeEventListener('mousedown', afuera)
      document.removeEventListener('keydown', escape)
      window.removeEventListener('resize', reubicar)
      window.removeEventListener('scroll', reubicar, true)
    }
  }, [abierta, cerrar, medir])

  const mover = (paso: 1 | -1) => {
    if (!habilitadas.length) return
    const pos = habilitadas.indexOf(activa)
    if (pos === -1) {
      setActiva(paso === 1 ? habilitadas[0] : habilitadas[habilitadas.length - 1])
      return
    }
    const siguiente = Math.min(habilitadas.length - 1, Math.max(0, pos + paso))
    setActiva(habilitadas[siguiente])
  }

  const buscar = (letra: string) => {
    const ahora = Date.now()
    const t = tecleo.current
    t.texto = ahora < t.hasta ? t.texto + letra.toLowerCase() : letra.toLowerCase()
    t.hasta = ahora + 500
    // Repetir la misma letra recorre las opciones que empiezan con ella.
    const repetida = t.texto.length > 1 && [...t.texto].every((c) => c === t.texto[0])
    const prefijo = repetida ? t.texto[0] : t.texto
    const desde = habilitadas.indexOf(activa)
    const orden = [...habilitadas.slice(desde + 1), ...habilitadas.slice(0, desde + 1)]
    const candidatas = repetida || t.texto.length === 1 ? orden : [activa, ...orden].filter((i) => i >= 0)
    const encontrada = candidatas.find((i) => options[i].label.toLowerCase().startsWith(prefijo))
    if (encontrada != null) setActiva(encontrada)
  }

  const teclaEnLista = (e: ReactKeyboardEvent<HTMLUListElement>) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        mover(1)
        return
      case 'ArrowUp':
        e.preventDefault()
        mover(-1)
        return
      case 'Home':
        e.preventDefault()
        if (habilitadas.length) setActiva(habilitadas[0])
        return
      case 'End':
        e.preventDefault()
        if (habilitadas.length) setActiva(habilitadas[habilitadas.length - 1])
        return
      case 'Enter':
      case ' ':
        e.preventDefault()
        if (activa >= 0) confirmar(activa, true)
        return
      case 'Escape':
        e.preventDefault()
        e.stopPropagation()
        e.nativeEvent.stopImmediatePropagation?.()
        ignorarProximoClick()
        cerrar(true)
        return
      case 'Tab':
        // Sin preventDefault: el foco vuelve al botón y el navegador sigue el
        // recorrido desde ahí, hacia adelante o hacia atrás.
        cerrar(true)
        return
      default:
        if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
          e.preventDefault()
          buscar(e.key)
        }
    }
  }

  const teclaEnBoton = (e: ReactKeyboardEvent<HTMLButtonElement>) => {
    if (abierta) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      abrir('seleccionada')
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      abrir('seleccionada')
    } else if (e.key === 'Home') {
      e.preventDefault()
      abrir('primera')
    } else if (e.key === 'End') {
      e.preventDefault()
      abrir('ultima')
    }
  }

  // El botón se nombra «rótulo + valor» (patrón de APG del listbox
  // desplegable): el lector anuncia qué campo es y qué tiene elegido. La
  // lista sólo lleva el rótulo.
  const rotuloId = `${auto}rotulo`
  const valorId = `${auto}valor`
  const rotulo = ariaLabel ? rotuloId : ariaLabelledBy ?? field?.labelId

  const lista = abierta && (
    <ul
      ref={listaRef}
      id={listaId}
      className="eo-select__list"
      role="listbox"
      tabIndex={-1}
      aria-labelledby={rotulo}
      aria-activedescendant={activa >= 0 ? opcionId(activa) : undefined}
      onKeyDown={teclaEnLista}
      style={
        lugar
          ? {
              position: 'fixed',
              top: lugar.top,
              bottom: lugar.bottom,
              left: lugar.left,
              width: lugar.width,
              maxHeight: lugar.maxHeight,
            }
          : { position: 'fixed' }
      }
    >
      {options.length === 0 && <li className="eo-select__none">Sin opciones</li>}
      {options.map((opt, i) => {
        const motivoId = opt.disabled && opt.disabledReason ? `${opcionId(i)}m` : undefined
        return (
          <li
            key={opt.value}
            id={opcionId(i)}
            role="option"
            aria-selected={opt.value === value}
            aria-disabled={opt.disabled || undefined}
            aria-label={opt.label}
            aria-describedby={motivoId}
            title={opt.disabled ? opt.disabledReason : undefined}
            className={
              'eo-select__option' +
              (opt.value === value ? ' eo-select__option--selected' : '') +
              (opt.disabled ? ' eo-select__option--disabled' : '') +
              (i === activa ? ' is-active' : '')
            }
            // Que el click no le saque el foco a la lista antes de confirmar.
            onMouseDown={(event) => event.preventDefault()}
            onMouseEnter={() => {
              if (!opt.disabled) setActiva(i)
            }}
            onClick={(event) => {
              // Un `<label>` que envuelva al selector reenviaría este click al
              // botón y reabriría la lista.
              event.preventDefault()
              confirmar(i, false)
            }}
          >
            <span className="eo-select__mark" aria-hidden="true">
              {opt.value === value ? <IconCheck /> : null}
            </span>
            <span className="eo-select__text">
              <span>{opt.label}</span>
              {motivoId ? (
                <span className="eo-select__reason" id={motivoId}>{opt.disabledReason}</span>
              ) : null}
            </span>
          </li>
        )
      })}
    </ul>
  )

  return (
    <div className="eo-select">
      <button
        ref={botonRef}
        type="button"
        id={botonId}
        className="eo-select__control"
        aria-haspopup="listbox"
        aria-expanded={abierta}
        aria-controls={abierta ? listaId : undefined}
        aria-describedby={joinIds(field?.describedBy, ariaDescribedBy)}
        aria-invalid={ariaInvalid ?? (field?.invalid ? true : undefined)}
        disabled={disabled}
        aria-labelledby={rotulo ? `${rotulo} ${valorId}` : undefined}
        onClick={() => {
          if (ignorarClick.current) {
            ignorarClick.current = false
            return
          }
          if (abierta) cerrar(true)
          else abrir()
        }}
        onKeyDown={teclaEnBoton}
        onKeyUp={(e) => {
          if (!ignorarClick.current) return
          // Espacio activa el botón al soltarse: se cancela, y el click que
          // igual llegue lo descarta `onClick`. Enter ya actuó en la lista.
          if (e.key === ' ') e.preventDefault()
          else if (e.key === 'Enter' || e.key === 'Escape') ignorarClick.current = false
        }}
      >
        <span id={valorId} className={seleccionada >= 0 ? 'eo-select__value' : 'eo-select__value eo-select__value--empty'}>
          {seleccionada >= 0 ? options[seleccionada].label : placeholder ?? 'Elegir…'}
        </span>
        <span className="eo-select__caret" aria-hidden="true"><IconChevron /></span>
      </button>
      {ariaLabel ? <span id={rotuloId} hidden>{ariaLabel}</span> : null}
      {lista ? createPortal(lista, destinoDelPortal(botonRef.current)) : null}
    </div>
  )
}
