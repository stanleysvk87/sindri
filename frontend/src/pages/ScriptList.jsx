import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { getRecentIds } from '../lib/recent'

function scriptIcon(name) {
  if (name.endsWith('.py')) return '🐍'
  if (name.endsWith('.sh')) return '🐚'
  return '📄'
}

export default function ScriptList() {
  const [scripts, setScripts] = useState([])
  const [hosts, setHosts] = useState([])
  const [allTags, setAllTags] = useState([])
  const [host, setHost] = useState('')
  const [selectedTags, setSelectedTags] = useState(() => new Set())
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [visibleCount, setVisibleCount] = useState(40)
  const PAGE_SIZE = 40
  const [selectMode, setSelectMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState(() => new Set())
  const [bulkAddTag, setBulkAddTag] = useState('')
  const [bulkRemoveTag, setBulkRemoveTag] = useState('')
  const [bulkApplying, setBulkApplying] = useState(false)
  const [bulkMessage, setBulkMessage] = useState('')
  const [favoriteOnly, setFavoriteOnly] = useState(false)
  const [allScriptsForRecent, setAllScriptsForRecent] = useState([])

  useEffect(() => {
    api.hosts().then((r) => setHosts(r.hosts)).catch(() => {})
    api.tags().then((r) => setAllTags(r.tags)).catch(() => {})
    api.listScripts({}).then((r) => setAllScriptsForRecent(r.scripts)).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    const timeout = setTimeout(() => {
      api
        .listScripts({ host: host || undefined, tags: [...selectedTags], q: q || undefined, favorite: favoriteOnly })
        .then((r) => {
          setScripts(r.scripts)
          setVisibleCount(PAGE_SIZE) // nový filter/hľadanie -- začni znova od prvej strany
        })
        .catch(() => setError('Nepodarilo sa načítať zoznam.'))
        .finally(() => setLoading(false))
    }, 200) // debounce fulltext hľadania
    return () => clearTimeout(timeout)
  }, [host, selectedTags, q, favoriteOnly])

  async function handleToggleFavorite(e, scriptId) {
    e.preventDefault()
    e.stopPropagation()
    const result = await api.toggleFavorite(scriptId)
    setScripts((prev) => prev.map((s) => (s.id === scriptId ? { ...s, is_favorite: result.is_favorite } : s)))
  }

  const recentScripts = getRecentIds()
    .map((id) => allScriptsForRecent.find((s) => s.id === id))
    .filter(Boolean)

  function toggleTag(tag) {
    setSelectedTags((prev) => {
      const next = new Set(prev)
      next.has(tag) ? next.delete(tag) : next.add(tag)
      return next
    })
  }

  function toggleSelected(id) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function exitSelectMode() {
    setSelectMode(false)
    setSelectedIds(new Set())
    setBulkAddTag('')
    setBulkRemoveTag('')
    setBulkMessage('')
  }

  async function handleBulkApply() {
    if (!bulkAddTag.trim() && !bulkRemoveTag.trim()) return
    setBulkApplying(true)
    setBulkMessage('')
    try {
      const result = await api.bulkTag([...selectedIds], bulkAddTag.trim(), bulkRemoveTag.trim())
      setBulkMessage(`Upravené tagy pri ${result.updated} skriptoch.`)
      setBulkAddTag('')
      setBulkRemoveTag('')
      const r = await api.listScripts({ host: host || undefined, tags: [...selectedTags], q: q || undefined, favorite: favoriteOnly })
      setScripts(r.scripts)
      api.tags().then((rr) => setAllTags(rr.tags)).catch(() => {})
    } catch (err) {
      setBulkMessage(err.message || 'Hromadná úprava zlyhala.')
    } finally {
      setBulkApplying(false)
    }
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
        <button
          type="button"
          onClick={() => setFavoriteOnly((v) => !v)}
          title="Zobraziť len obľúbené skripty"
          className={`rounded border px-3 py-2 text-sm ${
            favoriteOnly
              ? 'border-blue bg-blue text-white'
              : 'border-border-strong bg-panel text-text-secondary hover:border-blue hover:text-text-primary'
          }`}
        >
          ★ Obľúbené
        </button>
        <button
          type="button"
          onClick={() => (selectMode ? exitSelectMode() : setSelectMode(true))}
          className={`rounded border px-3 py-2 text-sm ${
            selectMode
              ? 'border-blue bg-blue text-white'
              : 'border-border-strong bg-panel text-text-secondary hover:border-blue hover:text-text-primary'
          }`}
        >
          {selectMode ? 'Zrušiť výber' : 'Hromadné úpravy tagov'}
        </button>
      </div>

      {selectMode && (
        <div className="mb-6 flex flex-wrap items-center gap-2 rounded-lg border border-border bg-panel p-3">
          <span className="text-xs text-text-secondary">
            {selectedIds.size === 0 ? 'Vyber skripty nižšie kliknutím...' : `Vybraných: ${selectedIds.size}`}
          </span>
          <input
            type="text"
            placeholder="pridať tag"
            value={bulkAddTag}
            onChange={(e) => setBulkAddTag(e.target.value)}
            disabled={selectedIds.size === 0}
            className="w-28 rounded border border-border-strong bg-bg px-2 py-1 text-xs text-text-primary outline-none focus:border-blue disabled:opacity-50"
          />
          <input
            type="text"
            placeholder="odstrániť tag"
            value={bulkRemoveTag}
            onChange={(e) => setBulkRemoveTag(e.target.value)}
            disabled={selectedIds.size === 0}
            className="w-28 rounded border border-border-strong bg-bg px-2 py-1 text-xs text-text-primary outline-none focus:border-blue disabled:opacity-50"
          />
          <button
            type="button"
            onClick={handleBulkApply}
            disabled={selectedIds.size === 0 || bulkApplying || (!bulkAddTag.trim() && !bulkRemoveTag.trim())}
            className="rounded bg-blue px-3 py-1 text-xs font-medium text-white hover:bg-blue-light disabled:opacity-50"
          >
            {bulkApplying ? 'Ukladám...' : 'Použiť'}
          </button>
          {bulkMessage && <span className="text-xs text-text-tertiary">{bulkMessage}</span>}
        </div>
      )}

      {!selectMode && !q && recentScripts.length > 0 && (
        <div className="mb-4">
          <h3 className="mb-1.5 text-xs uppercase tracking-wide text-text-tertiary">Naposledy otvorené</h3>
          <div className="flex flex-wrap gap-1.5">
            {recentScripts.map((s) => (
              <Link
                key={s.id}
                to={`/scripts/${s.id}`}
                className="rounded border border-border-strong bg-panel px-2 py-1 text-xs text-text-secondary hover:border-blue hover:text-text-primary"
              >
                {scriptIcon(s.name)} {s.name}
              </Link>
            ))}
          </div>
        </div>
      )}

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
      {scripts.length > 0 && (
        <p className="mb-3 text-xs text-text-tertiary">
          {Math.min(visibleCount, scripts.length)} z {scripts.length}
        </p>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {scripts.slice(0, visibleCount).map((s) => {
          const CardWrapper = selectMode ? 'div' : Link
          const wrapperProps = selectMode
            ? { onClick: () => toggleSelected(s.id), role: 'button' }
            : { to: `/scripts/${s.id}` }
          return (
          <CardWrapper
            key={s.id}
            {...wrapperProps}
            className={`min-w-0 rounded-lg border p-4 transition ${
              selectMode && selectedIds.has(s.id)
                ? 'cursor-pointer border-blue bg-fjord'
                : selectMode
                  ? 'cursor-pointer border-border bg-panel hover:border-blue'
                  : 'border-border bg-panel hover:border-blue'
            }`}
          >
            <div className="mb-1 flex items-center justify-between gap-2">
              <span className="flex min-w-0 items-center gap-2 font-medium text-text-primary">
                {selectMode && (
                  <input
                    type="checkbox"
                    checked={selectedIds.has(s.id)}
                    onChange={() => toggleSelected(s.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="h-3.5 w-3.5"
                  />
                )}
                <span title={s.name.endsWith('.py') ? 'Python' : s.name.endsWith('.sh') ? 'Shell' : 'Skript'}>
                  {scriptIcon(s.name)}
                </span>
                <span className="min-w-0 break-words">{s.name}</span>
              </span>
              <div className="flex items-center gap-2">
                {s.has_possible_secret && (
                  <span
                    title="Obsah možno obsahuje heslo/token"
                    className="rounded border border-warning/40 bg-warning/10 px-1.5 py-0.5 text-[10px] uppercase text-warning"
                  >
                    secret?
                  </span>
                )}
                <button
                  type="button"
                  onClick={(e) => handleToggleFavorite(e, s.id)}
                  title={s.is_favorite ? 'Odobrať z obľúbených' : 'Pridať medzi obľúbené'}
                  className={`text-sm ${s.is_favorite ? 'text-warning' : 'text-text-tertiary hover:text-warning'}`}
                >
                  {s.is_favorite ? '★' : '☆'}
                </button>
              </div>
            </div>
            <p className="mb-2 text-sm text-text-secondary">
              {s.short_description || <em className="text-text-tertiary">bez popisu</em>}
            </p>
            <div className="flex flex-wrap gap-1.5 text-xs text-text-tertiary">
              {s.host && (
                <span className="rounded bg-fjord px-1.5 py-0.5 text-blue-light">{s.host}</span>
              )}
              {s.works_everywhere ? (
                <span
                  title="Funguje na hocijakom stroji"
                  className="rounded bg-fjord px-1.5 py-0.5 text-success"
                >
                  ✓ všade
                </span>
              ) : null}
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
          </CardWrapper>
          )
        })}
      </div>

      {visibleCount < scripts.length && (
        <button
          type="button"
          onClick={() => setVisibleCount((v) => v + PAGE_SIZE)}
          className="mt-4 w-full rounded border border-border-strong py-2 text-sm text-text-secondary hover:border-blue hover:text-text-primary"
        >
          Zobraziť ďalších {Math.min(PAGE_SIZE, scripts.length - visibleCount)}
        </button>
      )}
    </div>
  )
}
