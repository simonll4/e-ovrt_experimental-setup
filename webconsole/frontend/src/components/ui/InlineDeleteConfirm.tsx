import Button from './Button'

export default function InlineDeleteConfirm({
  onConfirm,
  onCancel,
  question = '¿Borrar?',
  confirmLabel = 'Sí, borrar',
}: {
  onConfirm: () => void
  onCancel: () => void
  question?: string
  confirmLabel?: string
}) {
  return (
    <span className="eo-delete-confirm" role="group" aria-label={question}>
      <span>{question}</span>
      <Button variant="danger" onClick={onConfirm}>{confirmLabel}</Button>
      <Button variant="ghost" onClick={onCancel}>No</Button>
    </span>
  )
}
