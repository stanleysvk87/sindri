import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../lib/api'

function EditableField({ label, value, onSave, multiline = false, placeholder = '' }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value)

  useEffect(() => setDraft(value), [value])

  if (!editing) {
    return (
      <div className="mb-4">
        <div className="mb-1 flex items-center justify-between">
          <h3 className="text-xs uppercase tracking-wide text-text-tertiary">{label}</h3>
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="text-xs text-blue-light hover:underline"
          >
            upraviť
          </button>
        </div>
        <p className="whitespace-pre-wrap text-sm text-text-primary">
          {value || <span className="text-text-tertiary">{placeholder}</span>}
        </p>
      </div>
    )
  }

  return (
    <div className="mb-4">
      <h3 className="mb-1 text-xs uppercase tracking-wide text-text-tertiary">{label}</h3>
      {multiline ? (
        <textarea
          autoFocus
          rows={5}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          className="w-full rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
      ) : (
        <input
          autoFocus
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          className="w-full rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
      )}
      <div className="mt-2 flex gap-2">
        <button
          type="button"
          onClick={() => {
            onSave(draft)
            setEditing(false)
          }}
          className="rounded bg-blue px-3 py-1 text-xs font-medium text-white hover:bg-blue-light"
        >
          Uložiť
        </button>
        <button
          type="button"
          onClick={() => {
            setDraft(value)
            setEditing(false)
          }}
          className="rounded border border-border-strong px-3 py-1 text-xs text-text-secondary"
        >
          Zrušiť
        </button>
      </div>
    </div>
  )
}

export default function ScriptDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [script, setScript] = useState(null)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState('')
  const [aiAvailable, setAiAvailable] = useState(null)
  const [reviewing, setReviewing] = useState(false)
  const [review, setReview] = useState('')
  const [reviewError, setReviewError] = useState('')
  const [sandboxAvailable, setSandboxAvailable] = useState(null)
  const [sandboxRunning, setSandboxRunning] = useState(false)
  const [sandboxResult, setSandboxResult] = useState(null)

  function reload() {
    api.getScript(id).then(setScript).catch(() => setError('Skript sa nenašiel.'))
  }

  useEffect(reload, [id])
  useEffect(() => {
    api.aiStatus().then((s) => setAiAvailable(s.available)).catch(() => setAiAvailable(false))
    api.sandboxStatus().then((s) => setSandboxAvailable(s.available)).catch(() => setSandboxAvailable(false))
  }, [])

  async function save(field, value) {
    const updated = await api.updateScript(id, { [field]: value })
    setScript(updated)
  }

  async function handleCopy() {
    await navigator.clipboard.writeText(script.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  async function handleDelete() {
    if (!confirm(`Naozaj zmazať "${script.name}" z katalógu? (originál na disku sa netýka)`)) return
    await api.deleteScript(id)
    navigate('/')
  }

  async function handleReview() {
    setReviewing(true)
    setReviewError('')
    setReview('')
    try {
      const result = await api.aiReview(script.name, script.content)
      setReview(result.review)
    } catch {
      setReviewError('AI review zlyhal alebo nie je dostupný.')
    } finally {
      setReviewing(false)
    }
  }

  async function handleSandboxRun() {
    setSandboxRunning(true)
    setSandboxResult(null)
    try {
      const result = await api.sandboxRun(script.content)
      setSandboxResult(result)
    } catch {
      setSandboxResult({ error: 'Sandbox beh zlyhal.' })
    } finally {
      setSandboxRunning(false)
    }
  }

  async function handleAppendReviewToNotes() {
    const combined = script.notes ? `${script.notes}\n\n--- AI review ---\n${review}` : `--- AI review ---\n${review}`
    await save('notes', combined)
    setReview('')
  }

  if (error) return <p className="text-warning">{error}</p>
  if (!script) return <p className="text-text-tertiary">Načítavam...</p>

  return (
    <div>
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">{script.name}</h1>
          <p className="mt-1 text-xs text-text-tertiary">
            {script.source_type === 'local_import' ? `Import z ${script.source_ref}` : 'Vložené ručne'}
            {script.source_ref && script.source_type === 'pasted' && ` · zdroj: ${script.source_ref}`}
          </p>
        </div>
        <button
          type="button"
          onClick={handleDelete}
          className="text-xs text-text-tertiary hover:text-warning"
        >
          Odstrániť z katalógu
        </button>
      </div>

      {script.has_possible_secret && (
        <div className="mb-6 rounded border border-warning/40 bg-warning/10 px-3 py-2 text-sm text-warning">
          Obsah tohto skriptu vyzerá, že obsahuje heslo alebo token natvrdo v tele. Zváž jeho
          presun do premennej prostredia pred ďalším zdieľaním.
        </div>
      )}

      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <EditableField label="Stroj" value={script.host} onSave={(v) => save('host', v)} placeholder="opi / victus / kdekoľvek" />
        <EditableField label="Spôsob spustenia" value={script.run_mode} onSave={(v) => save('run_mode', v)} placeholder="manuál / cron / systemd" />
        <EditableField label="Tagy (čiarkou)" value={script.tags} onSave={(v) => save('tags', v)} placeholder="žiadne" />
        <div className="mb-4">
          <h3 className="mb-1 text-xs uppercase tracking-wide text-text-tertiary">Naposledy upravené</h3>
          <p className="text-sm text-text-primary">{new Date(script.updated_at).toLocaleString('sk-SK')}</p>
        </div>
      </div>

      <EditableField
        label="Krátky popis (v zozname)"
        value={script.short_description}
        onSave={(v) => save('short_description', v)}
        placeholder="bez popisu"
      />
      <EditableField
        label="Čo presne to je a čo to robí"
        value={script.long_description}
        onSave={(v) => save('long_description', v)}
        multiline
        placeholder="bez detailného popisu"
      />
      <EditableField
        label="Poznámky"
        value={script.notes}
        onSave={(v) => save('notes', v)}
        multiline
        placeholder="žiadne poznámky"
      />

      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-xs uppercase tracking-wide text-text-tertiary">Obsah</h3>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleCopy}
            className="rounded bg-blue px-3 py-1 text-xs font-medium text-white hover:bg-blue-light"
          >
            {copied ? 'Skopírované ✓' : 'Kopírovať'}
          </button>
          {aiAvailable && (
            <button
              type="button"
              onClick={handleReview}
              disabled={reviewing}
              className="rounded border border-border-strong px-3 py-1 text-xs text-text-secondary hover:border-blue hover:text-text-primary disabled:opacity-50"
            >
              {reviewing ? 'AI kontroluje...' : 'Skontrolovať cez AI'}
            </button>
          )}
          {sandboxAvailable && (
            <button
              type="button"
              onClick={handleSandboxRun}
              disabled={sandboxRunning}
              title="Izolovaný, jednorazový kontajner: bez siete, limitovaná pamäť/čas, zahodený po behu."
              className="rounded border border-border-strong px-3 py-1 text-xs text-text-secondary hover:border-blue hover:text-text-primary disabled:opacity-50"
            >
              {sandboxRunning ? 'Beží v sandboxe...' : 'Testovať v sandboxe'}
            </button>
          )}
          <button
            type="button"
            disabled
            title="Zatiaľ vypnuté — bude vyžadovať overenie sudo hesla pri každom spustení. Pozri docs/REMOTE_EXEC.md."
            className="cursor-not-allowed rounded border border-border-strong px-3 py-1 text-xs text-text-tertiary opacity-50"
          >
            Spustiť na diaľku (čoskoro)
          </button>
        </div>
      </div>
      <pre className="overflow-x-auto rounded-lg border border-border bg-panel p-4 font-mono text-xs text-text-primary">
        {script.content}
      </pre>

      {sandboxResult && (
        <div className="mt-4 rounded-lg border border-border bg-panel p-4">
          <h3 className="mb-2 text-xs uppercase tracking-wide text-text-tertiary">
            Sandbox výstup {sandboxResult.exit_code != null && `(exit ${sandboxResult.exit_code})`}
            {sandboxResult.timed_out && ' — TIMEOUT'}
          </h3>
          {sandboxResult.error ? (
            <p className="text-sm text-warning">{sandboxResult.error}</p>
          ) : (
            <>
              {sandboxResult.stdout && (
                <pre className="mb-2 overflow-x-auto whitespace-pre-wrap text-xs text-text-primary">{sandboxResult.stdout}</pre>
              )}
              {sandboxResult.stderr && (
                <pre className="overflow-x-auto whitespace-pre-wrap text-xs text-warning">{sandboxResult.stderr}</pre>
              )}
            </>
          )}
        </div>
      )}

      {reviewError && <p className="mt-3 text-sm text-warning">{reviewError}</p>}
      {review && (
        <div className="mt-4 rounded-lg border border-border bg-panel p-4">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-xs uppercase tracking-wide text-text-tertiary">AI review</h3>
            <button
              type="button"
              onClick={handleAppendReviewToNotes}
              className="text-xs text-blue-light hover:underline"
            >
              pridať do poznámok
            </button>
          </div>
          <p className="whitespace-pre-wrap text-sm text-text-primary">{review}</p>
        </div>
      )}
    </div>
  )
}
