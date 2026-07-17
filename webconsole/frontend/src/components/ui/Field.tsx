import type { ReactNode } from 'react'

export default function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string
  hint?: string
  error?: string
  children: ReactNode
}) {
  return (
    <label className="eo-field">
      <span className="eo-field__label">{label}</span>
      {children}
      {hint && !error ? <span className="eo-field__hint">{hint}</span> : null}
      {error ? <span className="eo-field__error">{error}</span> : null}
    </label>
  )
}
