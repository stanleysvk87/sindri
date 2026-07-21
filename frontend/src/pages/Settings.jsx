import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { useTranslation } from '../i18n/I18nContext.jsx'

function ScheduleCheckSection() {
  const { t } = useTranslation()
  const [result, setResult] = useState(null)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState('')

  async function handleCheck() {
    setChecking(true)
    setError('')
    try {
      const r = await api.scheduleCheck()
      setResult(r.results)
    } catch (err) {
      setError(err.message || t('settings.scheduleCheck.failed'))
    } finally {
      setChecking(false)
    }
  }

  return (
    <div>
      <h2 className="mb-3 text-lg font-semibold text-text-primary">{t('settings.scheduleCheck.title')}</h2>
      <div className="rounded-lg border border-border bg-panel p-4">
        <p className="mb-3 text-xs text-text-tertiary">{t('settings.scheduleCheck.description')}</p>
        <button
          type="button"
          onClick={handleCheck}
          disabled={checking}
          className="rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light disabled:opacity-50"
        >
          {checking ? t('settings.scheduleCheck.checking') : t('settings.scheduleCheck.check')}
        </button>
        {error && <p className="mt-3 text-sm text-warning">{error}</p>}
        {result && (
          <div className="mt-3 flex flex-col gap-3">
            {result.length === 0 && <p className="text-sm text-text-tertiary">{t('settings.scheduleCheck.noMachines')}</p>}
            {result.map((r) => (
              <div key={r.machine_name} className="rounded border border-border bg-ink p-3 text-xs">
                <p className="mb-2 font-medium text-text-primary">{r.machine_name}</p>
                {r.error ? (
                  <p className="text-warning">{r.error}</p>
                ) : r.mismatches.length === 0 ? (
                  <p className="text-success">{t('settings.scheduleCheck.allMatch', { checked: r.checked })}</p>
                ) : (
                  <div className="flex flex-col gap-1">
                    {r.mismatches.map((m) => (
                      <Link key={m.id} to={`/scripts/${m.id}`} className="text-text-secondary hover:text-text-primary">
                        <span className="font-medium">{m.name}</span> —{' '}
                        <span className="text-warning">
                          {m.issue === 'claimed_not_found'
                            ? t('settings.scheduleCheck.claimedNotFound')
                            : t('settings.scheduleCheck.foundNotClaimed')}
                        </span>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function OrphanedSection() {
  const { t } = useTranslation()
  const [result, setResult] = useState(null)
  const [checking, setChecking] = useState(false)

  async function handleCheck() {
    setChecking(true)
    try {
      const r = await api.orphanedScripts()
      setResult(r)
    } finally {
      setChecking(false)
    }
  }

  return (
    <div>
      <h2 className="mb-3 text-lg font-semibold text-text-primary">{t('settings.orphaned.title')}</h2>
      <div className="rounded-lg border border-border bg-panel p-4">
        <p className="mb-3 text-xs text-text-tertiary">{t('settings.orphaned.description')}</p>
        <button
          type="button"
          onClick={handleCheck}
          disabled={checking}
          className="rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light disabled:opacity-50"
        >
          {checking ? t('settings.orphaned.checking') : t('settings.orphaned.check')}
        </button>
        {result && (
          <div className="mt-3">
            <p className="mb-2 text-xs text-text-tertiary">
              {t('settings.orphaned.summary', { checked: result.checked, skipped: result.skipped_remote })}
            </p>
            {result.orphaned.length === 0 ? (
              <p className="text-sm text-success">{t('settings.orphaned.none')}</p>
            ) : (
              <div className="divide-y divide-border rounded border border-border">
                {result.orphaned.map((o) => (
                  <Link key={o.id} to={`/scripts/${o.id}`} className="block p-3 text-sm hover:bg-fjord/30">
                    <span className="font-medium text-text-primary">{o.name}</span>{' '}
                    <span className="text-xs text-warning">
                      {o.reason === 'machine_gone'
                        ? t('settings.orphaned.reasonMachineGone')
                        : t('settings.orphaned.reasonMissingFile')}
                    </span>
                    <p className="truncate text-xs text-text-tertiary">{o.source_ref}</p>
                  </Link>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function MachinesSection() {
  const { t } = useTranslation()
  const [machines, setMachines] = useState([])
  const [keys, setKeys] = useState([])
  const [form, setForm] = useState({
    name: '',
    host: '',
    port: 22,
    ssh_user: '',
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
      setError(t('settings.machines.nameHostRequired'))
      return
    }
    if (form.auth_type === 'key' && !form.ssh_key_path) {
      setError(t('settings.machines.selectKeyOrPassword'))
      return
    }
    try {
      await api.addMachine(form)
      setForm({ name: '', host: '', port: 22, ssh_user: '', auth_type: 'key', ssh_key_path: keys[0] || '' })
      reload()
    } catch {
      setError(t('settings.machines.addFailed'))
    }
  }

  async function handleDelete(id) {
    if (!confirm(t('settings.machines.confirmDelete'))) return
    await api.deleteMachine(id)
    reload()
  }

  return (
    <div>
      <h2 className="mb-3 text-lg font-semibold text-text-primary">{t('settings.machines.title')}</h2>
      {keys.length === 0 && (
        <p className="mb-4 text-sm text-warning">{t('settings.machines.noKeysWarning')}</p>
      )}
      <div className="mb-4 divide-y divide-border rounded-lg border border-border bg-panel">
        {machines.length === 0 && (
          <p className="p-4 text-sm text-text-tertiary">{t('settings.machines.noneRegistered')}</p>
        )}
        {machines.map((m) => (
          <div key={m.id} className="flex items-center justify-between p-4">
            <div>
              <p className="font-medium text-text-primary">{m.name}</p>
              <p className="text-xs text-text-tertiary">
                {m.ssh_user}@{m.host}:{m.port} ·{' '}
                {m.auth_type === 'password' ? t('settings.machines.passwordAuth') : t('settings.machines.keyAuth', { key: m.ssh_key_path })}
              </p>
            </div>
            <button
              type="button"
              onClick={() => handleDelete(m.id)}
              className="text-xs text-text-tertiary hover:text-warning"
            >
              {t('settings.machines.remove')}
            </button>
          </div>
        ))}
      </div>

      <form onSubmit={handleAdd} className="grid gap-3 sm:grid-cols-2">
        <input
          placeholder={t('settings.machines.namePlaceholder')}
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <input
          placeholder={t('settings.machines.hostPlaceholder')}
          value={form.host}
          onChange={(e) => setForm((f) => ({ ...f, host: e.target.value }))}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <input
          placeholder={t('settings.machines.sshUserPlaceholder')}
          value={form.ssh_user}
          onChange={(e) => setForm((f) => ({ ...f, ssh_user: e.target.value }))}
          className="rounded border border-border-strong bg-panel px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <input
          type="number"
          placeholder={t('settings.machines.portPlaceholder')}
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
            {t('settings.machines.keyAuthRadio')}
          </label>
          <label className="flex items-center gap-1.5">
            <input
              type="radio"
              checked={form.auth_type === 'password'}
              onChange={() => setForm((f) => ({ ...f, auth_type: 'password' }))}
            />
            {t('settings.machines.passwordAuthRadio')}
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
          {t('settings.machines.addMachine')}
        </button>
      </form>
    </div>
  )
}

function AISection() {
  const { t } = useTranslation()
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
      <h2 className="mb-3 text-lg font-semibold text-text-primary">{t('settings.ai.title')}</h2>
      <form onSubmit={handleSave} className="rounded-lg border border-border bg-panel p-4">
        <label className="mb-1 block text-xs uppercase tracking-wide text-text-tertiary">
          {t('settings.ai.providerModeLabel')}
        </label>
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          className="mb-3 w-full rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue sm:w-64"
        >
          <option value="auto">{t('settings.ai.autoOption')}</option>
          <option value="claude_cli">{t('settings.ai.claudeCliOption')}</option>
          <option value="codex_cli">{t('settings.ai.codexCliOption')}</option>
          <option value="anthropic_api">{t('settings.ai.apiKeyOption')}</option>
        </select>

        <label className="mb-1 block text-xs uppercase tracking-wide text-text-tertiary">
          {t('settings.ai.apiKeyLabel')}
        </label>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder={
            config.has_api_key
              ? t('settings.ai.apiKeySetPlaceholder', {
                  source: config.api_key_source === 'settings' ? t('settings.ai.apiKeySourceSettings') : t('settings.ai.apiKeySourceEnv'),
                })
              : t('settings.ai.apiKeyUnsetPlaceholder')
          }
          className="mb-3 w-full rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue sm:w-96"
        />

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={saving}
            className="rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light disabled:opacity-50"
          >
            {saving ? t('settings.ai.saving') : t('settings.ai.save')}
          </button>
          {saved && <span className="text-sm text-success">{t('settings.ai.saved')}</span>}
        </div>
      </form>
    </div>
  )
}

function HostStatusSection() {
  const { t } = useTranslation()
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
      setResult({ error: err.message || t('settings.hostStatus.failed') })
    } finally {
      setChecking(false)
    }
  }

  if (machines.length === 0) return null

  return (
    <div>
      <h2 className="mb-3 text-lg font-semibold text-text-primary">{t('settings.hostStatus.title')}</h2>
      <div className="rounded-lg border border-border bg-panel p-4">
        <p className="mb-3 text-xs text-text-tertiary">{t('settings.hostStatus.description')}</p>
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
            {checking ? t('settings.hostStatus.checking') : t('settings.hostStatus.check')}
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
  const { t } = useTranslation()
  const [stats, setStats] = useState(null)

  useEffect(() => {
    api.stats().then(setStats).catch(() => {})
  }, [])

  if (!stats) return null

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary">{t('settings.stats.title')}</h2>
        <div className="flex items-center gap-3">
          <Link to="/tags" className="text-xs text-blue-light hover:underline">
            {t('settings.stats.manageTags')}
          </Link>
          <a
            href="/api/scripts/meta/export"
            download
            className="text-xs text-blue-light hover:underline"
          >
            {t('settings.stats.export')}
          </a>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg border border-border bg-panel p-4">
          <p className="text-2xl font-semibold text-text-primary">{stats.total_scripts}</p>
          <p className="text-xs text-text-tertiary">{t('settings.stats.totalScripts')}</p>
        </div>
        <div className="rounded-lg border border-border bg-panel p-4">
          <p className="text-2xl font-semibold text-text-primary">{stats.possible_secrets}</p>
          <p className="text-xs text-text-tertiary">{t('settings.stats.possibleSecrets')}</p>
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
  const { t } = useTranslation()
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
      setError(t('settings.account.passwordTooShort'))
      return
    }
    if (newPassword !== newPassword2) {
      setError(t('settings.account.passwordsDontMatch'))
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
      setError(err.message === 'Request failed: 401' ? t('settings.account.wrongCurrentPassword') : t('settings.account.changeFailed'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <h2 className="mb-3 text-lg font-semibold text-text-primary">{t('settings.account.title')}</h2>
      <form onSubmit={handleSubmit} className="grid gap-3 rounded-lg border border-border bg-panel p-4 sm:w-96">
        <input
          type="password"
          placeholder={t('settings.account.currentPasswordPlaceholder')}
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
          className="rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <input
          type="password"
          placeholder={t('settings.account.newPasswordPlaceholder')}
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          className="rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        <input
          type="password"
          placeholder={t('settings.account.repeatPasswordPlaceholder')}
          value={newPassword2}
          onChange={(e) => setNewPassword2(e.target.value)}
          className="rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
        />
        {error && <p className="text-sm text-warning">{error}</p>}
        {saved && <p className="text-sm text-success">{t('settings.account.changed')}</p>}
        <button
          type="submit"
          disabled={saving || !currentPassword || !newPassword}
          className="w-fit rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light disabled:opacity-50"
        >
          {saving ? t('settings.account.saving') : t('settings.account.changePassword')}
        </button>
      </form>
    </div>
  )
}

function AppLogSection() {
  const { t } = useTranslation()
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
        <h2 className="text-lg font-semibold text-text-primary">{t('settings.appLog.title')}</h2>
        <button
          type="button"
          onClick={reload}
          className="text-xs text-blue-light hover:underline"
        >
          {loading ? t('settings.appLog.refreshing') : t('settings.appLog.refresh')}
        </button>
      </div>
      <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-lg border border-border bg-panel p-4 font-mono text-xs text-text-secondary">
        {log || t('settings.appLog.noErrors')}
      </pre>
    </div>
  )
}

export default function Settings() {
  return (
    <div className="grid gap-8">
      <StatsSection />
      <ScheduleCheckSection />
      <OrphanedSection />
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
  const { t, lang } = useTranslation()
  const [entries, setEntries] = useState([])
  const PAGE_SIZE = 20
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)

  useEffect(() => {
    api.auditLog().then((r) => setEntries(r.entries)).catch(() => {})
  }, [])

  return (
    <div>
      <h2 className="mb-3 text-lg font-semibold text-text-primary">{t('settings.auditLog.title')}</h2>
      <div className="divide-y divide-border rounded-lg border border-border bg-panel">
        {entries.length === 0 && (
          <p className="p-4 text-sm text-text-tertiary">{t('settings.auditLog.noActivity')}</p>
        )}
        {entries.slice(0, visibleCount).map((e) => (
          <div key={e.id} className="p-3 text-sm">
            <span className="text-text-tertiary">{new Date(e.created_at).toLocaleString(lang === 'en' ? 'en-US' : 'sk-SK')}</span>
            {' — '}
            <span className="font-medium text-text-primary">{e.action}</span>
            {e.script_name && <span className="text-text-secondary"> {e.script_name}</span>}
            {e.detail && <span className="text-text-tertiary"> ({e.detail})</span>}
          </div>
        ))}
      </div>
      {visibleCount < entries.length && (
        <button
          type="button"
          onClick={() => setVisibleCount((v) => v + PAGE_SIZE)}
          className="mt-2 w-full rounded border border-border-strong py-2 text-sm text-text-secondary hover:border-blue hover:text-text-primary"
        >
          {t('scriptList.showMore', { count: Math.min(PAGE_SIZE, entries.length - visibleCount) })}
        </button>
      )}
    </div>
  )
}
