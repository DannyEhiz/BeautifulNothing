// Small progressive enhancements. Every page works without this file; it adds motion,
// tracking, dialogs, copy buttons and the live order total.
;(() => {
  const $ = (sel, root = document) => root.querySelector(sel)
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)]
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches

  // ───────── Tracking ─────────
  function visitorId() {
    try {
      let id = localStorage.getItem('bn_vid')
      if (!id) {
        id = crypto.randomUUID()
        localStorage.setItem('bn_vid', id)
      }
      return id
    } catch {
      return null
    }
  }

  // Fire-and-forget; sent as text/plain so it never needs a CORS preflight. Must never break the page.
  function track(type) {
    try {
      const body = JSON.stringify({ type, visitor_id: visitorId(), path: location.pathname, referrer: document.referrer || null })
      const blob = new Blob([body], { type: 'text/plain' })
      if (!navigator.sendBeacon?.('/api/events', blob)) fetch('/api/events', { method: 'POST', body, keepalive: true }).catch(() => {})
    } catch {
      /* ignore */
    }
  }

  if (document.body.hasAttribute('data-track-visit')) track('visit')
  $$('[data-track]').forEach((el) => el.addEventListener('click', () => track(el.dataset.track)))
  $$('form[data-track-submit]').forEach((f) => f.addEventListener('submit', () => track(f.dataset.trackSubmit)))
  $$('[data-visitor-id]').forEach((input) => (input.value = visitorId() || ''))

  // ───────── Nav turns solid once you scroll ─────────
  const nav = $('[data-nav]')
  if (nav) {
    const onScroll = () => nav.classList.toggle('nav--solid', scrollY > 40)
    onScroll()
    addEventListener('scroll', onScroll, { passive: true })
  }

  // ───────── Reveal on scroll ─────────
  const reveal = $$('[data-reveal]')
  if (!('IntersectionObserver' in window)) reveal.forEach((el) => el.classList.add('is-in'))
  else {
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && (e.target.classList.add('is-in'), io.unobserve(e.target))),
      { rootMargin: '0px 0px -10% 0px', threshold: 0.15 },
    )
    reveal.forEach((el) => io.observe(el))
  }

  // ───────── Hero chalk scribbles: Loko's dated writings appear and fade ─────────
  const board = $('[data-scribbles]')
  if (board) {
    const PHRASES = [
      'what the eye cannot see — 14.iii.97', 'running to…', 'life sweet', '(ab)ⁿ = aⁿbⁿ', 'lim c = c', 'memories',
      'learning', 'climbs', 'the passage at dusk — 02.x.89', 'who pays the dead? — 21.vi.04', 'beautiful nothing',
      'ancestors eat first', 'a code, or nothing? — 09.ix.11', 'e^iπ + 1 = 0', 'faith ≠ sight',
    ]
    // Slots (% of the hero) sit around, not on top of, the headline and book.
    const SLOTS = [[3, 12], [30, 6], [58, 9], [80, 16], [4, 82], [34, 90], [62, 86], [82, 76], [86, 44], [46, 50], [2, 48], [70, 60]]
    const LIFE = 9000
    const pick = (a) => a[Math.floor(Math.random() * a.length)]
    const spawn = () => {
      const live = $$('.scribble', board)
      const usedSlots = new Set(live.map((s) => s.dataset.slot))
      const usedText = new Set(live.map((s) => s.textContent))
      const slot = pick(SLOTS.map((_, i) => String(i)).filter((i) => !usedSlots.has(i)))
      const el = document.createElement('span')
      el.className = 'scribble'
      el.dataset.slot = slot
      el.textContent = pick(PHRASES.filter((t) => !usedText.has(t)))
      el.style.left = SLOTS[slot][0] + '%'
      el.style.top = SLOTS[slot][1] + '%'
      el.style.setProperty('--rot', (Math.random() * 10 - 5).toFixed(1) + 'deg')
      board.appendChild(el)
      if (!reducedMotion) setTimeout(() => el.remove(), LIFE)
    }
    for (let i = 0; i < 4; i++) spawn()
    if (!reducedMotion) setInterval(spawn, 1500)
  }

  // ───────── Gentle 3D tilt of the book, following the pointer (desktop only) ─────────
  const tilt = $('[data-tilt]')
  if (tilt && matchMedia('(pointer: fine)').matches && !reducedMotion) {
    let raf = 0
    addEventListener('pointermove', (e) => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        tilt.style.setProperty('--ry', ((e.clientX / innerWidth - 0.5) * 14).toFixed(2) + 'deg')
        tilt.style.setProperty('--rx', ((0.5 - e.clientY / innerHeight) * 8).toFixed(2) + 'deg')
      })
    })
  }

  // ───────── Dialogs ─────────
  $$('[data-open-dialog]').forEach((btn) =>
    btn.addEventListener('click', () => $('#dialog-' + btn.dataset.openDialog)?.showModal()),
  )
  $$('dialog.dialog').forEach((d) => {
    d.addEventListener('click', (e) => e.target === d && d.close())
    $$('[data-close-dialog]', d).forEach((b) => b.addEventListener('click', () => d.close()))
    if (d.hasAttribute('data-open-on-load')) d.showModal()
  })

  // ───────── "Coming soon" links (Selar link not live yet) ─────────
  $$('[data-soon]').forEach((a) =>
    a.addEventListener('click', (e) => {
      e.preventDefault()
      const note = a.parentElement.querySelector('[data-soon-note]')
      if (note) note.textContent = a.dataset.soon
    }),
  )

  // ───────── Copy account numbers ─────────
  $$('[data-copy]').forEach((btn) => {
    const label = btn.querySelector('span') || btn // keep any icon inside the button
    const original = label.textContent
    btn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(btn.dataset.copy)
        label.textContent = 'Copied ✓'
        setTimeout(() => (label.textContent = original), 1800)
      } catch {
        /* clipboard blocked — the text is still visible */
      }
    })
  })

  // ───────── Confirm before destructive actions; no double submits ─────────
  $$('[data-confirm]').forEach((btn) =>
    btn.addEventListener('click', (e) => {
      if (!confirm(btn.dataset.confirm)) e.preventDefault()
    }),
  )
  $$('form').forEach((form) =>
    form.addEventListener('submit', (e) => {
      if (form.dataset.submitting) return e.preventDefault()
      form.dataset.submitting = '1'
      const btn = e.submitter
      if (btn?.dataset.busy) btn.textContent = btn.dataset.busy
      // Allow a retry if the browser comes back to this page (e.g. the back button).
      addEventListener('pageshow', () => delete form.dataset.submitting, { once: true })
    }),
  )

  // ───────── Order form: delivery/pickup, quantity, live total ─────────
  const order = $('[data-order-form]')
  if (order) {
    const prices = { delivery: +order.dataset.priceDelivery, pickup: +order.dataset.pricePickup }
    const qty = $('input[name=quantity]', order)
    const naira = (n) => '₦' + n.toLocaleString('en-NG')
    const update = () => {
      const how = $('input[name=fulfilment]:checked', order)?.value || 'delivery'
      const n = Math.min(20, Math.max(1, parseInt(qty.value, 10) || 1))
      $$('.choice__card', order).forEach((c) => c.classList.toggle('is-on', $('input', c).checked))
      $$('[data-delivery-only]', order).forEach((el) => {
        el.hidden = how !== 'delivery'
        const input = $('input[name=address]', el)
        if (input) input.required = how === 'delivery'
      })
      $('[data-total-line]', order).textContent = `${n} × ${naira(prices[how])}`
      $('[data-total-note]', order).textContent = how === 'delivery' ? 'Lagos delivery included' : 'Pickup at the store'
      $('[data-total]', order).textContent = naira(prices[how] * n)
      $$('[data-qty]', order).forEach((b) => (b.disabled = (b.dataset.qty < 0 && n <= 1) || (b.dataset.qty > 0 && n >= 20)))
    }
    $$('[data-qty]', order).forEach((b) =>
      b.addEventListener('click', () => {
        qty.value = Math.min(20, Math.max(1, (parseInt(qty.value, 10) || 1) + +b.dataset.qty))
        update()
      }),
    )
    order.addEventListener('change', update)
    qty.addEventListener('input', update)
    update()
  }
})()
