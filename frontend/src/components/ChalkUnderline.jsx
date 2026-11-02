// The double chalk swoosh under "Stories" on the cover.
export default function ChalkUnderline({ className = '' }) {
  return (
    <svg className={`swoosh ${className}`} viewBox="0 0 220 28" aria-hidden="true">
      <path d="M4 18 C 60 6, 140 4, 214 8" />
      <path d="M14 25 C 80 15, 150 13, 208 16" />
    </svg>
  )
}
