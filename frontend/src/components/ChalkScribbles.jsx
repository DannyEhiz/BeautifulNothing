import { useEffect, useState } from 'react'

// Loko scribbles on the walls of Dagbolu, beautiful handwriting and always dated.
// The hero borrows that idea: chalk phrases write themselves in, linger, then fade out.
const PHRASES = [
  'what the eye cannot see — 14.iii.97',
  'running to…',
  'life sweet',
  '(ab)ⁿ = aⁿbⁿ',
  'lim c = c',
  'memories',
  'learning',
  'climbs',
  'the passage at dusk — 02.x.89',
  'who pays the dead? — 21.vi.04',
  'beautiful nothing',
  'ancestors eat first',
  'a code, or nothing? — 09.ix.11',
  'e^iπ + 1 = 0',
  'faith ≠ sight',
]

// Slots (in % of the hero) chosen to sit around, not on top of, the headline and book.
const SLOTS = [
  { x: 3, y: 12 }, { x: 30, y: 6 }, { x: 58, y: 9 }, { x: 80, y: 16 },
  { x: 4, y: 82 }, { x: 34, y: 90 }, { x: 62, y: 86 }, { x: 82, y: 76 },
  { x: 86, y: 44 }, { x: 46, y: 50 }, { x: 2, y: 48 }, { x: 70, y: 60 },
]

const LIFE = 9000
const pick = (arr) => arr[Math.floor(Math.random() * arr.length)]

function spawn(prev, id) {
  const usedSlots = new Set(prev.map((p) => p.slot))
  const usedText = new Set(prev.map((p) => p.text))
  const slot = pick(SLOTS.map((_, i) => i).filter((i) => !usedSlots.has(i)))
  const text = pick(PHRASES.filter((t) => !usedText.has(t)))
  return { id, slot, text, born: Date.now(), rot: (Math.random() * 10 - 5).toFixed(1) }
}

export default function ChalkScribbles() {
  const [items, setItems] = useState(() => {
    let list = []
    for (let i = 0; i < 4; i++) list = [...list, spawn(list, -i - 1)]
    return list
  })

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    let id = 0
    const t = setInterval(() => {
      setItems((prev) => {
        const alive = prev.filter((p) => Date.now() - p.born < LIFE)
        return [...alive, spawn(alive, id++)]
      })
    }, 1500)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="scribbles" aria-hidden="true">
      {items.map((s) => (
        <span
          key={s.id}
          className="scribble"
          style={{ left: `${SLOTS[s.slot].x}%`, top: `${SLOTS[s.slot].y}%`, '--rot': `${s.rot}deg` }}
        >
          {s.text}
        </span>
      ))}
    </div>
  )
}
