// Single place for things the author will change before launch.
export const BOOK = {
  title: 'Beautiful Nothing',
  author: 'Oladimeji Ramon',
}

export const PRICES = {
  ebook: 5000,
  paperback: 12000, // includes delivery to the buyer's door
}

// Selah link isn't live yet. Leave empty and the button shows a "coming soon" note
// (clicks are still counted, so we can measure interest before launch).
export const SELAH_URL = ''

export const naira = (n) => `₦${n.toLocaleString('en-NG')}`
