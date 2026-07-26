import { CONDITION_NAMES } from '../../labels'

export default function ConditionName({ code }: { code: string }) {
  const name = CONDITION_NAMES[code]
  return (
    <>
      <span className="eo-mono">{code}</span>
      {name ? ` — ${name}` : null}
    </>
  )
}
