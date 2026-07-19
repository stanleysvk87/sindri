import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

export default function Login() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.login(password)
      navigate('/')
    } catch {
      setError('Nesprávne heslo.')
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
        <h1 className="mb-1 text-xl font-semibold text-text-primary">
          sin<span className="text-gold">dri</span>
        </h1>
        <p className="mb-6 text-sm text-text-secondary">Katalóg skriptov</p>
        <label className="mb-1 block text-sm text-text-secondary" htmlFor="password">
          Heslo
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
          {loading ? 'Prihlasujem...' : 'Prihlásiť'}
        </button>
      </form>
    </div>
  )
}
