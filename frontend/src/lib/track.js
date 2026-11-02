const API = import.meta.env.VITE_API_URL ?? ''

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

// Fire-and-forget. Sent as text/plain so cross-origin beacons need no CORS preflight;
// the backend parses the body as JSON. Tracking must never break the page.
export function track(type) {
  try {
    const body = JSON.stringify({
      type,
      visitor_id: visitorId(),
      path: location.pathname,
      referrer: document.referrer || null,
    })
    const url = `${API}/api/events`
    const blob = new Blob([body], { type: 'text/plain' })
    if (navigator.sendBeacon?.(url, blob)) return
    fetch(url, { method: 'POST', body, keepalive: true }).catch(() => {})
  } catch {
    /* ignore */
  }
}
