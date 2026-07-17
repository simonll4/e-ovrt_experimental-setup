import type { ReactNode } from 'react'

export default function ErrorBanner({ children }: { children: ReactNode }) {
  return <div className="eo-error" role="alert">{children}</div>
}
