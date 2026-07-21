import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useTranslation } from '../i18n/I18nContext.jsx'

function AIGenerateTab() {
  const { t } = useTranslation()
  const [aiAvailable, setAiAvailable] = useState(null)
  const [description, setDescription] = useState('')
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState(null) // {name, host, tags, short_description, content}
  const [adding, setAdding] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    api.aiStatus().then((s) => setAiAvailable(s.available)).catch(() => setAiAvailable(false))
  }, [])

  async function handleGenerate(e) {
    e.preventDefault()
    if (!description.trim()) return
    setError('')
    setGenerating(true)
    try {
      const result = await api.aiGenerate(description)
      setForm({
        name: '',
        host: '',
        tags: 'ai-generated',
        short_description: description.slice(0, 120),
        content: result.content,
      })
    } catch (err) {
      setError(err.message === 'Request failed: 503'
        ? t('addScript.ai.generateUnavailable')
        : t('addScript.ai.generateFailed'))
    } finally {
      setGenerating(false)
    }
  }

  async function handleAdd(e) {
    e.preventDefault()
    if (adding) return
    if (!form.name.trim()) {
      setError(t('addScript.ai.nameRequired'))
      return
    }
    setAdding(true)
    try {
      const created = await api.importPaste({ ...form, source_ref: t('addScript.ai.sourceRefValue') })
      navigate(`/scripts/${created.id}`)
    } catch {
      setError(t('addScript.ai.addFailed'))
      setAdding(false)
    }
  }

  if (aiAvailable === false) {
    return (
      <p className="text-text-tertiary">
        {t('addScript.ai.notConfiguredPrefix')}{' '}
        <code className="text-xs">claude</code>/<code className="text-xs">codex</code>{' '}
        {t('addScript.ai.notConfiguredMiddle')} <code className="text-xs">docs/AI_FEATURES.md</code>.
      </p>
    )
  }

  if (!form) {
    return (
      <form onSubmit={handleGenerate} className="grid gap-3">
        <textarea
          placeholder={t('addScript.ai.descriptionPlaceholder')}
          rows={4}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        {error && <p className="text-sm text-warning">{error}</p>}
        <button
          type="submit"
          disabled={generating || !description.trim()}
          className="w-fit rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light disabled:opacity-40"
        >
          {generating ? t('addScript.ai.generating') : t('addScript.ai.generate')}
        </button>
      </form>
    )
  }

  return (
    <form onSubmit={handleAdd} className="grid gap-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <input
          placeholder={t('addScript.ai.nameLabel')}
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <input
          placeholder={t('addScript.ai.hostLabel')}
          value={form.host}
          onChange={(e) => setForm((f) => ({ ...f, host: e.target.value }))}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
      </div>
      <p className="text-xs text-text-tertiary">{t('addScript.ai.reviewHint')}</p>
      <textarea
        rows={14}
        value={form.content}
        onChange={(e) => setForm((f) => ({ ...f, content: e.target.value }))}
        className="rounded border border-border-strong bg-panel px-3 py-2 font-mono text-xs text-text-primary outline-none focus:border-blue"
      />
      {error && <p className="text-sm text-warning">{error}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={adding}
          className="w-fit rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light disabled:opacity-50"
        >
          {adding ? t('common.saving') : t('addScript.ai.addToCatalog')}
        </button>
        <button
          type="button"
          disabled={adding}
          onClick={() => setForm(null)}
          className="w-fit rounded border border-border-strong px-4 py-2 text-sm text-text-secondary disabled:opacity-50"
        >
          {t('addScript.ai.regenerate')}
        </button>
      </div>
    </form>
  )
}

function ScanImportTab() {
  const { t } = useTranslation()
  const [path, setPath] = useState('')
  const [host, setHost] = useState('')
  const [candidates, setCandidates] = useState(null)
  const [selected, setSelected] = useState(() => new Set())
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const [importing, setImporting] = useState(false)
  const navigate = useNavigate()

  async function handleScan(e) {
    e.preventDefault()
    setError('')
    setStatus('')
    try {
      const result = await api.scanPath(path)
      setCandidates(result.candidates)
      setSelected(new Set(result.candidates.filter((c) => !c.already_imported).map((c) => c.path)))
    } catch {
      setError(t('addScript.scan.scanFailed'))
      setCandidates(null)
    }
  }

  function toggle(path) {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(path) ? next.delete(path) : next.add(path)
      return next
    })
  }

  async function handleImport() {
    if (selected.size === 0 || importing) return
    setImporting(true)
    const result = await api.confirmImport([...selected], host)
    setStatus(t('addScript.scan.importSummary', { created: result.created, updated: result.updated }))
    setTimeout(() => navigate('/'), 900)
  }

  return (
    <div>
      <form onSubmit={handleScan} className="mb-4 flex flex-col gap-3 sm:flex-row">
        <input
          type="text"
          placeholder={t('addScript.scan.pathPlaceholder')}
          value={path}
          onChange={(e) => setPath(e.target.value)}
          className="flex-1 rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <input
          type="text"
          placeholder={t('addScript.scan.hostPlaceholder')}
          value={host}
          onChange={(e) => setHost(e.target.value)}
          className="w-40 rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <button
          type="submit"
          className="rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light"
        >
          {t('addScript.scan.scan')}
        </button>
      </form>

      {error && <p className="mb-4 text-sm text-warning">{error}</p>}
      {status && <p className="mb-4 text-sm text-success">{status}</p>}

      {candidates && (
        <>
          {candidates.length === 0 ? (
            <p className="text-text-tertiary">{t('addScript.scan.noFilesFound')}</p>
          ) : (
            <div className="mb-4 divide-y divide-border rounded-lg border border-border bg-panel">
              {candidates.map((c) => (
                <label
                  key={c.path}
                  className={`flex items-start gap-3 px-4 py-3 ${c.already_imported ? 'opacity-50' : 'cursor-pointer hover:bg-fjord/30'}`}
                >
                  <input
                    type="checkbox"
                    disabled={c.already_imported}
                    checked={selected.has(c.path)}
                    onChange={() => toggle(c.path)}
                    className="mt-1"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-text-primary">{c.name}</span>
                      {c.already_imported && (
                        <span className="text-[10px] uppercase text-text-tertiary">{t('addScript.scan.alreadyImported')}</span>
                      )}
                      {c.has_possible_secret && (
                        <span className="rounded border border-warning/40 bg-warning/10 px-1.5 py-0.5 text-[10px] uppercase text-warning">
                          secret?
                        </span>
                      )}
                    </div>
                    <p className="truncate text-xs text-text-tertiary">{c.path}</p>
                    {c.short_description && (
                      <p className="mt-0.5 text-sm text-text-secondary">{c.short_description}</p>
                    )}
                  </div>
                </label>
              ))}
            </div>
          )}
          <button
            type="button"
            disabled={selected.size === 0 || importing}
            onClick={handleImport}
            className="rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light disabled:opacity-40"
          >
            {importing ? t('common.saving') : t('addScript.scan.importSelected', { count: selected.size })}
          </button>
        </>
      )}
    </div>
  )
}

function RemoteScanTab() {
  const { t } = useTranslation()
  const [machines, setMachines] = useState([])
  const [machineId, setMachineId] = useState('')
  const [path, setPath] = useState('')
  const [host, setHost] = useState('')
  const [candidates, setCandidates] = useState(null)
  const [selected, setSelected] = useState(() => new Set())
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const [importing, setImporting] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    api.machines().then((r) => {
      setMachines(r.machines)
      if (r.machines.length > 0) {
        setMachineId(String(r.machines[0].id))
        setHost(r.machines[0].name)
      }
    }).catch(() => {})
  }, [])

  async function handleScan(e) {
    e.preventDefault()
    setError('')
    setStatus('')
    setScanning(true)
    try {
      const result = await api.remoteScan(Number(machineId), path)
      setCandidates(result.candidates)
      setSelected(new Set(result.candidates.filter((c) => !c.already_imported).map((c) => c.path)))
    } catch (err) {
      setError(err.message || t('addScript.remote.scanFailed'))
      setCandidates(null)
    } finally {
      setScanning(false)
    }
  }

  function toggle(path) {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(path) ? next.delete(path) : next.add(path)
      return next
    })
  }

  async function handleImport() {
    if (selected.size === 0 || importing) return
    setImporting(true)
    const items = candidates
      .filter((c) => selected.has(c.path))
      .map((c) => ({ path: c.path, content: c.content }))
    const result = await api.remoteConfirmImport(Number(machineId), host, items)
    setStatus(t('addScript.remote.importSummary', { created: result.created, updated: result.updated }))
    setTimeout(() => navigate('/'), 900)
  }

  if (machines.length === 0) {
    return (
      <p className="text-text-tertiary">
        {t('addScript.remote.noMachinesPrefix')}{' '}
        <a href="/settings" className="text-blue-light hover:underline">
          {t('addScript.remote.noMachinesLink')}
        </a>{' '}
        {t('addScript.remote.noMachinesSuffix')}
      </p>
    )
  }

  return (
    <div>
      <form onSubmit={handleScan} className="mb-4 flex flex-col gap-3 sm:flex-row">
        <select
          value={machineId}
          onChange={(e) => {
            setMachineId(e.target.value)
            const m = machines.find((mm) => String(mm.id) === e.target.value)
            if (m) setHost(m.name)
          }}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        >
          {machines.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder={t('addScript.remote.pathPlaceholder')}
          value={path}
          onChange={(e) => setPath(e.target.value)}
          className="flex-1 rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <button
          type="submit"
          disabled={scanning || !path}
          className="rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light disabled:opacity-40"
        >
          {scanning ? t('addScript.remote.scanning') : t('addScript.remote.scan')}
        </button>
      </form>

      {error && <p className="mb-4 text-sm text-warning">{error}</p>}
      {status && <p className="mb-4 text-sm text-success">{status}</p>}

      {candidates && (
        <>
          {candidates.length === 0 ? (
            <p className="text-text-tertiary">{t('addScript.remote.noFilesFound')}</p>
          ) : (
            <div className="mb-4 divide-y divide-border rounded-lg border border-border bg-panel">
              {candidates.map((c) => (
                <label
                  key={c.path}
                  className={`flex items-start gap-3 px-4 py-3 ${c.already_imported ? 'opacity-50' : 'cursor-pointer hover:bg-fjord/30'}`}
                >
                  <input
                    type="checkbox"
                    disabled={c.already_imported}
                    checked={selected.has(c.path)}
                    onChange={() => toggle(c.path)}
                    className="mt-1"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-text-primary">{c.name}</span>
                      {c.already_imported && (
                        <span className="text-[10px] uppercase text-text-tertiary">{t('addScript.remote.alreadyImported')}</span>
                      )}
                      {c.has_possible_secret && (
                        <span className="rounded border border-warning/40 bg-warning/10 px-1.5 py-0.5 text-[10px] uppercase text-warning">
                          secret?
                        </span>
                      )}
                    </div>
                    <p className="truncate text-xs text-text-tertiary">{c.path}</p>
                    {c.short_description && (
                      <p className="mt-0.5 text-sm text-text-secondary">{c.short_description}</p>
                    )}
                  </div>
                </label>
              ))}
            </div>
          )}
          <button
            type="button"
            disabled={selected.size === 0 || importing}
            onClick={handleImport}
            className="rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light disabled:opacity-40"
          >
            {importing ? t('common.saving') : t('addScript.remote.importSelected', { count: selected.size })}
          </button>
        </>
      )}
    </div>
  )
}

function PasteImportTab() {
  const { t } = useTranslation()
  const [form, setForm] = useState({
    name: '',
    host: '',
    tags: '',
    short_description: '',
    run_mode: '',
    source_ref: '',
    content: '',
  })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const navigate = useNavigate()

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (submitting) return
    setError('')
    if (!form.name.trim() || !form.content.trim()) {
      setError(t('addScript.paste.nameContentRequired'))
      return
    }
    setSubmitting(true)
    try {
      const created = await api.importPaste(form)
      navigate(`/scripts/${created.id}`)
    } catch {
      setError(t('addScript.paste.importFailed'))
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <input
          placeholder={t('addScript.paste.nameLabel')}
          value={form.name}
          onChange={set('name')}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <input
          placeholder={t('addScript.paste.hostPlaceholder')}
          value={form.host}
          onChange={set('host')}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <input
          placeholder={t('addScript.paste.tagsPlaceholder')}
          value={form.tags}
          onChange={set('tags')}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <input
          placeholder={t('addScript.paste.runModePlaceholder')}
          value={form.run_mode}
          onChange={set('run_mode')}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
      </div>
      <input
        placeholder={t('addScript.paste.shortDescPlaceholder')}
        value={form.short_description}
        onChange={set('short_description')}
        className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
      />
      <input
        placeholder={t('addScript.paste.sourceRefPlaceholder')}
        value={form.source_ref}
        onChange={set('source_ref')}
        className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
      />
      <textarea
        placeholder={t('addScript.paste.contentPlaceholder')}
        rows={12}
        value={form.content}
        onChange={set('content')}
        className="rounded border border-border-strong bg-panel px-3 py-2 font-mono text-xs text-text-primary outline-none focus:border-blue"
      />
      {error && <p className="text-sm text-warning">{error}</p>}
      <button
        type="submit"
        disabled={submitting}
        className="w-fit rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light disabled:opacity-50"
      >
        {submitting ? t('common.saving') : t('addScript.paste.addToCatalog')}
      </button>
    </form>
  )
}

export default function AddScript() {
  const { t } = useTranslation()
  const [tab, setTab] = useState('scan')

  return (
    <div>
      <h1 className="mb-6 text-xl font-semibold text-text-primary">{t('addScript.title')}</h1>
      <div className="mb-6 flex gap-1 overflow-x-auto border-b border-border">
        {[
          ['scan', t('addScript.tabs.scan')],
          ['remote', t('addScript.tabs.remote')],
          ['paste', t('addScript.tabs.paste')],
          ['ai', t('addScript.tabs.ai')],
        ].map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={`shrink-0 whitespace-nowrap px-4 py-2 text-sm font-medium ${
              tab === key
                ? 'border-b-2 border-blue text-text-primary'
                : 'text-text-tertiary hover:text-text-secondary'
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === 'scan' && <ScanImportTab />}
      {tab === 'remote' && <RemoteScanTab />}
      {tab === 'paste' && <PasteImportTab />}
      {tab === 'ai' && <AIGenerateTab />}
    </div>
  )
}
