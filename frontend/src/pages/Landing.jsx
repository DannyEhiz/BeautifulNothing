import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import Nav from '../components/Nav.jsx'
import Footer from '../components/Footer.jsx'
import ChalkScribbles from '../components/ChalkScribbles.jsx'
import ChalkUnderline from '../components/ChalkUnderline.jsx'
import TornEdge from '../components/TornEdge.jsx'
import { PRICES, SELAH_URL, naira } from '../config.js'
import { track } from '../lib/track.js'
import { useReveal } from '../lib/useReveal.js'

// Headings and kickers are descriptive, not the real story titles. Swap them in once confirmed.
const STORIES = [
  {
    num: 'I',
    kicker: 'London · Ogboni',
    title: 'A body far from home',
    text: 'A Yoruba chief dies in London and his children rebuff the Ogboni confraternity’s demand that the body be repatriated to Nigeria for traditional burial rites, citing the cost. Soon, a mysterious string of deaths begins to ravage the family.',
    scrawl: 'who pays the dead?',
  },
  {
    num: 'II',
    kicker: 'A passage · An apparition',
    title: 'What the boy saw',
    text: 'A little Christian boy mocks his grandmother and their landlady’s habit of invoking and offering food to invisible ancestors. But his certainty about the foolishness of their beliefs is shattered one evening when he encounters an apparition in the passage of their house.',
    scrawl: 'ancestors eat first',
  },
  {
    num: 'III',
    kicker: 'Dagbolu · Charcoal',
    title: 'The writing on the wall',
    text: 'Loko roams Dagbolu town shirtless, clutching a piece of charcoal and scribbling on walls. The community has stories about the beloved schoolteacher who suddenly ran mad. His handwriting remains beautiful, but no one can make sense of the compositions he leaves behind wherever he pauses.',
    scrawl: 'a code, or nothing? — 09.ix.11',
  },
]

// Loko's wall: lines of charcoal handwriting behind the question the third story asks.
const WALL = [
  'the river remembers its source — 03.ii.98',
  'what the eye cannot see is still seeing you',
  '12 + 7 = the night the lamp went out — 17.v.01',
  'they said I ran mad. I ran towards — 30.x.26',
  'àṣẹ',
  'beautiful nothing, beautiful nothing — 11.xi.09',
  'chalk is only charcoal that forgot — 05.iv.13',
  'count the doors in the passage',
]

const TIMELINE = [
  { when: 'Trained', what: 'Veterinary surgeon, University of Ibadan' },
  { when: '5 years', what: 'In veterinary practice' },
  { when: '2014', what: 'Left the clinic to pursue a lifelong passion for writing' },
  { when: 'Editor', what: 'News Editor, The PUNCH newspaper' },
  { when: 'Now', what: 'Writes for The Africa Report, headquartered in Paris' },
  { when: 'Debut', what: 'Beautiful Nothing, his first work of fiction' },
]

let visitTracked = false // StrictMode runs effects twice in dev; count a page view once.

function Hero() {
  const bookRef = useRef(null)

  // Gentle 3D tilt that follows the pointer (desktop only).
  useEffect(() => {
    const fine = window.matchMedia('(pointer: fine)').matches
    const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (!fine || still) return
    let raf = 0
    const onMove = (e) => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        const x = e.clientX / window.innerWidth - 0.5
        const y = e.clientY / window.innerHeight - 0.5
        bookRef.current?.style.setProperty('--ry', `${(x * 14).toFixed(2)}deg`)
        bookRef.current?.style.setProperty('--rx', `${(-y * 8).toFixed(2)}deg`)
      })
    }
    window.addEventListener('pointermove', onMove)
    return () => {
      window.removeEventListener('pointermove', onMove)
      cancelAnimationFrame(raf)
    }
  }, [])

  return (
    <header className="hero board">
      <ChalkScribbles />
      <div className="wrap hero__inner">
        <div className="hero__copy">
          <p className="eyebrow">
            <span className="eyebrow__dot" /> Out now · A debut collection
          </p>
          <h1 className="hero__title">
            <span className="hero__line">Beautiful</span>
            <span className="hero__line">Nothing</span>
          </h1>
          <p className="hero__stories">
            Stories
            <ChalkUnderline />
          </p>
          <p className="hero__lede">
            Where faith collides, and the line between the physical and the spiritual quietly gives way.
          </p>
          <div className="hero__ctas">
            <a className="btn btn--red" href="#get">Get the book</a>
            <a className="btn btn--ghost" href="#stories">Meet the stories</a>
          </div>
          <p className="hero__prices">
            Ebook {naira(PRICES.ebook)} <span aria-hidden="true">·</span> Paperback {naira(PRICES.paperback)}, delivered
          </p>
        </div>

        <div className="hero__book" ref={bookRef}>
          <img
            src="/img/book-3d.webp"
            alt="Beautiful Nothing by Oladimeji Ramon, hardback cover"
            width="487"
            height="863"
            fetchpriority="high"
          />
          <span className="hero__shadow" aria-hidden="true" />
        </div>
      </div>
      <a className="hero__scroll" href="#book" aria-label="Scroll to read about the book">
        <span>scroll</span>
      </a>
    </header>
  )
}

function SelahButton() {
  const [soon, setSoon] = useState(false)
  const onClick = (e) => {
    track('selah_click')
    if (!SELAH_URL) {
      e.preventDefault()
      setSoon(true)
    }
  }
  return (
    <>
      <a
        className="btn btn--ink btn--block"
        href={SELAH_URL || '#get'}
        target={SELAH_URL ? '_blank' : undefined}
        rel="noopener noreferrer"
        onClick={onClick}
      >
        Buy on Selah <span aria-hidden="true">↗</span>
      </a>
      <p className="option__note" aria-live="polite">
        {soon ? 'The Selah link goes live very soon. Please check back shortly.' : 'Read on your phone, tablet or laptop.'}
      </p>
    </>
  )
}

export default function Landing() {
  useReveal()

  useEffect(() => {
    if (visitTracked) return
    visitTracked = true
    track('visit')
  }, [])

  return (
    <>
      <Nav />
      <Hero />

      <main>
        {/* The book */}
        <section id="book" className="section paper">
          <TornEdge color="var(--paper)" seed={11} />
          <div className="wrap about">
            <p className="kicker" data-reveal>The book</p>
            <h2 className="statement" data-reveal>
              Between what we believe and what we see, there is a passage.{' '}
              <em>These stories walk it.</em>
            </h2>
            <div className="about__body" data-reveal>
              <p className="dropcap">
                <em>Beautiful Nothing</em> is a collection of short stories exploring the clash of faith and the
                blurred line between the physical and the spiritual.
              </p>
              <p>
                Across its varied tales, the characters are confronted with experiences that unsettle their beliefs,
                leaving them grappling with the possibility of alternative realities beyond what the eyes can see.
              </p>
            </div>
            <dl className="facts" data-reveal>
              <div><dt>Form</dt><dd>Short stories</dd></div>
              <div><dt>Worlds</dt><dd>Nigeria &amp; London</dd></div>
              <div><dt>Editions</dt><dd>Ebook &amp; paperback</dd></div>
              <div><dt>Author</dt><dd>Oladimeji Ramon</dd></div>
            </dl>
          </div>
        </section>

        {/* The stories */}
        <section id="stories" className="section board">
          <TornEdge color="var(--board)" seed={23} />
          <div className="wrap">
            <header className="section-head" data-reveal>
              <p className="kicker kicker--chalk">Inside</p>
              <h2 className="chalk-title">Three doors into the book</h2>
              <p className="section-head__sub">A glimpse of three of the tales waiting inside.</p>
            </header>
            <div className="notes">
              {STORIES.map((s, i) => (
                <article key={s.num} className="note" style={{ '--tilt': `${[-1.6, 1.2, -0.8][i]}deg`, '--d': `${i * 90}ms` }} data-reveal>
                  <span className="note__tape" aria-hidden="true" />
                  <span className="note__num" aria-hidden="true">{s.num}</span>
                  <p className="note__kicker">{s.kicker}</p>
                  <h3 className="note__title">{s.title}</h3>
                  <p className="note__text">{s.text}</p>
                  <p className="note__scrawl" aria-hidden="true">{s.scrawl}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* Loko's wall */}
        <section className="wall board" aria-label="A question from the book">
          <div className="wall__scrawl" aria-hidden="true">
            {WALL.map((line, i) => (
              <span key={i} style={{ '--i': i }}>{line}</span>
            ))}
          </div>
          <div className="wrap wall__inner" data-reveal>
            <p className="wall__q">
              Are the writings mere ramblings of a troubled mind,
              <br />
              <em>or a code carrying a message?</em>
            </p>
          </div>
        </section>

        {/* Praise */}
        <section className="section paper praise">
          <TornEdge color="var(--paper)" seed={41} />
          <figure className="wrap praise__fig" data-reveal>
            <span className="praise__mark" aria-hidden="true">“</span>
            <blockquote>
              Reading <em>Beautiful Nothing</em> feels like listening to stories told by someone with a deep connection
              to their roots. Ramon has a real gift for creating compelling characters and drawing the reader into
              their world.
            </blockquote>
            <figcaption>
              <strong>Akin Akingbogun</strong>
              <span>author of <em>Damaged Goods</em></span>
            </figcaption>
          </figure>
        </section>

        {/* Author */}
        <section id="author" className="section board author">
          <TornEdge color="var(--board)" seed={57} />
          <div className="wrap author__grid">
            <figure className="polaroid" data-reveal>
              <span className="polaroid__tape" aria-hidden="true" />
              <img src="/img/oladimeji-ramon.jpg" alt="Portrait of Oladimeji Ramon" width="1041" height="1280" loading="lazy" />
              <figcaption>Oladimeji Ramon</figcaption>
            </figure>
            <div className="author__copy">
              <p className="kicker kicker--chalk" data-reveal>The author</p>
              <h2 className="chalk-title" data-reveal>Oladimeji Ramon</h2>
              <p className="author__tag" data-reveal>
                Journalist. Storyteller. Painter. <span>Once, a veterinary surgeon.</span>
              </p>
              <p className="author__bio" data-reveal>
                Oladimeji Ramon is an award-winning journalist, fiction writer and part-time painter. He trained as a
                veterinary surgeon at the University of Ibadan and worked in veterinary practice for five years before
                switching careers in 2014 to pursue his lifelong passion for writing. He served as News Editor at{' '}
                <em>The PUNCH</em> newspaper and currently writes for <em>The Africa Report</em>, headquartered in
                Paris, France. <em>Beautiful Nothing</em> marks his debut in fiction.
              </p>
              <ol className="timeline" data-reveal>
                {TIMELINE.map((t) => (
                  <li key={t.when}>
                    <span className="timeline__when">{t.when}</span>
                    <span className="timeline__what">{t.what}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </section>

        {/* Get the book */}
        <section id="get" className="section sand get">
          <TornEdge color="var(--sand)" seed={73} />
          <div className="wrap get__grid">
            <div className="get__visual" data-reveal>
              <img src="/img/books-pair.jpg" alt="Two copies of Beautiful Nothing standing side by side" width="1213" height="1280" loading="lazy" />
            </div>
            <div className="get__copy">
              <p className="kicker" data-reveal>Get your copy</p>
              <h2 className="get__title" data-reveal>Two ways in.</h2>
              <p className="get__sub" data-reveal>Read it tonight on your screen, or hold it in your hands.</p>

              <div className="options">
                <article className="option" data-reveal>
                  <header className="option__head">
                    <span className="option__label">Ebook</span>
                    <span className="option__price">{naira(PRICES.ebook)}</span>
                  </header>
                  <p className="option__desc">Instant access through Selah. Start reading in minutes.</p>
                  <SelahButton />
                </article>

                <article className="option option--dark" data-reveal style={{ '--d': '90ms' }}>
                  <span className="option__badge">Delivery included</span>
                  <header className="option__head">
                    <span className="option__label">Paperback</span>
                    <span className="option__price">{naira(PRICES.paperback)}</span>
                  </header>
                  <p className="option__desc">A physical copy, delivered straight to your door.</p>
                  <Link className="btn btn--red btn--block" to="/order" onClick={() => track('order_click')}>
                    Order the paperback <span aria-hidden="true">→</span>
                  </Link>
                  <p className="option__note">Payment and delivery details on the next page.</p>
                </article>
              </div>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </>
  )
}
