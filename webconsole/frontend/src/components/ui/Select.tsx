import { useEffect, useRef, useState } from 'react'

export interface SelectOption {
  value: string
  label: string
  disabled?: boolean
  disabledReason?: string
}

export default function Select({
  value,
  options,
  onChange,
  placeholder,
  ariaLabel,
}: {
  value: string
  options: SelectOption[]
  onChange: (value: string) => void
  placeholder?: string
  /** Nombre accesible del control. Hace falta cuando va dentro de un `Field`: el
   *  control es un <button>, y un <button> no se asocia por envoltura con un
   *  <label> como sí lo hace un <select> nativo. */
  ariaLabel?: string
}) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const selected = options.find((o) => o.value === value)

  useEffect(() => {
    if (!open) return
    const onDocClick = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDocClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const pick = (opt: SelectOption) => {
    if (opt.disabled) return
    onChange(opt.value)
    setOpen(false)
  }

  return (
    <div className="eo-select" ref={rootRef}>
      <button
        type="button"
        className="eo-select__control"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={ariaLabel}
        onClick={() => setOpen((o) => !o)}
      >
        <span>{selected ? selected.label : placeholder ?? 'Elegir…'}</span>
        <span className="eo-select__caret" aria-hidden="true">▾</span>
      </button>
      {open && (
        <ul className="eo-select__list" role="listbox">
          {options.map((opt) => (
            <li
              key={opt.value}
              role="option"
              aria-selected={opt.value === value}
              aria-disabled={opt.disabled}
              aria-label={opt.label}
              title={opt.disabled ? opt.disabledReason : undefined}
              className={
                'eo-select__option' +
                (opt.value === value ? ' eo-select__option--selected' : '') +
                (opt.disabled ? ' eo-select__option--disabled' : '')
              }
              onClick={() => pick(opt)}
            >
              <span>{opt.label}</span>
              {opt.disabled && opt.disabledReason ? (
                <span className="eo-select__reason">{opt.disabledReason}</span>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
