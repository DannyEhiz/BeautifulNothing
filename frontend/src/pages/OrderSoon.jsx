import { Link } from 'react-router-dom'
import Nav from '../components/Nav.jsx'
import ChalkUnderline from '../components/ChalkUnderline.jsx'
import { PRICES, naira } from '../config.js'

// Placeholder until the paperback sales page is built.
export default function OrderSoon() {
  return (
    <>
      <Nav />
      <main className="soon board">
        <div className="wrap soon__inner">
          <p className="kicker kicker--chalk">Paperback · {naira(PRICES.paperback)} delivered</p>
          <h1 className="chalk-title soon__title">Orders open here soon</h1>
          <ChalkUnderline className="soon__swoosh" />
          <p className="soon__text">
            We are putting the finishing touches on paperback ordering. Check back shortly to have your copy of{' '}
            <em>Beautiful Nothing</em> delivered to your door.
          </p>
          <Link className="btn btn--ghost" to="/">← Back to the book</Link>
        </div>
      </main>
    </>
  )
}
