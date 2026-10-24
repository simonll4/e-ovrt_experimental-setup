import { forwardRef, type ButtonHTMLAttributes } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'

const Button = forwardRef<HTMLButtonElement, { variant?: ButtonVariant } & ButtonHTMLAttributes<HTMLButtonElement>>(
  function Button({ variant = 'secondary', className, ...rest }, ref) {
    const cls = ['eo-btn', `eo-btn--${variant}`, className].filter(Boolean).join(' ')
    return <button ref={ref} type="button" className={cls} {...rest} />
  },
)

export default Button
