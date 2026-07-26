import Button from './Button'

export default function InlineDeleteConfirm({
  onConfirm,
  onCancel,
}: {
  onConfirm: () => void
  onCancel: () => void
}) {
  return (
    <span className="eo-delete-confirm">
      ¿Borrar?
      <Button variant="danger" onClick={onConfirm}>Sí, borrar</Button>
      <Button variant="ghost" onClick={onCancel}>No</Button>
    </span>
  )
}
