import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

export default function Nav() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <nav className={`nav ${scrolled ? 'nav--solid' : ''}`} aria-label="Main">
      <div className="wrap nav__inner">
        <Link to="/" className="nav__brand">Beautiful Nothing</Link>
        <div className="nav__links">
          <a href="/#stories">The stories</a>
          <a href="/#author">The author</a>
          <a href="/#get" className="btn btn--red btn--sm">Get the book</a>
        </div>
      </div>
    </nav>
  )
}
