// A ripped-paper edge, like the torn strip on the book cover.
// Sits at the top of a section and is filled with that section's colour.
function tornPath(seed, w = 1440, h = 48) {
  let s = seed
  const rnd = () => ((s = (s * 9301 + 49297) % 233280), s / 233280)
  let d = `M0 ${h} L0 ${(h * 0.55).toFixed(1)}`
  for (let x = 0; x < w; x += 10 + rnd() * 26) {
    d += ` L${x.toFixed(1)} ${(h * 0.18 + rnd() * h * 0.62).toFixed(1)}`
  }
  return `${d} L${w} ${(h * 0.5).toFixed(1)} L${w} ${h} Z`
}

export default function TornEdge({ color, seed = 7, className = '' }) {
  return (
    <svg className={`torn ${className}`} viewBox="0 0 1440 48" preserveAspectRatio="none" aria-hidden="true">
      <path d={tornPath(seed)} fill={color} />
    </svg>
  )
}
