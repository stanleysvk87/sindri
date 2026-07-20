import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useTranslation } from '../i18n/I18nContext.jsx'
import LanguageToggle from '../components/LanguageToggle'

export default function Login() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { t } = useTranslation()

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.login(password)
      navigate('/')
    } catch (err) {
      setError(err.status === 429 ? err.message : t('login.wrongPassword'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-lg border border-border bg-panel p-8"
      >
        <div className="mb-1 flex items-center justify-between">
          <h1 className="text-xl font-semibold text-text-primary">
            sin<span className="text-gold">dri</span>
          </h1>
          <LanguageToggle />
        </div>
        <p className="mb-6 text-sm text-text-secondary">{t('login.subtitle')}</p>
        <label className="mb-1 block text-sm text-text-secondary" htmlFor="password">
          {t('login.passwordLabel')}
        </label>
        <input
          id="password"
          type="password"
          autoFocus
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mb-4 w-full rounded border border-border-strong bg-ink px-3 py-2 text-text-primary outline-none focus:border-blue"
        />
        {error && <p className="mb-4 text-sm text-warning">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-blue px-3 py-2 font-medium text-white hover:bg-blue-light disabled:opacity-50"
        >
          {loading ? t('login.loggingIn') : t('login.loginButton')}
        </button>
      </form>
    </div>
  )
}
