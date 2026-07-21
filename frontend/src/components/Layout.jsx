import { Link, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import CommandPalette from './CommandPalette'
import LanguageToggle from './LanguageToggle'
import { useTranslation } from '../i18n/I18nContext.jsx'

export default function Layout({ children }) {
  const navigate = useNavigate()
  const { t } = useTranslation()

  async function handleLogout() {
    await api.logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-ink text-text-primary">
      <header className="border-b border-border bg-panel">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-3 sm:px-6 sm:py-4">
          <Link to="/" className="flex shrink-0 items-center gap-2">
            <span className="text-lg font-semibold tracking-tight text-text-primary">
              sin<span className="text-gold">dri</span>
            </span>
          </Link>
          <nav className="flex flex-wrap items-center gap-x-3 gap-y-2 text-sm sm:gap-x-4">
            <Link to="/" className="text-text-secondary hover:text-text-primary">
              {t('layout.catalog')}
            </Link>
            <Link to="/tags" className="text-text-secondary hover:text-text-primary">
              {t('layout.tags')}
            </Link>
            <Link to="/settings" className="text-text-secondary hover:text-text-primary">
              {t('layout.settings')}
            </Link>
            <span
              title={t('layout.quickSearchHint')}
              className="hidden rounded border border-border-strong px-1.5 py-0.5 text-[10px] text-text-tertiary sm:inline"
            >
              Ctrl+K
            </span>
            <LanguageToggle />
            <Link
              to="/add"
              className="rounded bg-blue px-3 py-1.5 font-medium text-white hover:bg-blue-light"
            >
              {t('layout.addScript')}
            </Link>
            <button
              type="button"
              onClick={handleLogout}
              className="text-text-tertiary hover:text-text-secondary"
            >
              {t('layout.logout')}
            </button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
      <CommandPalette />
    </div>
  )
}
