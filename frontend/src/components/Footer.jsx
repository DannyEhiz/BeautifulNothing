export default function Footer() {
  return (
    <footer className="footer board">
      <div className="wrap footer__inner">
        <p className="footer__brand">Beautiful Nothing</p>
        <p className="footer__line">Stories by Oladimeji Ramon</p>
        <nav className="footer__links" aria-label="Footer">
          <a href="/#book">The book</a>
          <a href="/#stories">The stories</a>
          <a href="/#author">The author</a>
          <a href="/#get">Get the book</a>
        </nav>
        <p className="footer__copy">© {new Date().getFullYear()} Oladimeji Ramon. All rights reserved.</p>
      </div>
    </footer>
  )
}
