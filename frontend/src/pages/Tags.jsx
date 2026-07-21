import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { useTranslation } from '../i18n/I18nContext.jsx'

export default function Tags() {
  const { t } = useTranslation()
  const [tags, setTags] = useState([])
  const [counts, setCounts] = useState({})
  const [renaming, setRenaming] = useState(null)
  const [renameValue, setRenameValue] = useState('')
  const [busy, setBusy] = useState(false)
  const [q, setQ] = useState('')
  const [justRenamed, setJustRenamed] = useState(null)

  function reload() {
    api.tags().then((r) => setTags(r.tags)).catch(() => {})
    // Počet skriptov na tag -- potrebné na to, aby premenovanie/mazanie
    // nebolo "čierna skrinka": user má vidieť koľko záznamov sa tým reálne
    // dotkne skôr, než to potvrdí (rename/delete je vždy naprieč CELÝM
    // katalógom, nie len jedným zobrazeným riadkom).
    api
      .listScripts({})
      .then((r) => {
        const next = {}
        for (const s of r.scripts) {
          for (const tag of (s.tags || '').split(',').map((x) => x.trim()).filter(Boolean)) {
            next[tag] = (next[tag] || 0) + 1
          }
        }
        setCounts(next)
      })
      .catch(() => {})
  }

  useEffect(reload, [])

  async function handleRename(tag) {
    const next = renameValue.trim()
    if (!next || next === tag) {
      setRenaming(null)
      return
    }
    const count = counts[tag] || 0
    if (!confirm(t('settings.tags.confirmRename', { tag, next, count }))) return
    setBusy(true)
    try {
      await api.renameTag(tag, next)
      setRenaming(null)
      setJustRenamed(next)
      reload()
      setTimeout(() => setJustRenamed(null), 2500)
    } finally {
      setBusy(false)
    }
  }

  async function handleDelete(tag) {
    const count = counts[tag] || 0
    if (!confirm(t('settings.tags.confirmDelete', { tag, count }))) return
    setBusy(true)
    try {
      await api.deleteTag(tag)
      reload()
    } finally {
      setBusy(false)
    }
  }

  const visibleTags = q ? tags.filter((tag) => tag.toLowerCase().includes(q.toLowerCase())) : tags

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-text-primary">
          {t('settings.tags.title')} <span className="font-normal text-text-tertiary">({tags.length})</span>
        </h1>
        <input
          type="text"
          placeholder={t('tagsPage.searchPlaceholder')}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="w-full rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue sm:w-64"
        />
      </div>
      <p className="mb-4 text-xs text-text-tertiary">{t('settings.tags.renameHint')}</p>
      <div className="divide-y divide-border rounded-lg border border-border bg-panel">
        {visibleTags.length === 0 && (
          <p className="p-4 text-sm text-text-tertiary">{q ? t('tagsPage.noMatch') : t('settings.tags.none')}</p>
        )}
        {visibleTags.map((tag) => (
          <div key={tag} className="flex items-center justify-between gap-2 p-3 text-sm">
            {renaming === tag ? (
              <input
                autoFocus
                value={renameValue}
                onChange={(e) => setRenameValue(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleRename(tag)}
                className="rounded border border-border-strong bg-ink px-2 py-1 text-sm text-text-primary outline-none focus:border-blue"
              />
            ) : (
              <span className="text-text-primary">
                #{tag} <span className="text-text-tertiary">({counts[tag] || 0})</span>
                {justRenamed === tag && <span className="ml-2 text-xs text-success">{t('settings.tags.renamed')}</span>}
              </span>
            )}
            <div className="flex gap-3 text-xs">
              {renaming === tag ? (
                <>
                  <button type="button" disabled={busy} onClick={() => handleRename(tag)} className="text-blue-light hover:underline">
                    {t('common.save')}
                  </button>
                  <button type="button" onClick={() => setRenaming(null)} className="text-text-tertiary hover:underline">
                    {t('common.cancel')}
                  </button>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      setRenaming(tag)
                      setRenameValue(tag)
                    }}
                    className="text-blue-light hover:underline"
                  >
                    {t('scriptDetail.editField')}
                  </button>
                  <button type="button" disabled={busy} onClick={() => handleDelete(tag)} className="text-warning hover:underline">
                    {t('settings.tags.delete')}
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
