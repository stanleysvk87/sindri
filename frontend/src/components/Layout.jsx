import { Link, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

export default function Layout({ children }) {
  const navigate = useNavigate()

  async function handleLogout() {
    await api.logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-ink text-text-primary">
      <header className="border-b border-border bg-panel">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link to="/" className="flex items-center gap-2">
            <span className="text-lg font-semibold tracking-tight text-text-primary">
              sin<span className="text-gold">dri</span>
            </span>
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            <Link to="/" className="text-text-secondary hover:text-text-primary">
              Katalóg
            </Link>
            <Link
              to="/add"
              className="rounded bg-blue px-3 py-1.5 font-medium text-white hover:bg-blue-light"
            >
              + Pridať skript
            </Link>
            <button
              type="button"
              onClick={handleLogout}
              className="text-text-tertiary hover:text-text-secondary"
            >
              Odhlásiť
            </button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
    </div>
  )
}
