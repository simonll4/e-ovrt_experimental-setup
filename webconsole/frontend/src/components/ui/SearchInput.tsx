import { IconSearch } from './icons'

export default function SearchInput({
  value,
  onChange,
  placeholder,
  ariaLabel,
}: {
  value: string
  onChange: (value: string) => void
  placeholder: string
  ariaLabel: string
}) {
  return (
    <div className="eo-search">
      <span className="eo-search__icon" aria-hidden="true">
        <IconSearch />
      </span>
      <input
        type="search"
        className="eo-search__input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={ariaLabel}
      />
    </div>
  )
}
