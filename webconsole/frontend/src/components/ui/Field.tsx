import { createContext, useContext, useId, type ReactNode } from 'react'

/** Lo que un campo le pasa a su control: con qué id lo apunta el `<label>`, qué
 *  textos lo describen y si está en error. Los controles del kit (`TextInput`,
 *  `TextArea`, `NativeSelect`, `Select`) lo leen; un hijo desconocido no se
 *  clona ni se le inyectan atributos. */
export interface FieldContextValue {
  controlId: string
  labelId: string
  describedBy?: string
  invalid: boolean
}

const FieldContext = createContext<FieldContextValue | null>(null)

export function useField(): FieldContextValue | null {
  return useContext(FieldContext)
}

/** Une dos listas de ids de `aria-describedby` sin dejar espacios sueltos. */
export function joinIds(...ids: Array<string | undefined | null | false>): string | undefined {
  const out = ids.filter(Boolean).join(' ').trim()
  return out || undefined
}

/**
 * Campo con su etiqueta, su ayuda y su error, asociados por id.
 *
 * El `<label>` apunta al control con `htmlFor` (no lo envuelve): envuelto, la
 * ayuda y el error terminaban formando parte del nombre accesible del control.
 * La ayuda y el error llegan al control por `aria-describedby`, y el error
 * además marca `aria-invalid`.
 *
 * `labelKey` es la clave técnica del contrato (`warmup_frames`): se muestra al
 * lado del rótulo humano, en monoespaciada, y forma parte del nombre accesible.
 */
export default function Field({
  label,
  labelKey,
  hint,
  error,
  id,
  className,
  children,
}: {
  label: ReactNode
  labelKey?: string
  hint?: ReactNode
  error?: ReactNode
  id?: string
  className?: string
  children: ReactNode
}) {
  const auto = useId()
  const controlId = id ?? `${auto}control`
  const labelId = `${auto}label`
  const hintId = `${auto}hint`
  const errorId = `${auto}error`
  const describedBy = joinIds(hint ? hintId : undefined, error ? errorId : undefined)
  const cls = ['eo-field', error ? 'eo-field--invalid' : '', className].filter(Boolean).join(' ')
  return (
    <div className={cls}>
      <label className="eo-field__label" id={labelId} htmlFor={controlId}>
        {label}
        {labelKey && <code className="eo-field__key">{labelKey}</code>}
      </label>
      <FieldContext.Provider value={{ controlId, labelId, describedBy, invalid: Boolean(error) }}>
        {children}
      </FieldContext.Provider>
      {hint ? <p className="eo-field__hint" id={hintId}>{hint}</p> : null}
      {error ? <p className="eo-field__error" id={errorId}>{error}</p> : null}
    </div>
  )
}
