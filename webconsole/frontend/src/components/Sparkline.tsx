export default function Sparkline({ values, width = 220, height = 40 }: {
  values: number[]; width?: number; height?: number
}) {
  if (values.length < 2) return <svg width={width} height={height} />
  const max = Math.max(...values, 1e-9)
  const points = values
    .map((v, i) => `${(i / (values.length - 1)) * width},${height - (v / max) * (height - 2)}`)
    .join(' ')
  return (
    <svg width={width} height={height}>
      <polyline points={points} fill="none" stroke="#36c" strokeWidth={1.5} />
    </svg>
  )
}
