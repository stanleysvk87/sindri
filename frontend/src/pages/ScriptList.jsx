import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'

export default function ScriptList() {
  const [scripts, setScripts] = useState([])
  const [hosts, setHosts] = useState([])
  const [allTags, setAllTags] = useState([])
  const [host, setHost] = useState('')
  const [selectedTags, setSelectedTags] = useState(() => new Set())
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.hosts().then((r) => setHosts(r.hosts)).catch(() => {})
    api.tags().then((r) => setAllTags(r.tags)).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    const timeout = setTimeout(() => {
      api
        .listScripts({ host: host || undefined, tags: [...selectedTags], q: q || undefined })
        .then((r) => setScripts(r.scripts))
        .catch(() => setError('Nepodarilo sa načítať zoznam.'))
        .finally(() => setLoading(false))
    }, 200) // debounce fulltext hľadania
    return () => clearTimeout(timeout)
  }, [host, selectedTags, q])

  function toggleTag(tag) {
    setSelectedTags((prev) => {
      const next = new Set(prev)
      next.has(tag) ? next.delete(tag) : next.add(tag)
      return next
    })
  }

  return (
    <div>
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
        <input
          type="text"
          placeholder="Hľadaj podľa mena, popisu, poznámok alebo obsahu..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="flex-1 rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <select
          value={host}
          onChange={(e) => setHost(e.target.value)}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        >
          <option value="">Všetky stroje</option>
          {hosts.map((h) => (
            <option key={h} value={h}>
              {h}
            </option>
          ))}
        </select>
      </div>

      {allTags.length > 0 && (
        <div className="mb-6 flex flex-wrap gap-1.5">
          {allTags.map((t) => {
            const active = selectedTags.has(t)
            return (
              <button
                key={t}
                type="button"
                onClick={() => toggleTag(t)}
                className={`rounded-full border px-2.5 py-1 text-xs transition ${
                  active
                    ? 'border-blue bg-blue text-white'
                    : 'border-border-strong bg-panel text-text-secondary hover:border-blue hover:text-text-primary'
                }`}
              >
                #{t}
              </button>
            )
          })}
          {selectedTags.size > 0 && (
            <button
              type="button"
              onClick={() => setSelectedTags(new Set())}
              className="rounded-full px-2.5 py-1 text-xs text-text-tertiary hover:text-warning"
            >
              zrušiť filter ×
            </button>
          )}
        </div>
      )}

      {error && <p className="text-warning">{error}</p>}
      {!loading && scripts.length === 0 && (
        <p className="text-text-tertiary">Žiadne skripty nenájdené.</p>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {scripts.map((s) => (
          <Link
            key={s.id}
            to={`/scripts/${s.id}`}
            className="rounded-lg border border-border bg-panel p-4 transition hover:border-blue"
          >
            <div className="mb-1 flex items-center justify-between gap-2">
              <span className="font-medium text-text-primary">{s.name}</span>
              {s.has_possible_secret && (
                <span
                  title="Obsah možno obsahuje heslo/token"
                  className="rounded border border-warning/40 bg-warning/10 px-1.5 py-0.5 text-[10px] uppercase text-warning"
                >
                  secret?
                </span>
              )}
            </div>
            <p className="mb-2 text-sm text-text-secondary">
              {s.short_description || <em className="text-text-tertiary">bez popisu</em>}
            </p>
            <div className="flex flex-wrap gap-1.5 text-xs text-text-tertiary">
              {s.host && (
                <span className="rounded bg-fjord px-1.5 py-0.5 text-blue-light">{s.host}</span>
              )}
              {s.run_mode && <span className="rounded bg-fjord px-1.5 py-0.5">{s.run_mode}</span>}
              {s.tags
                .split(',')
                .map((t) => t.trim())
                .filter(Boolean)
                .map((t) => (
                  <span
                    key={t}
                    role="button"
                    onClick={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      toggleTag(t)
                    }}
                    className="rounded bg-fjord px-1.5 py-0.5 hover:text-blue-light"
                  >
                    #{t}
                  </span>
                ))}
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
