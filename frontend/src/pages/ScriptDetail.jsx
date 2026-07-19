import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../lib/api'

// Display-only masking (mirrors backend/app/secret_scan.py's heuristics
// loosely) -- hides likely secrets by default so a shoulder-surf or
// screenshot doesn't leak them, without needing the server to track
// which exact substrings matched. Never affects what's actually stored.
const SECRET_MASK_PATTERNS = [
  /((?:pass(?:word)?|passwd|pwd)\s*[:=]\s*['"])([^'"]{4,})(['"])/gi,
  /((?:token|api[_-]?key|secret|apikey)\s*[:=]\s*['"])([^'"]{6,})(['"])/gi,
  /(bot\d{6,}:)([a-zA-Z0-9_-]{20,})/gi,
  /(Bearer\s+)([a-zA-Z0-9._-]{10,})/gi,
]

function maskSecrets(content) {
  let masked = content
  for (const re of SECRET_MASK_PATTERNS) {
    masked = masked.replace(re, (...args) => {
      const groups = args.slice(1, -2)
      if (groups.length === 3) return `${groups[0]}••••••••${groups[2]}`
      return `${groups[0]}••••••••`
    })
  }
  return masked
}

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
  const [reviewError, setReviewError] = useState('')
  const [chatMessages, setChatMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatSending, setChatSending] = useState(false)
  const [sandboxAvailable, setSandboxAvailable] = useState(null)
  const [sandboxRunning, setSandboxRunning] = useState(false)
  const [sandboxResult, setSandboxResult] = useState(null)
  const [remoteExecEnabled, setRemoteExecEnabled] = useState(false)
  const [machines, setMachines] = useState([])
  const [remotePanelOpen, setRemotePanelOpen] = useState(false)
  const [remoteMachineId, setRemoteMachineId] = useState('')
  const [remoteSudoPassword, setRemoteSudoPassword] = useState('')
  const [remoteUseSudo, setRemoteUseSudo] = useState(false)
  const [remoteRunning, setRemoteRunning] = useState(false)
  const [remoteResult, setRemoteResult] = useState(null)
  const [useAdHoc, setUseAdHoc] = useState(false)
  const [adHoc, setAdHoc] = useState({
    host: '', port: 22, ssh_user: 'stanley', auth_type: 'key', ssh_key_path: '',
  })
  const [adHocSshPassword, setAdHocSshPassword] = useState('')
  const [adHocSaveName, setAdHocSaveName] = useState('')
  const [availableKeys, setAvailableKeys] = useState([])
  const [revealSecrets, setRevealSecrets] = useState(false)
  const [pushing, setPushing] = useState(false)
  const [pushResult, setPushResult] = useState(null)

  function reload() {
    api.getScript(id).then(setScript).catch(() => setError('Skript sa nenašiel.'))
  }

  useEffect(reload, [id])
  useEffect(() => setRevealSecrets(false), [id])
  useEffect(() => {
    api.aiStatus().then((s) => setAiAvailable(s.available)).catch(() => setAiAvailable(false))
    api.sandboxStatus().then((s) => setSandboxAvailable(s.available)).catch(() => setSandboxAvailable(false))
    api.settings().then((s) => setRemoteExecEnabled(s.remote_exec_enabled)).catch(() => {})
    api.machines().then((r) => {
      setMachines(r.machines)
      if (r.machines.length > 0) setRemoteMachineId(String(r.machines[0].id))
    }).catch(() => {})
    api.availableKeys().then((r) => {
      setAvailableKeys(r.keys)
      if (r.keys.length > 0) setAdHoc((a) => ({ ...a, ssh_key_path: r.keys[0] }))
    }).catch(() => {})
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
    setChatMessages([])
    try {
      const result = await api.aiReview(script.name, script.content)
      setChatMessages([{ role: 'assistant', text: result.review }])
    } catch {
      setReviewError('AI review zlyhal alebo nie je dostupný.')
    } finally {
      setReviewing(false)
    }
  }

  async function handleChatSend() {
    if (!chatInput.trim()) return
    const nextMessages = [...chatMessages, { role: 'user', text: chatInput.trim() }]
    setChatMessages(nextMessages)
    setChatInput('')
    setChatSending(true)
    try {
      const result = await api.aiChat(script.name, script.content, nextMessages)
      setChatMessages([...nextMessages, { role: 'assistant', text: result.reply }])
    } catch {
      setChatMessages([...nextMessages, { role: 'assistant', text: '(chyba -- odpoveď zlyhala)' }])
    } finally {
      setChatSending(false)
    }
  }

  function extractCodeBlock(text) {
    const match = text.match(/```[a-zA-Z]*\n([\s\S]*?)```/)
    return match ? match[1].trimEnd() : null
  }

  async function handleSaveAsNew(code) {
    const name = prompt('Meno pre nový skript:', `${script.name.replace(/\.sh$|\.py$/, '')}-upravene.sh`)
    if (!name) return
    const created = await api.importPaste({
      name,
      content: code,
      host: script.host,
      tags: script.tags,
      run_mode: script.run_mode,
      short_description: `Upravené cez AI chat z ${script.name}`,
      source_ref: `AI chat, pôvodne ${script.name}`,
    })
    navigate(`/scripts/${created.id}`)
  }

  async function handleReplaceContent(code) {
    if (!confirm('Nahradiť obsah tohto skriptu upravenou verziou z AI chatu?')) return
    await save('content', code)
    setChatMessages((msgs) => [...msgs, { role: 'assistant', text: '(obsah skriptu bol nahradený)' }])
  }

  async function handleAskAiToMoveSecrets() {
    const nextMessages = [
      ...chatMessages,
      {
        role: 'user',
        text: 'V skripte je natvrdo zapísané heslo/token. Prepíš ho tak, aby sa čítalo z premennej prostredia (napr. ${NAZOV:?chýba premenná NAZOV}), a v odpovedi mi napíš aj presný názov premennej, ktorú mám nastaviť.',
      },
    ]
    setChatMessages(nextMessages)
    setChatSending(true)
    try {
      const result = await api.aiChat(script.name, script.content, nextMessages)
      setChatMessages([...nextMessages, { role: 'assistant', text: result.reply }])
    } catch {
      setChatMessages([...nextMessages, { role: 'assistant', text: '(chyba -- odpoveď zlyhala)' }])
    } finally {
      setChatSending(false)
    }
  }

  async function handlePush() {
    setPushing(true)
    setPushResult(null)
    try {
      const result = await api.pushScript(id)
      setPushResult(result)
    } catch (err) {
      setPushResult({ error: err.message || 'Zápis na pôvodný stroj zlyhal.' })
    } finally {
      setPushing(false)
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

  async function handleRemoteExec() {
    setRemoteRunning(true)
    setRemoteResult(null)
    try {
      const payload = useAdHoc
        ? {
            connection: {
              ...adHoc,
              save_as_name: adHocSaveName.trim() || null,
            },
            sudo_password: remoteUseSudo ? remoteSudoPassword : null,
            ssh_password: adHoc.auth_type === 'password' ? adHocSshPassword : null,
          }
        : {
            machine_id: Number(remoteMachineId),
            sudo_password: remoteUseSudo ? remoteSudoPassword : null,
          }
      const result = await api.remoteExec(id, payload)
      setRemoteResult(result)
      if (result.saved_machine_id) {
        api.machines().then((r) => setMachines(r.machines)).catch(() => {})
      }
    } catch (err) {
      setRemoteResult({ error: err.message || 'Vzdialené spustenie zlyhalo.' })
    } finally {
      setRemoteRunning(false)
      setRemoteSudoPassword('')
      setAdHocSshPassword('')
    }
  }

  if (error) return <p className="text-warning">{error}</p>
  if (!script) return <p className="text-text-tertiary">Načítavam...</p>

  return (
    <div>
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">{script.name}</h1>
          <p className="mt-1 text-xs text-text-tertiary">
            {script.source_type === 'local_import' && `Import z ${script.source_ref}`}
            {script.source_type === 'remote_import' && `Stiahnuté z ${script.source_ref}`}
            {script.source_type === 'pasted' && 'Vložené ručne'}
            {script.source_ref && script.source_type === 'pasted' && ` · zdroj: ${script.source_ref}`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {script.source_type === 'remote_import' && remoteExecEnabled && (
            <button
              type="button"
              onClick={handlePush}
              disabled={pushing}
              title="Zapíše aktuálny obsah naspäť na pôvodné miesto na pôvodnom stroji."
              className="text-xs text-blue-light hover:underline disabled:opacity-50"
            >
              {pushing ? 'Posielam...' : '↑ Push naspäť'}
            </button>
          )}
          <button
            type="button"
            onClick={handleDelete}
            className="text-xs text-text-tertiary hover:text-warning"
          >
            Odstrániť z katalógu
          </button>
        </div>
      </div>
      {pushResult && (
        <p className={`mb-4 text-sm ${pushResult.error ? 'text-warning' : 'text-success'}`}>
          {pushResult.error || `Zapísané na ${pushResult.path} (${pushResult.duration_ms} ms)`}
        </p>
      )}

      {script.has_possible_secret && (
        <div className="mb-6 rounded border border-warning/40 bg-warning/10 px-3 py-2 text-sm text-warning">
          <p className="mb-2">
            Obsah tohto skriptu vyzerá, že obsahuje heslo alebo token natvrdo v tele. Nižšie je
            zobrazenie predvolene skryté. Zváž presun do premennej prostredia pred ďalším
            zdieľaním.
          </p>
          {aiAvailable && (
            <button
              type="button"
              onClick={handleAskAiToMoveSecrets}
              className="rounded border border-warning/40 px-2 py-1 text-xs text-warning hover:bg-warning/10"
            >
              Navrhni presun cez AI
            </button>
          )}
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
          {remoteExecEnabled && (
            <button
              type="button"
              onClick={() => {
                if (machines.length === 0) setUseAdHoc(true)
                setRemotePanelOpen((v) => !v)
              }}
              className="rounded border border-border-strong px-3 py-1 text-xs text-text-secondary hover:border-blue hover:text-text-primary"
            >
              Spustiť na diaľku
            </button>
          )}
          {!remoteExecEnabled && (
            <button
              type="button"
              disabled
              title="Zatiaľ vypnuté (SINDRI_REMOTE_EXEC_ENABLED=false). Pozri docs/REMOTE_EXEC.md."
              className="cursor-not-allowed rounded border border-border-strong px-3 py-1 text-xs text-text-tertiary opacity-50"
            >
              Spustiť na diaľku (vypnuté)
            </button>
          )}
        </div>
      </div>
      {script.has_possible_secret && (
        <button
          type="button"
          onClick={() => setRevealSecrets((v) => !v)}
          className="mb-2 text-xs text-blue-light hover:underline"
        >
          {revealSecrets ? 'Skryť heslá/tokeny' : 'Zobraziť aj s heslami/tokenmi'}
        </button>
      )}
      <pre className="overflow-x-auto rounded-lg border border-border bg-panel p-4 font-mono text-xs text-text-primary">
        {script.has_possible_secret && !revealSecrets ? maskSecrets(script.content) : script.content}
      </pre>

      {remotePanelOpen && (
        <div className="mt-4 rounded-lg border border-border bg-panel p-4">
          <h3 className="mb-3 text-xs uppercase tracking-wide text-text-tertiary">
            Spustiť na diaľku
          </h3>

          {machines.length > 0 && (
            <label className="mb-3 flex items-center gap-2 text-sm text-text-secondary">
              <input
                type="checkbox"
                checked={useAdHoc}
                onChange={(e) => setUseAdHoc(e.target.checked)}
              />
              Iný stroj (bez uloženého záznamu)
            </label>
          )}

          {!useAdHoc ? (
            <select
              value={remoteMachineId}
              onChange={(e) => setRemoteMachineId(e.target.value)}
              className="rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
            >
              {machines.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} ({m.ssh_user}@{m.host})
                </option>
              ))}
            </select>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                placeholder="Host (IP alebo hostname)"
                value={adHoc.host}
                onChange={(e) => setAdHoc((a) => ({ ...a, host: e.target.value }))}
                className="rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
              />
              <input
                placeholder="SSH user"
                value={adHoc.ssh_user}
                onChange={(e) => setAdHoc((a) => ({ ...a, ssh_user: e.target.value }))}
                className="rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
              />
              <input
                type="number"
                placeholder="Port"
                value={adHoc.port}
                onChange={(e) => setAdHoc((a) => ({ ...a, port: Number(e.target.value) }))}
                className="rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
              />
              <div className="flex items-center gap-4 text-sm text-text-secondary">
                <label className="flex items-center gap-1.5">
                  <input
                    type="radio"
                    checked={adHoc.auth_type === 'key'}
                    onChange={() => setAdHoc((a) => ({ ...a, auth_type: 'key' }))}
                  />
                  kľúč
                </label>
                <label className="flex items-center gap-1.5">
                  <input
                    type="radio"
                    checked={adHoc.auth_type === 'password'}
                    onChange={() => setAdHoc((a) => ({ ...a, auth_type: 'password' }))}
                  />
                  heslo
                </label>
              </div>

              {adHoc.auth_type === 'key' ? (
                <select
                  value={adHoc.ssh_key_path}
                  onChange={(e) => setAdHoc((a) => ({ ...a, ssh_key_path: e.target.value }))}
                  className="rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue sm:col-span-2"
                >
                  {availableKeys.map((k) => (
                    <option key={k} value={k}>
                      {k}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="password"
                  placeholder="SSH heslo (nikdy sa neukladá)"
                  value={adHocSshPassword}
                  onChange={(e) => setAdHocSshPassword(e.target.value)}
                  className="rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue sm:col-span-2"
                />
              )}

              <input
                placeholder="Uložiť medzi známe stroje ako (voliteľné meno)"
                value={adHocSaveName}
                onChange={(e) => setAdHocSaveName(e.target.value)}
                className="rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue sm:col-span-2"
              />
            </div>
          )}

          <label className="mt-3 flex items-center gap-2 text-sm text-text-secondary">
            <input
              type="checkbox"
              checked={remoteUseSudo}
              onChange={(e) => setRemoteUseSudo(e.target.checked)}
            />
            spustiť cez sudo
          </label>
          {remoteUseSudo && (
            <input
              type="password"
              placeholder="sudo heslo (nikdy sa neukladá, zadáva sa nanovo pri každom spustení)"
              value={remoteSudoPassword}
              onChange={(e) => setRemoteSudoPassword(e.target.value)}
              className="mt-3 w-full rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
            />
          )}
          <p className="mt-2 text-xs text-text-tertiary">
            Pozor: toto reálne spustí obsah skriptu na vybranom stroji. Ak sudo na cieľovom stroji
            vyžaduje fyzický hardvérový kľúč (napr. FIDO2), heslom sa to nepotvrdí — musíš byť pri
            stroji a dotknúť sa ho.
          </p>
          <button
            type="button"
            onClick={handleRemoteExec}
            disabled={remoteRunning || (useAdHoc ? !adHoc.host : !remoteMachineId)}
            className="mt-3 rounded bg-warning px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            {remoteRunning ? 'Spúšťam...' : 'Naozaj spustiť'}
          </button>
        </div>
      )}

      {remoteResult && (
        <div className="mt-4 rounded-lg border border-border bg-panel p-4">
          <h3 className="mb-2 text-xs uppercase tracking-wide text-text-tertiary">
            Výstup vzdialeného spustenia{' '}
            {remoteResult.exit_code != null && `(exit ${remoteResult.exit_code})`}
            {remoteResult.timed_out && ' — TIMEOUT'}
          </h3>
          {remoteResult.error || remoteResult.detail ? (
            <p className="text-sm text-warning">{remoteResult.error || remoteResult.detail}</p>
          ) : (
            <>
              {remoteResult.stdout && (
                <pre className="mb-2 overflow-x-auto whitespace-pre-wrap text-xs text-text-primary">{remoteResult.stdout}</pre>
              )}
              {remoteResult.stderr && (
                <pre className="overflow-x-auto whitespace-pre-wrap text-xs text-warning">{remoteResult.stderr}</pre>
              )}
            </>
          )}
        </div>
      )}

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
      {chatMessages.length > 0 && (
        <div className="mt-4 rounded-lg border border-border bg-panel p-4">
          <h3 className="mb-3 text-xs uppercase tracking-wide text-text-tertiary">AI review a rozhovor</h3>
          <div className="mb-3 grid gap-3">
            {chatMessages.map((m, i) => {
              const code = m.role === 'assistant' ? extractCodeBlock(m.text) : null
              return (
                <div
                  key={i}
                  className={`rounded p-3 text-sm ${
                    m.role === 'user' ? 'bg-fjord text-text-primary' : 'bg-ink text-text-primary'
                  }`}
                >
                  <p className="mb-1 text-[10px] uppercase tracking-wide text-text-tertiary">
                    {m.role === 'user' ? 'Ty' : 'AI'}
                  </p>
                  <p className="whitespace-pre-wrap">{m.text}</p>
                  {code && (
                    <div className="mt-2 flex gap-2">
                      <button
                        type="button"
                        onClick={() => handleReplaceContent(code)}
                        className="rounded bg-blue px-3 py-1 text-xs font-medium text-white hover:bg-blue-light"
                      >
                        Nahradiť obsah tohto skriptu
                      </button>
                      <button
                        type="button"
                        onClick={() => handleSaveAsNew(code)}
                        className="rounded border border-border-strong px-3 py-1 text-xs text-text-secondary hover:border-blue hover:text-text-primary"
                      >
                        Uložiť ako nový skript
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
          <div className="flex gap-2">
            <input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !chatSending && handleChatSend()}
              placeholder="Opýtaj sa AI na review, alebo popíš čo chceš upraviť..."
              className="flex-1 rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
            />
            <button
              type="button"
              onClick={handleChatSend}
              disabled={chatSending || !chatInput.trim()}
              className="rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light disabled:opacity-50"
            >
              {chatSending ? '...' : 'Poslať'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
