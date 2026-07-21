import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { getRecentIds } from '../lib/recent'
import { useTranslation } from '../i18n/I18nContext.jsx'

function scriptIcon(name) {
  if (name.endsWith('.py')) return '🐍'
  if (name.endsWith('.sh')) return '🐚'
  return '📄'
}

export default function ScriptList() {
  const { t } = useTranslation()
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
  const [everywhereOnly, setEverywhereOnly] = useState(false)
  const [secretOnly, setSecretOnly] = useState(false)
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
        .listScripts({ host: host || undefined, tags: [...selectedTags], q: q || undefined, favorite: favoriteOnly, everywhere: everywhereOnly, secret: secretOnly })
        .then((r) => {
          setScripts(r.scripts)
          setVisibleCount(PAGE_SIZE) // nový filter/hľadanie -- začni znova od prvej strany
        })
        .catch(() => setError(t('scriptList.loadFailed')))
        .finally(() => setLoading(false))
    }, 200) // debounce fulltext hľadania
    return () => clearTimeout(timeout)
  }, [host, selectedTags, q, favoriteOnly, everywhereOnly, secretOnly])

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
      setBulkMessage(t('scriptList.bulkTagUpdated', { count: result.updated }))
      setBulkAddTag('')
      setBulkRemoveTag('')
      const r = await api.listScripts({ host: host || undefined, tags: [...selectedTags], q: q || undefined, favorite: favoriteOnly })
      setScripts(r.scripts)
      api.tags().then((rr) => setAllTags(rr.tags)).catch(() => {})
    } catch (err) {
      setBulkMessage(err.message || t('scriptList.bulkTagFailed'))
    } finally {
      setBulkApplying(false)
    }
  }

  // Referenčné katalógy (host=cheatsheet/pentest) majú desiatky záznamov
  // rozdelených do kategórií cez druhý tag (napr. "cheatsheet,docker,claude"
  // -> kategória "docker"). Zoskupenie sa aplikuje len keď prehliadaš celý
  // zoznam bez ďalšieho filtra (tag click / hľadanie), aby sa to nebilo s
  // existujúcim tag-filter mechanizmom.
  const CATALOG_HOSTS = ['cheatsheet', 'pentest']
  const groupedView = CATALOG_HOSTS.includes(host) && selectedTags.size === 0 && !q
  const categoryGroups = groupedView
    ? Object.entries(
        scripts.reduce((acc, s) => {
          const parts = (s.tags || '').split(',').map((x) => x.trim()).filter(Boolean)
          const category = parts[1] || t('scriptList.uncategorized')
          ;(acc[category] ||= []).push(s)
          return acc
        }, {})
      ).sort(([a], [b]) => a.localeCompare(b))
    : []

  // Tag cloud obmedzený na tagy, ktoré sa reálne vyskytujú pri aktuálne
  // vybranom stroji -- inak sa dá kliknúť na tag ako #wifi vo výbere
  // host=cheatsheet a dostať prázdny výsledok. allScriptsForRecent má vždy
  // celý katalóg (backend list_scripts nič nestránkuje), takže sa dá počítať
  // bez ďalšieho API volania. Bez vybraného stroja sa ukazuje plný zoznam.
  const visibleTags = host
    ? [...new Set(
        allScriptsForRecent
          .filter((s) => s.host === host)
          .flatMap((s) => (s.tags || '').split(',').map((x) => x.trim()).filter(Boolean))
      )].sort()
    : allTags

  function renderCard(s) {
    const CardWrapper = selectMode ? 'div' : Link
    const wrapperProps = selectMode
      ? { onClick: () => toggleSelected(s.id), role: 'button' }
      : { to: `/scripts/${s.id}` }
    const isReference = CATALOG_HOSTS.includes(s.host)
    return (
      <CardWrapper
        key={s.id}
        {...wrapperProps}
        className={`min-w-0 rounded-lg border p-4 transition ${isReference ? 'border-l-2 border-l-gold' : ''} ${
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
            <span title={isReference ? t('scriptList.typeReference') : s.name.endsWith('.py') ? t('scriptList.typePython') : s.name.endsWith('.sh') ? t('scriptList.typeShell') : t('scriptList.typeScript')}>
              {isReference ? '📖' : scriptIcon(s.name)}
            </span>
            <span className="min-w-0 break-words">{s.name}</span>
          </span>
          <div className="flex items-center gap-2">
            {s.has_possible_secret && (
              <span
                title={t('scriptList.secretBadgeTitle')}
                className="rounded border border-warning/40 bg-warning/10 px-1.5 py-0.5 text-[10px] uppercase text-warning"
              >
                {t('scriptList.secretBadge')}
              </span>
            )}
            <button
              type="button"
              onClick={(e) => handleToggleFavorite(e, s.id)}
              title={s.is_favorite ? t('scriptList.removeFavorite') : t('scriptList.addFavorite')}
              className={`text-sm ${s.is_favorite ? 'text-warning' : 'text-text-tertiary hover:text-warning'}`}
            >
              {s.is_favorite ? '★' : '☆'}
            </button>
          </div>
        </div>
        <p className="mb-2 text-sm text-text-secondary">
          {s.short_description || <em className="text-text-tertiary">{t('scriptList.noDescription')}</em>}
        </p>
        <div className="flex flex-wrap gap-1.5 text-xs text-text-tertiary">
          {s.host && <span className="rounded bg-fjord px-1.5 py-0.5 text-blue-light">{s.host}</span>}
          {s.works_everywhere ? (
            <span title={t('scriptList.everywhereBadgeTitle')} className="rounded bg-fjord px-1.5 py-0.5 text-success">
              {t('scriptList.everywhereBadge')}
            </span>
          ) : null}
          {s.run_mode && <span className="rounded bg-fjord px-1.5 py-0.5">{s.run_mode}</span>}
          {s.tags
            .split(',')
            .map((tg) => tg.trim())
            .filter(Boolean)
            .map((tg) => (
              <span
                key={tg}
                role="button"
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  toggleTag(tg)
                }}
                className="rounded bg-fjord px-1.5 py-0.5 hover:text-blue-light"
              >
                #{tg}
              </span>
            ))}
        </div>
      </CardWrapper>
    )
  }

  return (
    <div>
      <div className="mb-4 flex flex-col flex-wrap gap-3 sm:flex-row sm:items-center">
        <input
          type="text"
          placeholder={t('scriptList.searchPlaceholder')}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="flex-1 rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <select
          value={host}
          onChange={(e) => setHost(e.target.value)}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        >
          <option value="">{t('scriptList.allMachines')}</option>
          {[...hosts]
            .sort((a, b) => (a.toLowerCase() < b.toLowerCase() ? -1 : a.toLowerCase() > b.toLowerCase() ? 1 : 0))
            .map((h) => (
            <option key={h} value={h}>
              {h}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={() => setFavoriteOnly((v) => !v)}
          title={t('scriptList.favoritesOnlyTitle')}
          className={`rounded border px-3 py-2 text-sm ${
            favoriteOnly
              ? 'border-blue bg-blue text-white'
              : 'border-border-strong bg-panel text-text-secondary hover:border-blue hover:text-text-primary'
          }`}
        >
          {t('scriptList.favoritesOnly')}
        </button>
        <button
          type="button"
          onClick={() => setEverywhereOnly((v) => !v)}
          title={t('scriptList.everywhereOnlyTitle')}
          className={`rounded border px-3 py-2 text-sm ${
            everywhereOnly
              ? 'border-blue bg-blue text-white'
              : 'border-border-strong bg-panel text-text-secondary hover:border-blue hover:text-text-primary'
          }`}
        >
          {t('scriptList.everywhereOnly')}
        </button>
        <button
          type="button"
          onClick={() => setSecretOnly((v) => !v)}
          title={t('scriptList.secretOnlyTitle')}
          className={`rounded border px-3 py-2 text-sm ${
            secretOnly
              ? 'border-blue bg-blue text-white'
              : 'border-border-strong bg-panel text-text-secondary hover:border-blue hover:text-text-primary'
          }`}
        >
          {t('scriptList.secretOnly')}
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
          {selectMode ? t('scriptList.cancelSelection') : t('scriptList.bulkEdit')}
        </button>
      </div>

      {selectMode && (
        <div className="mb-6 flex flex-wrap items-center gap-2 rounded-lg border border-border bg-panel p-3">
          <span className="text-xs text-text-secondary">
            {selectedIds.size === 0 ? t('scriptList.selectHint') : t('scriptList.selectedCount', { count: selectedIds.size })}
          </span>
          <input
            type="text"
            placeholder={t('scriptList.addTagPlaceholder')}
            value={bulkAddTag}
            onChange={(e) => setBulkAddTag(e.target.value)}
            disabled={selectedIds.size === 0}
            className="w-28 rounded border border-border-strong bg-bg px-2 py-1 text-xs text-text-primary outline-none focus:border-blue disabled:opacity-50"
          />
          <input
            type="text"
            placeholder={t('scriptList.removeTagPlaceholder')}
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
            {bulkApplying ? t('scriptList.applying') : t('scriptList.apply')}
          </button>
          {bulkMessage && <span className="text-xs text-text-tertiary">{bulkMessage}</span>}
        </div>
      )}

      {!selectMode && !q && recentScripts.length > 0 && (
        <div className="mb-4">
          <h3 className="mb-1.5 text-xs uppercase tracking-wide text-text-tertiary">{t('scriptList.recentlyOpened')}</h3>
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

      {visibleTags.length > 0 && (
        <div className="mb-6 flex flex-wrap gap-1.5">
          {visibleTags.map((t) => {
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
              {t('scriptList.clearFilter')}
            </button>
          )}
        </div>
      )}

      {error && <p className="text-warning">{error}</p>}
      {!loading && scripts.length === 0 && (
        <p className="text-text-tertiary">{t('scriptList.noScriptsFound')}</p>
      )}
      {scripts.length > 0 && (
        <p className="mb-3 text-xs text-text-tertiary">
          {groupedView
            ? t('scriptList.showingGroupedCount', { total: scripts.length, groups: categoryGroups.length })
            : t('scriptList.showingCount', { shown: Math.min(visibleCount, scripts.length), total: scripts.length })}
        </p>
      )}

      {groupedView ? (
        <div className="flex flex-col gap-2">
          {categoryGroups.map(([category, items]) => (
            <details key={category} className="rounded-lg border border-border bg-panel" open={categoryGroups.length <= 1}>
              <summary className="cursor-pointer select-none px-4 py-3 text-sm font-medium text-text-primary hover:text-blue-light">
                #{category} <span className="font-normal text-text-tertiary">({items.length})</span>
              </summary>
              <div className="grid gap-3 border-t border-border p-4 sm:grid-cols-2">
                {items.map((s) => renderCard(s))}
              </div>
            </details>
          ))}
        </div>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2">{scripts.slice(0, visibleCount).map((s) => renderCard(s))}</div>

          {visibleCount < scripts.length && (
            <button
              type="button"
              onClick={() => setVisibleCount((v) => v + PAGE_SIZE)}
              className="mt-4 w-full rounded border border-border-strong py-2 text-sm text-text-secondary hover:border-blue hover:text-text-primary"
            >
              {t('scriptList.showMore', { count: Math.min(PAGE_SIZE, scripts.length - visibleCount) })}
            </button>
          )}
        </>
      )}
    </div>
  )
}
