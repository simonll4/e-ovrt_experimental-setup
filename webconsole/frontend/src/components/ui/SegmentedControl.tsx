export interface SegmentedOption<T extends string> {
  value: T
  label: string
}

export default function SegmentedControl<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T
  options: Array<SegmentedOption<T>>
  onChange: (value: T) => void
}) {
  return (
    <div className="eo-segmented">
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
