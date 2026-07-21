import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { recordVisit } from '../lib/recent'
import { copyToClipboard } from '../lib/clipboard'
import { useTranslation } from '../i18n/I18nContext.jsx'
import DiffView from '../components/DiffView'

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

const ACTION_LABEL_KEYS = {
  create_paste: 'scriptDetail.actionLabels.createPaste',
  update: 'scriptDetail.actionLabels.update',
  delete: 'scriptDetail.actionLabels.delete',
  remote_exec: 'scriptDetail.actionLabels.remoteExec',
  push: 'scriptDetail.actionLabels.push',
  bulk_import: 'scriptDetail.actionLabels.bulkImport',
  remote_import: 'scriptDetail.actionLabels.remoteImport',
  restore_version: 'scriptDetail.actionLabels.restoreVersion',
}

const VERSION_SOURCE_LABEL_KEYS = {
  update: 'scriptDetail.versionSource.update',
  rescan: 'scriptDetail.versionSource.rescan',
  restore: 'scriptDetail.versionSource.restore',
}

function EditableField({ label, value, onSave, multiline = false, placeholder = '' }) {
  const { t } = useTranslation()
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value)

  useEffect(() => setDraft(value), [value])

  if (!editing) {
    return (
      <div className="mb-4 min-w-0">
        <div className="mb-1 flex items-center justify-between">
          <h3 className="text-xs uppercase tracking-wide text-text-tertiary">{label}</h3>
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="text-xs text-blue-light hover:underline"
          >
            {t('scriptDetail.editField')}
          </button>
        </div>
        <p className="whitespace-pre-wrap break-words text-sm text-text-primary">
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
          {t('common.save')}
        </button>
        <button
          type="button"
          onClick={() => {
            setDraft(value)
            setEditing(false)
          }}
          className="rounded border border-border-strong px-3 py-1 text-xs text-text-secondary"
        >
          {t('common.cancel')}
        </button>
      </div>
    </div>
  )
}

export default function ScriptDetail() {
  const { t, lang } = useTranslation()
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
  const [runAllRunning, setRunAllRunning] = useState(false)
  const [runAllResults, setRunAllResults] = useState(null)
  const [useAdHoc, setUseAdHoc] = useState(false)
  const [adHoc, setAdHoc] = useState({
    host: '', port: 22, ssh_user: '', auth_type: 'key', ssh_key_path: '',
  })
  const [adHocSshPassword, setAdHocSshPassword] = useState('')
  const [adHocSaveName, setAdHocSaveName] = useState('')
  const [availableKeys, setAvailableKeys] = useState([])
  const [revealSecrets, setRevealSecrets] = useState(false)
  const [revealPrompt, setRevealPrompt] = useState(false)
  const [revealPassword, setRevealPassword] = useState('')
  const [revealError, setRevealError] = useState('')
  const [revealChecking, setRevealChecking] = useState(false)
  const [pushing, setPushing] = useState(false)
  const [pushResult, setPushResult] = useState(null)
  const [rescanning, setRescanning] = useState(false)
  const [rescanResult, setRescanResult] = useState(null)
  const [rescanBefore, setRescanBefore] = useState(null)
  const [rescanDiffOpen, setRescanDiffOpen] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [versionsOpen, setVersionsOpen] = useState(false)
  const [versions, setVersions] = useState([])
  const [versionsLoading, setVersionsLoading] = useState(false)
  const [expandedVersionId, setExpandedVersionId] = useState(null)
  const [versionContents, setVersionContents] = useState({})
  const [sshCopyOpen, setSshCopyOpen] = useState(false)
  const [sshCopyMachineId, setSshCopyMachineId] = useState('')
  const [sshCopied, setSshCopied] = useState(false)

  function reload() {
    api
      .getScript(id)
      .then((s) => {
        setScript(s)
        recordVisit(s.id)
      })
      .catch(() => setError(t('scriptDetail.notFound')))
  }

  useEffect(reload, [id])
  useEffect(() => {
    setRevealSecrets(false)
    setRevealPrompt(false)
    setRevealPassword('')
    setRevealError('')
    setHistoryOpen(false)
    setHistory([])
    setVersionsOpen(false)
    setVersions([])
    setExpandedVersionId(null)
    setVersionContents({})
    setSshCopyOpen(false)
    setSshCopied(false)
    setRescanResult(null)
    setRescanBefore(null)
    setRescanDiffOpen(false)
    setPushResult(null)
    setRunAllResults(null)
  }, [id])
  useEffect(() => {
    api.aiStatus().then((s) => setAiAvailable(s.available)).catch(() => setAiAvailable(false))
    api.sandboxStatus().then((s) => setSandboxAvailable(s.available)).catch(() => setSandboxAvailable(false))
    api.settings().then((s) => setRemoteExecEnabled(s.remote_exec_enabled)).catch(() => {})
    api.machines().then((r) => {
      setMachines(r.machines)
      if (r.machines.length > 0) {
        setRemoteMachineId(String(r.machines[0].id))
        setSshCopyMachineId(String(r.machines[0].id))
      }
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

  async function handleToggleHistory() {
    if (historyOpen) {
      setHistoryOpen(false)
      return
    }
    setHistoryOpen(true)
    setHistoryLoading(true)
    try {
      const result = await api.scriptHistory(id)
      setHistory(result.entries)
    } catch {
      setHistory([])
    } finally {
      setHistoryLoading(false)
    }
  }

  async function handleToggleVersions() {
    if (versionsOpen) {
      setVersionsOpen(false)
      return
    }
    setVersionsOpen(true)
    setVersionsLoading(true)
    try {
      const result = await api.scriptVersions(id)
      setVersions(result.versions)
    } catch {
      setVersions([])
    } finally {
      setVersionsLoading(false)
    }
  }

  async function handleToggleVersionDiff(versionId) {
    if (expandedVersionId === versionId) {
      setExpandedVersionId(null)
      return
    }
    setExpandedVersionId(versionId)
    if (versionContents[versionId] == null) {
      const v = await api.getScriptVersion(id, versionId)
      setVersionContents((prev) => ({ ...prev, [versionId]: v.content }))
    }
  }

  async function handleRestoreVersion(versionId) {
    if (!confirm(t('scriptDetail.confirmRestoreVersion'))) return
    const updated = await api.restoreScriptVersion(id, versionId)
    setScript(updated)
    setExpandedVersionId(null)
    const result = await api.scriptVersions(id)
    setVersions(result.versions)
  }

  async function handleCopy() {
    await copyToClipboard(script.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  function buildSshCommand(machine, content) {
    const target = `${machine.ssh_user}@${machine.host}`
    const portFlag = machine.port && machine.port !== 22 ? ` -p ${machine.port}` : ''
    const keyFlag = machine.auth_type === 'key' && machine.ssh_key_path_host ? ` -i ${machine.ssh_key_path_host}` : ''
    return `ssh${keyFlag}${portFlag} ${target} 'bash -s' <<'SINDRI_SCRIPT'\n${content}\nSINDRI_SCRIPT`
  }

  function handleToggleSshCopy() {
    if (sshCopyOpen) {
      setSshCopyOpen(false)
      return
    }
    const matching = machines.find((m) => m.name === script.host)
    if (matching) setSshCopyMachineId(String(matching.id))
    setSshCopied(false)
    setSshCopyOpen(true)
  }

  async function handleCopySshCommand() {
    const machine = machines.find((m) => String(m.id) === sshCopyMachineId)
    if (!machine) return
    await copyToClipboard(buildSshCommand(machine, script.content))
    setSshCopied(true)
    setTimeout(() => setSshCopied(false), 1500)
  }

  async function handleDelete() {
    if (!confirm(t('scriptDetail.confirmDelete', { name: script.name }))) return
    await api.deleteScript(id)
    navigate('/')
  }

  async function handleToggleFavorite() {
    const result = await api.toggleFavorite(id)
    setScript((s) => ({ ...s, is_favorite: result.is_favorite }))
  }

  async function handleDuplicate() {
    const copy = await api.duplicateScript(id)
    navigate(`/scripts/${copy.id}`)
  }

  async function handleReview() {
    setReviewing(true)
    setReviewError('')
    setChatMessages([])
    try {
      const result = await api.aiReview(script.name, script.content)
      setChatMessages([{ role: 'assistant', text: result.review }])
    } catch {
      setReviewError(t('scriptDetail.reviewFailed'))
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
      setChatMessages([...nextMessages, { role: 'assistant', text: t('scriptDetail.chatFailed') }])
    } finally {
      setChatSending(false)
    }
  }

  function extractCodeBlock(text) {
    const match = text.match(/```[a-zA-Z]*\n([\s\S]*?)```/)
    return match ? match[1].trimEnd() : null
  }

  async function handleSaveAsNew(code) {
    const name = prompt(t('scriptDetail.promptSaveAsNewName'), `${script.name.replace(/\.sh$|\.py$/, '')}-upravene.sh`)
    if (!name) return
    const created = await api.importPaste({
      name,
      content: code,
      host: script.host,
      tags: script.tags,
      run_mode: script.run_mode,
      short_description: t('scriptDetail.saveAsNewShortDescription', { name: script.name }),
      source_ref: t('scriptDetail.saveAsNewSourceRef', { name: script.name }),
    })
    navigate(`/scripts/${created.id}`)
  }

  async function handleReplaceContent(code) {
    if (!confirm(t('scriptDetail.confirmReplaceContent'))) return
    await save('content', code)
    setChatMessages((msgs) => [...msgs, { role: 'assistant', text: t('scriptDetail.contentReplacedNote') }])
  }

  async function handleAskAiToMoveSecrets() {
    const nextMessages = [
      ...chatMessages,
      {
        role: 'user',
        text: t('scriptDetail.moveSecretsPrompt'),
      },
    ]
    setChatMessages(nextMessages)
    setChatSending(true)
    try {
      const result = await api.aiChat(script.name, script.content, nextMessages)
      setChatMessages([...nextMessages, { role: 'assistant', text: result.reply }])
    } catch {
      setChatMessages([...nextMessages, { role: 'assistant', text: t('scriptDetail.chatFailed') }])
    } finally {
      setChatSending(false)
    }
  }

  async function handleConfirmReveal(e) {
    e.preventDefault()
    setRevealError('')
    setRevealChecking(true)
    try {
      const result = await api.verifyPassword(revealPassword)
      if (result.ok) {
        setRevealSecrets(true)
        setRevealPrompt(false)
        setRevealPassword('')
      } else {
        setRevealError(t('scriptDetail.wrongPassword'))
      }
    } catch {
      setRevealError(t('scriptDetail.verifyFailed'))
    } finally {
      setRevealChecking(false)
    }
  }

  async function handlePush() {
    setPushing(true)
    setPushResult(null)
    try {
      const result = await api.pushScript(id)
      setPushResult(result)
    } catch (err) {
      setPushResult({ error: err.message || t('scriptDetail.pushFailed') })
    } finally {
      setPushing(false)
    }
  }

  async function handleRescan() {
    setRescanning(true)
    setRescanResult(null)
    setRescanDiffOpen(false)
    const before = script.content
    try {
      const result = await api.rescanScript(id)
      setScript(result.script)
      setRescanResult({ changed: result.changed })
      setRescanBefore(result.changed ? before : null)
    } catch (err) {
      setRescanResult({ error: err.message || t('scriptDetail.rescanFailed') })
    } finally {
      setRescanning(false)
    }
  }

  async function handleSandboxRun() {
    setSandboxRunning(true)
    setSandboxResult(null)
    try {
      const result = await api.sandboxRun(script.content)
      setSandboxResult(result)
    } catch {
      setSandboxResult({ error: t('scriptDetail.sandboxRunFailed') })
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
      setRemoteResult({ error: err.message || t('scriptDetail.remoteExecFailed') })
    } finally {
      setRemoteRunning(false)
      setRemoteSudoPassword('')
      setAdHocSshPassword('')
    }
  }

  async function handleRemoteExecAll() {
    setRunAllRunning(true)
    setRunAllResults(null)
    try {
      const result = await api.remoteExecAll(id, remoteUseSudo ? remoteSudoPassword : null)
      setRunAllResults(result.results)
    } catch (err) {
      setRunAllResults([{ machine_name: '?', error: err.message || t('scriptDetail.runAllFailed') }])
    } finally {
      setRunAllRunning(false)
      setRemoteSudoPassword('')
    }
  }

  if (error) return <p className="text-warning">{error}</p>
  if (!script) return <p className="text-text-tertiary">{t('scriptDetail.loading')}</p>

  // "cheatsheet"/"pentest" sú referenčné katalógy (príkaz + vysvetlenie,
  // nie automatizačný skript pre konkrétny stroj) -- SSH-copy/sandbox/
  // remote-exec tu nedáva zmysel a pri útočných príkazoch (napr. hydra,
  // Responder) je to zbytočné riziko na omylné kliknutie.
  const isReferenceEntry = ['cheatsheet', 'pentest'].includes(script.host)

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="flex flex-wrap items-center gap-2 text-xl font-semibold text-text-primary">
            <span>{isReferenceEntry ? '📖' : script.name.endsWith('.py') ? '🐍' : script.name.endsWith('.sh') ? '🐚' : '📄'}</span>
            <span className="min-w-0 break-words">{script.name}</span>
            <button
              type="button"
              onClick={handleToggleFavorite}
              title={script.is_favorite ? t('scriptDetail.removeFavorite') : t('scriptDetail.addFavorite')}
              className={`text-lg ${script.is_favorite ? 'text-warning' : 'text-text-tertiary hover:text-warning'}`}
            >
              {script.is_favorite ? '★' : '☆'}
            </button>
          </h1>
          <p className="mt-1 break-words text-xs text-text-tertiary">
            {script.source_type === 'local_import' && t('scriptDetail.sourceImportedFrom', { ref: script.source_ref })}
            {script.source_type === 'remote_import' && t('scriptDetail.sourceDownloadedFrom', { ref: script.source_ref })}
            {script.source_type === 'pasted' && t('scriptDetail.sourcePasted')}
            {script.source_ref && script.source_type === 'pasted' && t('scriptDetail.sourceRefSuffix', { ref: script.source_ref })}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {(script.source_type === 'local_import' ||
            (script.source_type === 'remote_import' && remoteExecEnabled)) && (
            <button
              type="button"
              onClick={handleRescan}
              disabled={rescanning}
              title={t('scriptDetail.restoreFromSourceTitle')}
              className="text-xs text-blue-light hover:underline disabled:opacity-50"
            >
              {rescanning ? t('scriptDetail.checkingSource') : t('scriptDetail.restoreFromSource')}
            </button>
          )}
          {script.source_type === 'remote_import' && remoteExecEnabled && (
            <button
              type="button"
              onClick={handlePush}
              disabled={pushing}
              title={t('scriptDetail.pushBackTitle')}
              className="text-xs text-blue-light hover:underline disabled:opacity-50"
            >
              {pushing ? t('scriptDetail.pushing') : t('scriptDetail.pushBack')}
            </button>
          )}
          <button
            type="button"
            onClick={handleDuplicate}
            className="text-xs text-blue-light hover:underline"
          >
            {t('scriptDetail.duplicate')}
          </button>
          <button
            type="button"
            onClick={handleDelete}
            className="text-xs text-text-tertiary hover:text-warning"
          >
            {t('scriptDetail.removeFromCatalog')}
          </button>
        </div>
      </div>
      {pushResult && (
        <p className={`mb-4 text-sm ${pushResult.error ? 'text-warning' : 'text-success'}`}>
          {pushResult.error || t('scriptDetail.pushedTo', { path: pushResult.path, ms: pushResult.duration_ms })}
        </p>
      )}
      {rescanResult && (
        <div className="mb-4">
          <p className={`text-sm ${rescanResult.error ? 'text-warning' : rescanResult.changed ? 'text-warning' : 'text-success'}`}>
            {rescanResult.error ||
              (rescanResult.changed
                ? t('scriptDetail.rescanChanged')
                : t('scriptDetail.rescanUnchanged'))}
            {rescanResult.changed && rescanBefore != null && (
              <button
                type="button"
                onClick={() => setRescanDiffOpen((v) => !v)}
                className="ml-2 text-xs text-blue-light hover:underline"
              >
                {rescanDiffOpen ? t('scriptDetail.hideChanges') : t('scriptDetail.showChanges')}
              </button>
            )}
          </p>
          {rescanDiffOpen && rescanBefore != null && (
            <div className="mt-2">
              <DiffView before={rescanBefore} after={script.content} />
            </div>
          )}
        </div>
      )}

      {script.has_possible_secret && (
        <div className="mb-6 rounded border border-warning/40 bg-warning/10 px-3 py-2 text-sm text-warning">
          <p className="mb-2">{t('scriptDetail.secretWarning')}</p>
          {aiAvailable && (
            <button
              type="button"
              onClick={handleAskAiToMoveSecrets}
              className="rounded border border-warning/40 px-2 py-1 text-xs text-warning hover:bg-warning/10"
            >
              {t('scriptDetail.suggestMoveViaAi')}
            </button>
          )}
        </div>
      )}

      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="min-w-0">
          <EditableField label={t('scriptDetail.machine')} value={script.host} onSave={(v) => save('host', v)} placeholder={t('scriptDetail.machinePlaceholder')} />
          <label className="-mt-2 flex items-center gap-1.5 text-xs text-text-secondary">
            <input
              type="checkbox"
              checked={!!script.works_everywhere}
              onChange={(e) => save('works_everywhere', e.target.checked)}
            />
            {t('scriptDetail.worksEverywhere')}
          </label>
        </div>
        <EditableField label={t('scriptDetail.runMode')} value={script.run_mode} onSave={(v) => save('run_mode', v)} placeholder={t('scriptDetail.runModePlaceholder')} />
        <EditableField label={t('scriptDetail.tags')} value={script.tags} onSave={(v) => save('tags', v)} placeholder={t('scriptDetail.tagsPlaceholder')} />
        <div className="mb-4 min-w-0">
          <h3 className="mb-1 text-xs uppercase tracking-wide text-text-tertiary">{t('scriptDetail.lastModified')}</h3>
          <p className="text-sm text-text-primary">{new Date(script.updated_at).toLocaleString(lang === 'en' ? 'en-US' : 'sk-SK')}</p>
        </div>
      </div>

      <EditableField
        label={t('scriptDetail.shortDescription')}
        value={script.short_description}
        onSave={(v) => save('short_description', v)}
        placeholder={t('scriptDetail.noShortDescription')}
      />
      <EditableField
        label={t('scriptDetail.longDescription')}
        value={script.long_description}
        onSave={(v) => save('long_description', v)}
        multiline
        placeholder={t('scriptDetail.noLongDescription')}
      />
      <EditableField
        label={t('scriptDetail.notes')}
        value={script.notes}
        onSave={(v) => save('notes', v)}
        multiline
        placeholder={t('scriptDetail.noNotes')}
      />

      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-xs uppercase tracking-wide text-text-tertiary">{t('scriptDetail.content')}</h3>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleCopy}
            className="rounded bg-blue px-3 py-1 text-xs font-medium text-white hover:bg-blue-light"
          >
            {copied ? t('scriptDetail.copied') : t('scriptDetail.copy')}
          </button>
          <button
            type="button"
            onClick={handleToggleHistory}
            className="rounded border border-border-strong px-3 py-1 text-xs text-text-secondary hover:border-blue hover:text-text-primary"
          >
            {t('scriptDetail.history')}
          </button>
          <button
            type="button"
            onClick={handleToggleVersions}
            className="rounded border border-border-strong px-3 py-1 text-xs text-text-secondary hover:border-blue hover:text-text-primary"
          >
            {t('scriptDetail.versions')}
          </button>
          {!isReferenceEntry && machines.length > 0 && (
            <button
              type="button"
              onClick={handleToggleSshCopy}
              title={t('scriptDetail.copyAsSshTitle')}
              className="rounded border border-border-strong px-3 py-1 text-xs text-text-secondary hover:border-blue hover:text-text-primary"
            >
              {t('scriptDetail.copyAsSsh')}
            </button>
          )}
          {aiAvailable && (
            <button
              type="button"
              onClick={handleReview}
              disabled={reviewing}
              className="rounded border border-border-strong px-3 py-1 text-xs text-text-secondary hover:border-blue hover:text-text-primary disabled:opacity-50"
            >
              {reviewing ? t('scriptDetail.aiChecking') : t('scriptDetail.checkViaAi')}
            </button>
          )}
          {!isReferenceEntry && sandboxAvailable && (
            <button
              type="button"
              onClick={handleSandboxRun}
              disabled={sandboxRunning}
              title={t('scriptDetail.sandboxTestTitle')}
              className="rounded border border-border-strong px-3 py-1 text-xs text-text-secondary hover:border-blue hover:text-text-primary disabled:opacity-50"
            >
              {sandboxRunning ? t('scriptDetail.sandboxRunning') : t('scriptDetail.sandboxTest')}
            </button>
          )}
          {!isReferenceEntry && remoteExecEnabled && (
            <button
              type="button"
              onClick={() => {
                if (machines.length === 0) setUseAdHoc(true)
                setRemotePanelOpen((v) => !v)
              }}
              className="rounded border border-border-strong px-3 py-1 text-xs text-text-secondary hover:border-blue hover:text-text-primary"
            >
              {t('scriptDetail.remoteRun')}
            </button>
          )}
          {!isReferenceEntry && !remoteExecEnabled && (
            <button
              type="button"
              disabled
              title={t('scriptDetail.remoteRunDisabledTitle')}
              className="cursor-not-allowed rounded border border-border-strong px-3 py-1 text-xs text-text-tertiary opacity-50"
            >
              {t('scriptDetail.remoteRunDisabled')}
            </button>
          )}
        </div>
      </div>
      {sshCopyOpen && (
        <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-border bg-panel p-3">
          <span className="text-xs text-text-secondary">{t('scriptDetail.targetMachine')}</span>
          <select
            value={sshCopyMachineId}
            onChange={(e) => setSshCopyMachineId(e.target.value)}
            className="rounded border border-border-strong bg-bg px-2 py-1 text-xs text-text-primary"
          >
            {machines.map((m) => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>
          <button
            type="button"
            onClick={handleCopySshCommand}
            className="rounded bg-blue px-3 py-1 text-xs font-medium text-white hover:bg-blue-light"
          >
            {sshCopied ? t('scriptDetail.copied') : t('scriptDetail.copyCommand')}
          </button>
          <span className="text-xs text-text-tertiary">{t('scriptDetail.sshCommandHint')}</span>
        </div>
      )}
      {script.has_possible_secret && (
        <button
          type="button"
          onClick={() => {
            if (revealSecrets) {
              setRevealSecrets(false)
            } else {
              setRevealError('')
              setRevealPassword('')
              setRevealPrompt(true)
            }
          }}
          className="mb-2 text-xs text-blue-light hover:underline"
        >
          {revealSecrets ? t('scriptDetail.hideSecrets') : t('scriptDetail.showWithSecrets')}
        </button>
      )}
      {revealPrompt && (
        <form
          onSubmit={handleConfirmReveal}
          className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-border bg-panel p-3"
        >
          <span className="text-xs text-text-secondary">{t('scriptDetail.enterPasswordConfirm')}</span>
          <input
            type="password"
            autoFocus
            value={revealPassword}
            onChange={(e) => setRevealPassword(e.target.value)}
            className="rounded border border-border-strong bg-bg px-2 py-1 text-xs text-text-primary"
          />
          <button
            type="submit"
            disabled={revealChecking || !revealPassword}
            className="rounded bg-blue-light px-3 py-1 text-xs font-medium text-bg disabled:opacity-50"
          >
            {revealChecking ? t('scriptDetail.verifying') : t('scriptDetail.confirm')}
          </button>
          <button
            type="button"
            onClick={() => {
              setRevealPrompt(false)
              setRevealPassword('')
              setRevealError('')
            }}
            className="rounded border border-border-strong px-3 py-1 text-xs text-text-secondary"
          >
            {t('common.cancel')}
          </button>
          {revealError && <span className="text-xs text-red-400">{revealError}</span>}
        </form>
      )}
      <pre className="overflow-x-auto rounded-lg border border-border bg-panel p-4 font-mono text-xs text-text-primary">
        {script.has_possible_secret && !revealSecrets ? maskSecrets(script.content) : script.content}
      </pre>

      {remotePanelOpen && (
        <div className="mt-4 rounded-lg border border-border bg-panel p-4">
          <h3 className="mb-3 text-xs uppercase tracking-wide text-text-tertiary">
            {t('scriptDetail.remoteRun')}
          </h3>

          {machines.length > 0 && (
            <label className="mb-3 flex items-center gap-2 text-sm text-text-secondary">
              <input
                type="checkbox"
                checked={useAdHoc}
                onChange={(e) => setUseAdHoc(e.target.checked)}
              />
              {t('scriptDetail.otherMachine')}
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
                placeholder={t('scriptDetail.hostPlaceholder')}
                value={adHoc.host}
                onChange={(e) => setAdHoc((a) => ({ ...a, host: e.target.value }))}
                className="rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
              />
              <input
                placeholder={t('scriptDetail.sshUserPlaceholder')}
                value={adHoc.ssh_user}
                onChange={(e) => setAdHoc((a) => ({ ...a, ssh_user: e.target.value }))}
                className="rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
              />
              <input
                type="number"
                placeholder={t('scriptDetail.portPlaceholder')}
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
                  {t('scriptDetail.keyAuthRadio')}
                </label>
                <label className="flex items-center gap-1.5">
                  <input
                    type="radio"
                    checked={adHoc.auth_type === 'password'}
                    onChange={() => setAdHoc((a) => ({ ...a, auth_type: 'password' }))}
                  />
                  {t('scriptDetail.passwordAuthRadio')}
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
                  placeholder={t('scriptDetail.sshPasswordPlaceholder')}
                  value={adHocSshPassword}
                  onChange={(e) => setAdHocSshPassword(e.target.value)}
                  className="rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue sm:col-span-2"
                />
              )}

              <input
                placeholder={t('scriptDetail.saveAsKnownMachinePlaceholder')}
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
            {t('scriptDetail.runViaSudo')}
          </label>
          {remoteUseSudo && (
            <input
              type="password"
              placeholder={t('scriptDetail.sudoPasswordPlaceholder')}
              value={remoteSudoPassword}
              onChange={(e) => setRemoteSudoPassword(e.target.value)}
              className="mt-3 w-full rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
            />
          )}
          <p className="mt-2 text-xs text-text-tertiary">{t('scriptDetail.sudoHardwareKeyWarning')}</p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={handleRemoteExec}
              disabled={remoteRunning || (useAdHoc ? !adHoc.host : !remoteMachineId)}
              className="rounded bg-warning px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
            >
              {remoteRunning ? t('scriptDetail.running') : t('scriptDetail.reallyRun')}
            </button>
            {!useAdHoc && machines.length > 1 && (
              <button
                type="button"
                onClick={handleRemoteExecAll}
                disabled={runAllRunning}
                title={t('scriptDetail.runOnAllTitle')}
                className="rounded border border-warning px-4 py-2 text-sm font-medium text-warning hover:bg-warning/10 disabled:opacity-50"
              >
                {runAllRunning ? t('scriptDetail.runningOnAll') : t('scriptDetail.runOnAll', { count: machines.length })}
              </button>
            )}
          </div>
        </div>
      )}

      {runAllResults && (
        <div className="mt-4 flex flex-col gap-3">
          {runAllResults.map((r, i) => (
            <div key={i} className="rounded-lg border border-border bg-panel p-4">
              <h3 className="mb-2 text-xs uppercase tracking-wide text-text-tertiary">
                {r.machine_name}{' '}
                {r.exit_code != null && t('scriptDetail.exitCode', { code: r.exit_code })}
                {r.timed_out && t('scriptDetail.timeout')}
              </h3>
              {r.error || r.detail ? (
                <p className="text-sm text-warning">{r.error || r.detail}</p>
              ) : (
                <>
                  {r.stdout && (
                    <pre className="mb-2 overflow-x-auto whitespace-pre-wrap text-xs text-text-primary">{r.stdout}</pre>
                  )}
                  {r.stderr && (
                    <pre className="overflow-x-auto whitespace-pre-wrap text-xs text-warning">{r.stderr}</pre>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      )}

      {remoteResult && (
        <div className="mt-4 rounded-lg border border-border bg-panel p-4">
          <h3 className="mb-2 text-xs uppercase tracking-wide text-text-tertiary">
            {t('scriptDetail.remoteOutputTitle')}{' '}
            {remoteResult.exit_code != null && t('scriptDetail.exitCode', { code: remoteResult.exit_code })}
            {remoteResult.timed_out && t('scriptDetail.timeout')}
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
            {t('scriptDetail.sandboxOutputTitle')} {sandboxResult.exit_code != null && t('scriptDetail.exitCode', { code: sandboxResult.exit_code })}
            {sandboxResult.timed_out && t('scriptDetail.timeout')}
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

      {historyOpen && (
        <div className="mt-4 rounded-lg border border-border bg-panel p-4">
          <h3 className="mb-3 text-xs uppercase tracking-wide text-text-tertiary">{t('scriptDetail.historyTitle')}</h3>
          {historyLoading && <p className="text-sm text-text-tertiary">{t('common.loading')}</p>}
          {!historyLoading && history.length === 0 && (
            <p className="text-sm text-text-tertiary">{t('scriptDetail.noHistory')}</p>
          )}
          {!historyLoading && history.length > 0 && (
            <div className="flex flex-col gap-2">
              {history.map((h) => (
                <div key={h.id} className="rounded bg-ink px-3 py-2 text-xs text-text-secondary">
                  {new Date(h.created_at).toLocaleString(lang === 'en' ? 'en-US' : 'sk-SK')} —{' '}
                  <span className="font-medium text-text-primary">{ACTION_LABEL_KEYS[h.action] ? t(ACTION_LABEL_KEYS[h.action]) : h.action}</span>
                  {h.detail && <span className="text-text-tertiary"> ({h.detail})</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {versionsOpen && (
        <div className="mt-4 rounded-lg border border-border bg-panel p-4">
          <h3 className="mb-3 text-xs uppercase tracking-wide text-text-tertiary">{t('scriptDetail.versionsTitle')}</h3>
          {versionsLoading && <p className="text-sm text-text-tertiary">{t('common.loading')}</p>}
          {!versionsLoading && versions.length === 0 && (
            <p className="text-sm text-text-tertiary">{t('scriptDetail.noVersions')}</p>
          )}
          {!versionsLoading && versions.length > 0 && (
            <div className="flex flex-col gap-2">
              {versions.map((v) => (
                <div key={v.id} className="rounded bg-ink px-3 py-2 text-xs text-text-secondary">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span>
                      {new Date(v.created_at).toLocaleString(lang === 'en' ? 'en-US' : 'sk-SK')} —{' '}
                      <span className="font-medium text-text-primary">
                        {VERSION_SOURCE_LABEL_KEYS[v.source] ? t(VERSION_SOURCE_LABEL_KEYS[v.source]) : v.source}
                      </span>{' '}
                      ({t('scriptDetail.versionLength', { count: v.content_length })})
                    </span>
                    <div className="flex gap-3">
                      <button
                        type="button"
                        onClick={() => handleToggleVersionDiff(v.id)}
                        className="text-blue-light hover:underline"
                      >
                        {expandedVersionId === v.id ? t('scriptDetail.hideChanges') : t('scriptDetail.showChanges')}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRestoreVersion(v.id)}
                        className="text-warning hover:underline"
                      >
                        {t('scriptDetail.restoreVersion')}
                      </button>
                    </div>
                  </div>
                  {expandedVersionId === v.id && (
                    <div className="mt-2">
                      {versionContents[v.id] == null ? (
                        <p className="text-text-tertiary">{t('common.loading')}</p>
                      ) : (
                        <DiffView before={versionContents[v.id]} after={script.content} />
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {reviewError && <p className="mt-3 text-sm text-warning">{reviewError}</p>}
      {chatMessages.length > 0 && (
        <div className="mt-4 rounded-lg border border-border bg-panel p-4">
          <h3 className="mb-3 text-xs uppercase tracking-wide text-text-tertiary">{t('scriptDetail.reviewAndChat')}</h3>
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
                    {m.role === 'user' ? t('scriptDetail.you') : t('scriptDetail.ai')}
                  </p>
                  <p className="whitespace-pre-wrap">{m.text}</p>
                  {code && (
                    <div className="mt-2 flex gap-2">
                      <button
                        type="button"
                        onClick={() => handleReplaceContent(code)}
                        className="rounded bg-blue px-3 py-1 text-xs font-medium text-white hover:bg-blue-light"
                      >
                        {t('scriptDetail.replaceContent')}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleSaveAsNew(code)}
                        className="rounded border border-border-strong px-3 py-1 text-xs text-text-secondary hover:border-blue hover:text-text-primary"
                      >
                        {t('scriptDetail.saveAsNew')}
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
              placeholder={t('scriptDetail.chatPlaceholder')}
              className="flex-1 rounded border border-border-strong bg-ink px-3 py-2 text-sm text-text-primary outline-none focus:border-blue"
            />
            <button
              type="button"
              onClick={handleChatSend}
              disabled={chatSending || !chatInput.trim()}
              className="rounded bg-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-light disabled:opacity-50"
            >
              {chatSending ? t('scriptDetail.sending') : t('scriptDetail.send')}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
