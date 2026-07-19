import { useEffect, useState } from 'react'
import { api } from '../lib/api'

function MachinesSection() {
  const [machines, setMachines] = useState([])
  const [keys, setKeys] = useState([])
  const [form, setForm] = useState({ name: '', host: '', port: 22, ssh_user: 'stanley', ssh_key_path: '' })
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
    if (!form.name || !form.host || !form.ssh_key_path) {
      setError('Meno, stroj a kľúč sú povinné.')
      return
    }
    try {
      await api.addMachine(form)
      setForm({ name: '', host: '', port: 22, ssh_user: 'stanley', ssh_key_path: keys[0] || '' })
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
          Žiadne SSH kľúče nenájdené na namontovanej ceste — vzdialené spustenie nebude fungovať,
          kým nebude aspoň jeden kľúč dostupný (pozri docker-compose.yml).
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
                {m.ssh_user}@{m.host}:{m.port} · kľúč: {m.ssh_key_path}
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

export default function Settings() {
  return (
    <div className="grid gap-8">
      <StatsSection />
      <MachinesSection />
      <AuditLogSection />
    </div>
  )
}
