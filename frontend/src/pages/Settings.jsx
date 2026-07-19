import { useEffect, useState } from 'react'
import { api } from '../lib/api'

function MachinesSection() {
  const [machines, setMachines] = useState([])
  const [keys, setKeys] = useState([])
  const [form, setForm] = useState({
    name: '',
    host: '',
    port: 22,
    ssh_user: 'stanley',
    auth_type: 'key',
    ssh_key_path: '',
  })
  const [error, setError] = useState('')

  function reload() {
    api.machines().then((r) => setMachines(r.machines)).catch(() => {})
    api.availableKeys().then((r) => {
      setKeys(r.keys)
      if (r.keys.length > 0 && !form.ssh_key_path) {
        setForm((f) => ({ ...f, ssh_key_path: r.keys[0] }))
      }
    }).catch(() => {})
  }

  useEffect(reload, [])

  async function handleAdd(e) {
    e.preventDefault()
    setError('')
    if (!form.name || !form.host) {
      setError('Meno a stroj sú povinné.')
      return
    }
    if (form.auth_type === 'key' && !form.ssh_key_path) {
      setError('Vyber SSH kľúč, alebo prepni na heslové prihlásenie.')
      return
    }
    try {
      await api.addMachine(form)
      setForm({ name: '', host: '', port: 22, ssh_user: 'stanley', auth_type: 'key', ssh_key_path: keys[0] || '' })
      reload()
    } catch {
      setError('Nepodarilo sa pridať stroj.')
    }
  }

  async function handleDelete(id) {
    if (!confirm('Odstrániť tento stroj z registra?')) return
    await api.deleteMachine(id)
    reload()
  }

  return (
    <div>
      <h2 className="mb-3 text-lg font-semibold text-text-primary">Spravované stroje</h2>
      {keys.length === 0 && (
        <p className="mb-4 text-sm text-warning">
          Žiadne SSH kľúče nenájdené na namontovanej ceste — stroje s kľúčovým prihlásením nebudú
          fungovať, kým nebude aspoň jeden kľúč dostupný (pozri docker-compose.yml). Heslové
          prihlásenie funguje aj bez toho.
        </p>
      )}
      <div className="mb-4 divide-y divide-border rounded-lg border border-border bg-panel">
        {machines.length === 0 && (
          <p className="p-4 text-sm text-text-tertiary">Žiadne stroje zaregistrované.</p>
        )}
        {machines.map((m) => (
          <div key={m.id} className="flex items-center justify-between p-4">
            <div>
              <p className="font-medium text-text-primary">{m.name}</p>
              <p className="text-xs text-text-tertiary">
                {m.ssh_user}@{m.host}:{m.port} ·{' '}
                {m.auth_type === 'password' ? 'heslo (zadáva sa pri spustení)' : `kľúč: ${m.ssh_key_path}`}
              </p>
            </div>
            <button
              type="button"
              onClick={() => handleDelete(m.id)}
              className="text-xs text-text-tertiary hover:text-warning"
            >
              odstrániť
            </button>
          </div>
        ))}
      </div>

      <form onSubmit={handleAdd} className="grid gap-3 sm:grid-cols-2">
        <input
          placeholder="Meno (napr. opi)"
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <input
          placeholder="Host (IP alebo hostname)"
          value={form.host}
          onChange={(e) => setForm((f) => ({ ...f, host: e.target.value }))}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <input
          placeholder="SSH user"
          value={form.ssh_user}
          onChange={(e) => setForm((f) => ({ ...f, ssh_user: e.target.value }))}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <input
          type="number"
          placeholder="Port"
          value={form.port}
          onChange={(e) => setForm((f) => ({ ...f, port: Number(e.target.value) }))}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />

        <div className="flex gap-4 text-sm text-text-secondary sm:col-span-2">
          <label className="flex items-center gap-1.5">
            <input
              type="radio"
              checked={form.auth_type === 'key'}
              onChange={() => setForm((f) => ({ ...f, auth_type: 'key' }))}
            />
            SSH kľúč
          </label>
          <label className="flex items-center gap-1.5">
            <input
              type="radio"
              checked={form.auth_type === 'password'}
              onChange={() => setForm((f) => ({ ...f, auth_type: 'password' }))}
            />
            Heslo (zadáš pri každom spustení, neukladá sa)
          </label>
        </div>

        {form.auth_type === 'key' && (
          <select
            value={form.ssh_key_path}
            onChange={(e) => setForm((f) => ({ ...f, ssh_key_path: e.target.value }))}
            className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue sm:col-span-2"
          >
            {keys.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        )}

        {error && <p className="text-sm text-warning sm:col-span-2">{error}</p>}
        <button
          type="submit"
          className="w-fit rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light sm:col-span-2"
        >
          Pridať stroj
        </button>
      </form>
    </div>
  )
}

function AISection() {
  const [config, setConfig] = useState(null)
  const [mode, setMode] = useState('auto')
  const [apiKey, setApiKey] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  function reload() {
    api.aiConfig().then((c) => {
      setConfig(c)
      setMode(c.provider_mode)
    }).catch(() => {})
  }

  useEffect(reload, [])

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setSaved(false)
    try {
      const payload = { provider_mode: mode }
      if (apiKey) payload.anthropic_api_key = apiKey
      await api.updateAiConfig(payload)
      setApiKey('')
      setSaved(true)
      reload()
    } finally {
      setSaving(false)
    }
  }

  if (!config) return null

  return (
    <div>
      <h2 className="mb-3 text-lg font-semibold text-text-primary">AI nastavenia</h2>
      <form onSubmit={handleSave} className="rounded-lg border border-border bg-panel p-4">
        <label className="mb-1 block text-xs uppercase tracking-wide text-text-tertiary">
          Provider mode
        </label>
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          className="mb-3 w-full rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue sm:w-64"
        >
          <option value="auto">auto (claude → codex → API kľúč)</option>
          <option value="claude_cli">len claude CLI</option>
          <option value="codex_cli">len codex CLI</option>
          <option value="anthropic_api">len Anthropic API kľúč</option>
        </select>

        <label className="mb-1 block text-xs uppercase tracking-wide text-text-tertiary">
          Anthropic API kľúč (fallback, voliteľný)
        </label>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder={
            config.has_api_key
              ? `nastavený (zdroj: ${config.api_key_source === 'settings' ? 'Nastavenia' : '.env'}) — vlož nový na prepísanie`
              : 'nenastavený'
          }
          className="mb-3 w-full rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue sm:w-96"
        />

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={saving}
            className="rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light disabled:opacity-50"
          >
            {saving ? 'Ukladám...' : 'Uložiť'}
          </button>
          {saved && <span className="text-sm text-success">Uložené ✓</span>}
        </div>
      </form>
    </div>
  )
}

function HostStatusSection() {
  const [machines, setMachines] = useState([])
  const [machineId, setMachineId] = useState('')
  const [checking, setChecking] = useState(false)
  const [result, setResult] = useState(null)

  useEffect(() => {
    api.machines().then((r) => {
      setMachines(r.machines)
      if (r.machines.length > 0) setMachineId(String(r.machines[0].id))
    }).catch(() => {})
  }, [])

  async function handleCheck() {
    setChecking(true)
    setResult(null)
    try {
      const r = await api.hostStatus(Number(machineId))
      setResult(r)
    } catch (err) {
      setResult({ error: err.message || 'Zlyhalo.' })
    } finally {
      setChecking(false)
    }
  }

  if (machines.length === 0) return null

  return (
    <div>
      <h2 className="mb-3 text-lg font-semibold text-text-primary">Stav hostiteľa</h2>
      <div className="rounded-lg border border-border bg-panel p-4">
        <p className="mb-3 text-xs text-text-tertiary">
          Beží cez rovnaké SSH spojenie ako vzdialené spustenie — vyber, ktorý zaregistrovaný stroj
          skontrolovať.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={machineId}
            onChange={(e) => setMachineId(e.target.value)}
            className="rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
          >
            {machines.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={handleCheck}
            disabled={checking}
            className="rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light disabled:opacity-50"
          >
            {checking ? 'Kontrolujem...' : 'Skontrolovať'}
          </button>
        </div>
        {result && (
          <div className="mt-3">
            {result.error || result.detail ? (
              <p className="text-sm text-warning">{result.error || result.detail}</p>
            ) : (
              <pre className="overflow-x-auto whitespace-pre-wrap rounded border border-border bg-ink p-3 text-xs text-text-primary">
                {result.stdout || result.stderr}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function StatsSection() {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    api.stats().then(setStats).catch(() => {})
  }, [])

  if (!stats) return null

  return (
    <div>
      <h2 className="mb-3 text-lg font-semibold text-text-primary">Prehľad katalógu</h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg border border-border bg-panel p-4">
          <p className="text-2xl font-semibold text-text-primary">{stats.total_scripts}</p>
          <p className="text-xs text-text-tertiary">skriptov spolu</p>
        </div>
        <div className="rounded-lg border border-border bg-panel p-4">
          <p className="text-2xl font-semibold text-text-primary">{stats.possible_secrets}</p>
          <p className="text-xs text-text-tertiary">s možným heslom/tokenom</p>
        </div>
        {Object.entries(stats.by_host).map(([host, count]) => (
          <div key={host} className="rounded-lg border border-border bg-panel p-4">
            <p className="text-2xl font-semibold text-text-primary">{count}</p>
            <p className="text-xs text-text-tertiary">{host}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function AccountSection() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newPassword2, setNewPassword2] = useState('')
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSaved(false)
    if (newPassword.length < 8) {
      setError('Nové heslo musí mať aspoň 8 znakov.')
      return
    }
    if (newPassword !== newPassword2) {
      setError('Nové heslá sa nezhodujú.')
      return
    }
    setSaving(true)
    try {
      await api.updateAccountPassword(currentPassword, newPassword)
      setCurrentPassword('')
      setNewPassword('')
      setNewPassword2('')
      setSaved(true)
    } catch (err) {
      setError(err.message === 'Request failed: 401' ? 'Súčasné heslo nesedí.' : 'Nepodarilo sa zmeniť heslo.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <h2 className="mb-3 text-lg font-semibold text-text-primary">Účet</h2>
      <form onSubmit={handleSubmit} className="grid gap-3 rounded-lg border border-border bg-panel p-4 sm:w-96">
        <input
          type="password"
          placeholder="Súčasné heslo"
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
          className="rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <input
          type="password"
          placeholder="Nové heslo (min. 8 znakov)"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          className="rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <input
          type="password"
          placeholder="Zopakuj nové heslo"
          value={newPassword2}
          onChange={(e) => setNewPassword2(e.target.value)}
          className="rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        {error && <p className="text-sm text-warning">{error}</p>}
        {saved && <p className="text-sm text-success">Heslo zmenené ✓</p>}
        <button
          type="submit"
          disabled={saving || !currentPassword || !newPassword}
          className="w-fit rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light disabled:opacity-50"
        >
          {saving ? 'Ukladám...' : 'Zmeniť heslo'}
        </button>
      </form>
    </div>
  )
}

function AppLogSection() {
  const [log, setLog] = useState('')
  const [loading, setLoading] = useState(false)

  function reload() {
    setLoading(true)
    api.appLog(300).then((r) => setLog(r.log)).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(reload, [])

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary">Logy appky</h2>
        <button
          type="button"
          onClick={reload}
          className="text-xs text-blue-light hover:underline"
        >
          {loading ? 'Načítavam...' : 'Obnoviť'}
        </button>
      </div>
      <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-lg border border-border bg-panel p-4 font-mono text-xs text-text-secondary">
        {log || 'Zatiaľ žiadne zaznamenané chyby.'}
      </pre>
    </div>
  )
}

export default function Settings() {
  return (
    <div className="grid gap-8">
      <StatsSection />
      <HostStatusSection />
      <MachinesSection />
      <AISection />
      <AccountSection />
      <AuditLogSection />
      <AppLogSection />
    </div>
  )
}

function AuditLogSection() {
  const [entries, setEntries] = useState([])

  useEffect(() => {
    api.auditLog().then((r) => setEntries(r.entries)).catch(() => {})
  }, [])

  return (
    <div>
      <h2 className="mb-3 text-lg font-semibold text-text-primary">Log aktivity</h2>
      <div className="divide-y divide-border rounded-lg border border-border bg-panel">
        {entries.length === 0 && (
          <p className="p-4 text-sm text-text-tertiary">Zatiaľ žiadna aktivita.</p>
        )}
        {entries.map((e) => (
          <div key={e.id} className="p-3 text-sm">
            <span className="text-text-tertiary">{new Date(e.created_at).toLocaleString('sk-SK')}</span>
            {' — '}
            <span className="font-medium text-text-primary">{e.action}</span>
            {e.script_name && <span className="text-text-secondary"> {e.script_name}</span>}
            {e.detail && <span className="text-text-tertiary"> ({e.detail})</span>}
          </div>
        ))}
      </div>
    </div>
  )
}
