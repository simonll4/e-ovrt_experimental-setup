export interface SegmentedOption<T extends string> {
  value: T
  label: string
}

export default function SegmentedControl<T extends string>({
  value,
  options,
  onChange,
  label,
}: {
  value: T
  options: Array<SegmentedOption<T>>
  onChange: (value: T) => void
  /** Qué elige el grupo. Sin él los botones se anuncian sueltos. */
  label?: string
}) {
  return (
    <div className="eo-segmented" role="group" aria-label={label}>
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          aria-pressed={opt.value === value}
          onClick={() => onChange(opt.value)}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}
