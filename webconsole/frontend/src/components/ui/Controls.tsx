import type {
  InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes,
} from 'react'
import { joinIds, useField } from './Field'

/** Atributos de asociación que un control toma de su `Field`, sin pisar los
 *  que el consumidor haya pasado a mano. */
function asociar<T extends { id?: string; 'aria-describedby'?: string; 'aria-invalid'?: unknown }>(
  props: T,
  field: ReturnType<typeof useField>,
) {
  return {
    id: props.id ?? field?.controlId,
    'aria-describedby': joinIds(field?.describedBy, props['aria-describedby']),
    'aria-invalid': (props['aria-invalid'] ?? (field?.invalid ? true : undefined)) as
      | boolean
      | 'true'
      | 'false'
      | undefined,
  }
}

export function TextInput({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  const field = useField()
  return (
    <input
      {...props}
      {...asociar(props, field)}
      className={['eo-input', className].filter(Boolean).join(' ')}
    />
  )
}

export function TextArea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const field = useField()
  return (
    <textarea
      {...props}
      {...asociar(props, field)}
      className={['eo-input eo-input--area', className].filter(Boolean).join(' ')}
    />
  )
}

/** `<select>` del sistema. Se conserva donde ya estaba (formularios de
 *  derivación, grabación, recorte) porque su teclado y su lector ya funcionan;
 *  sólo se le agrega la asociación con su campo. */
export function NativeSelect({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  const field = useField()
  return (
    <select
      {...props}
      {...asociar(props, field)}
      className={['eo-input eo-input--select', className].filter(Boolean).join(' ')}
    />
  )
}
