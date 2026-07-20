import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useTranslation } from '../i18n/I18nContext.jsx'

function scriptIcon(name) {
  if (name.endsWith('.py')) return '🐍'
  if (name.endsWith('.sh')) return '🐚'
  return '📄'
}

export default function CommandPalette() {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [results, setResults] = useState([])
  const [activeIndex, setActiveIndex] = useState(0)
  const inputRef = useRef(null)
  const navigate = useNavigate()
  const { t } = useTranslation()

  useEffect(() => {
    function onKeyDown(e) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setOpen((v) => !v)
      } else if (e.key === 'Escape' && open) {
        setOpen(false)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open])

  useEffect(() => {
    if (open) {
      setQ('')
      setResults([])
      setActiveIndex(0)
      setTimeout(() => inputRef.current?.focus(), 0)
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    const timeout = setTimeout(() => {
      api
        .listScripts({ q: q || undefined })
        .then((r) => {
          setResults(r.scripts.slice(0, 12))
          setActiveIndex(0)
        })
        .catch(() => setResults([]))
    }, 150)
    return () => clearTimeout(timeout)
  }, [q, open])

  function goTo(scriptId) {
    setOpen(false)
    navigate(`/scripts/${scriptId}`)
  }

  function onKeyDown(e) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex((i) => Math.min(i + 1, results.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && results[activeIndex]) {
      goTo(results[activeIndex].id)
    }
  }

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 pt-24"
      onClick={() => setOpen(false)}
    >
      <div
        className="w-full max-w-lg rounded-lg border border-border-strong bg-panel shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          ref={inputRef}
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={t('commandPalette.placeholder')}
          className="w-full rounded-t-lg border-b border-border bg-panel px-4 py-3 text-sm text-text-primary outline-none"
        />
        {results.length > 0 && (
          <div className="max-h-80 overflow-y-auto py-1">
            {results.map((s, i) => (
              <button
                key={s.id}
                type="button"
                onClick={() => goTo(s.id)}
                onMouseEnter={() => setActiveIndex(i)}
                className={`flex w-full items-center gap-2 px-4 py-2 text-left text-sm ${
                  i === activeIndex ? 'bg-fjord text-text-primary' : 'text-text-secondary'
                }`}
              >
                <span>{scriptIcon(s.name)}</span>
                <span className="font-medium">{s.name}</span>
                <span className="truncate text-xs text-text-tertiary">
                  {s.short_description}
                </span>
              </button>
            ))}
          </div>
        )}
        {q && results.length === 0 && (
          <p className="px-4 py-3 text-sm text-text-tertiary">{t('commandPalette.noResults')}</p>
        )}
      </div>
    </div>
  )
}
