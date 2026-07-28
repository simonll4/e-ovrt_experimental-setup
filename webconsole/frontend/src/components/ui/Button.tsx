import type { ButtonHTMLAttributes } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'

export default function Button({
  variant = 'secondary',
  className,
  ...rest
}: { variant?: ButtonVariant } & ButtonHTMLAttributes<HTMLButtonElement>) {
  const cls = ['eo-btn', `eo-btn--${variant}`, className].filter(Boolean).join(' ')
  return <button type="button" className={cls} {...rest} />
}
