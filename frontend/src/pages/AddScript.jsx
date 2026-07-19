import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

function AIGenerateTab() {
  const [aiAvailable, setAiAvailable] = useState(null)
  const [description, setDescription] = useState('')
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState(null) // {name, host, tags, short_description, content}
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
        ? 'AI momentálne nie je dostupné (nie je nastavené claude/codex CLI ani API kľúč).'
        : 'Generovanie zlyhalo.')
    } finally {
      setGenerating(false)
    }
  }

  async function handleAdd(e) {
    e.preventDefault()
    if (!form.name.trim()) {
      setError('Meno je povinné.')
      return
    }
    try {
      const created = await api.importPaste({ ...form, source_ref: 'AI vygenerované' })
      navigate(`/scripts/${created.id}`)
    } catch {
      setError('Pridanie zlyhalo.')
    }
  }

  if (aiAvailable === false) {
    return (
      <p className="text-text-tertiary">
        AI generovanie nie je nakonfigurované na tomto serveri — potrebuje prihlásený{' '}
        <code className="text-xs">claude</code>/<code className="text-xs">codex</code> CLI alebo
        API kľúč. Pozri <code className="text-xs">docs/AI_FEATURES.md</code>.
      </p>
    )
  }

  if (!form) {
    return (
      <form onSubmit={handleGenerate} className="grid gap-3">
        <textarea
          placeholder="Popíš čo má skript robiť (napr. 'skript čo zálohuje priečinok do tar.gz s dátumom v názve')"
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
          {generating ? 'Generujem...' : 'Vygenerovať'}
        </button>
      </form>
    )
  }

  return (
    <form onSubmit={handleAdd} className="grid gap-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <input
          placeholder="Meno *"
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <input
          placeholder="Stroj"
          value={form.host}
          onChange={(e) => setForm((f) => ({ ...f, host: e.target.value }))}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
      </div>
      <p className="text-xs text-text-tertiary">
        Skontroluj vygenerovaný obsah pred pridaním — AI sa môže mýliť.
      </p>
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
          className="w-fit rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light"
        >
          Pridať do katalógu
        </button>
        <button
          type="button"
          onClick={() => setForm(null)}
          className="w-fit rounded border border-border-strong px-4 py-2 text-sm text-text-secondary"
        >
          Vygenerovať znova
        </button>
      </div>
    </form>
  )
}

function ScanImportTab() {
  const [path, setPath] = useState('')
  const [host, setHost] = useState('')
  const [candidates, setCandidates] = useState(null)
  const [selected, setSelected] = useState(() => new Set())
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
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
      setError('Priečinok sa nepodarilo prehľadať — over cestu (musí byť dostupná v kontajneri).')
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
    if (selected.size === 0) return
    const result = await api.confirmImport([...selected], host)
    setStatus(`Pridané: ${result.created}, aktualizované: ${result.updated}.`)
    setTimeout(() => navigate('/'), 900)
  }

  return (
    <div>
      <form onSubmit={handleScan} className="mb-4 flex flex-col gap-3 sm:flex-row">
        <input
          type="text"
          placeholder="/home/stanley/scripts"
          value={path}
          onChange={(e) => setPath(e.target.value)}
          className="flex-1 rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <input
          type="text"
          placeholder="stroj (napr. opi)"
          value={host}
          onChange={(e) => setHost(e.target.value)}
          className="w-40 rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <button
          type="submit"
          className="rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light"
        >
          Prehľadať
        </button>
      </form>

      {error && <p className="mb-4 text-sm text-warning">{error}</p>}
      {status && <p className="mb-4 text-sm text-success">{status}</p>}

      {candidates && (
        <>
          {candidates.length === 0 ? (
            <p className="text-text-tertiary">Žiadne .sh/.py súbory nenájdené.</p>
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
                        <span className="text-[10px] uppercase text-text-tertiary">už v katalógu</span>
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
            disabled={selected.size === 0}
            onClick={handleImport}
            className="rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light disabled:opacity-40"
          >
            Importovať vybrané ({selected.size})
          </button>
        </>
      )}
    </div>
  )
}

function RemoteScanTab() {
  const [machines, setMachines] = useState([])
  const [machineId, setMachineId] = useState('')
  const [path, setPath] = useState('')
  const [host, setHost] = useState('')
  const [candidates, setCandidates] = useState(null)
  const [selected, setSelected] = useState(() => new Set())
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
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
      setError(err.message || 'Prehľadávanie zlyhalo.')
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
    if (selected.size === 0) return
    const items = candidates
      .filter((c) => selected.has(c.path))
      .map((c) => ({ path: c.path, content: c.content }))
    const result = await api.remoteConfirmImport(Number(machineId), host, items)
    setStatus(`Pridané: ${result.created}, aktualizované: ${result.updated}.`)
    setTimeout(() => navigate('/'), 900)
  }

  if (machines.length === 0) {
    return (
      <p className="text-text-tertiary">
        Žiadne stroje zaregistrované — pridaj aspoň jeden v{' '}
        <a href="/settings" className="text-blue-light hover:underline">
          Nastaveniach
        </a>{' '}
        predtým, než budeš vedieť prehľadávať vzdialenú cestu.
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
          placeholder="/home/stanley/scripts (cesta na vzdialenom stroji)"
          value={path}
          onChange={(e) => setPath(e.target.value)}
          className="flex-1 rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <button
          type="submit"
          disabled={scanning || !path}
          className="rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light disabled:opacity-40"
        >
          {scanning ? 'Prehľadávam...' : 'Prehľadať'}
        </button>
      </form>

      {error && <p className="mb-4 text-sm text-warning">{error}</p>}
      {status && <p className="mb-4 text-sm text-success">{status}</p>}

      {candidates && (
        <>
          {candidates.length === 0 ? (
            <p className="text-text-tertiary">Žiadne .sh/.py súbory nenájdené.</p>
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
                        <span className="text-[10px] uppercase text-text-tertiary">už v katalógu</span>
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
            disabled={selected.size === 0}
            onClick={handleImport}
            className="rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light disabled:opacity-40"
          >
            Importovať vybrané ({selected.size})
          </button>
        </>
      )}
    </div>
  )
}

function PasteImportTab() {
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
  const navigate = useNavigate()

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (!form.name.trim() || !form.content.trim()) {
      setError('Meno a obsah sú povinné.')
      return
    }
    try {
      const created = await api.importPaste(form)
      navigate(`/scripts/${created.id}`)
    } catch {
      setError('Import zlyhal.')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <input
          placeholder="Meno *"
          value={form.name}
          onChange={set('name')}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <input
          placeholder="Stroj (opi / victus / kdekoľvek)"
          value={form.host}
          onChange={set('host')}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <input
          placeholder="Tagy (čiarkou)"
          value={form.tags}
          onChange={set('tags')}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <input
          placeholder="Spôsob spustenia (manuál/cron/systemd)"
          value={form.run_mode}
          onChange={set('run_mode')}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
      </div>
      <input
        placeholder="Krátky popis"
        value={form.short_description}
        onChange={set('short_description')}
        className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
      />
      <input
        placeholder="Zdrojová URL (voliteľné, len ako poznámka — obsah sa nikdy nesťahuje automaticky)"
        value={form.source_ref}
        onChange={set('source_ref')}
        className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
      />
      <textarea
        placeholder="Obsah skriptu *"
        rows={12}
        value={form.content}
        onChange={set('content')}
        className="rounded border border-border-strong bg-panel px-3 py-2 font-mono text-xs text-text-primary outline-none focus:border-blue"
      />
      {error && <p className="text-sm text-warning">{error}</p>}
      <button
        type="submit"
        className="w-fit rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light"
      >
        Pridať do katalógu
      </button>
    </form>
  )
}

export default function AddScript() {
  const [tab, setTab] = useState('scan')

  return (
    <div>
      <h1 className="mb-6 text-xl font-semibold text-text-primary">Pridať skript</h1>
      <div className="mb-6 flex gap-1 border-b border-border">
        {[
          ['scan', 'Prehľadať priečinok'],
          ['remote', 'Vzdialená cesta (SSH)'],
          ['paste', 'Vložiť obsah'],
          ['ai', 'Vygenerovať cez AI'],
        ].map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={`px-4 py-2 text-sm font-medium ${
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
