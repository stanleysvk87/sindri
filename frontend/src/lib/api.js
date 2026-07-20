async function request(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (res.status === 401) {
    const err = new Error('unauthorized')
    err.status = 401
    throw err
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const err = new Error(body.detail || `Request failed: ${res.status}`)
    err.status = res.status
    throw err
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  login: (password) =>
    request('/auth/login', { method: 'POST', body: JSON.stringify({ password }) }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  verifyPassword: (password) =>
    request('/auth/verify', { method: 'POST', body: JSON.stringify({ password }) }),

  listScripts: ({ host, tags, q, favorite, everywhere, secret } = {}) => {
    const params = new URLSearchParams()
    if (host) params.set('host', host)
    for (const t of tags || []) params.append('tag', t)
    if (q) params.set('q', q)
    if (favorite) params.set('favorite', 'true')
    if (everywhere) params.set('everywhere', 'true')
    if (secret) params.set('secret', 'true')
    const qs = params.toString()
    return request(`/scripts${qs ? `?${qs}` : ''}`)
  },
  getScript: (id) => request(`/scripts/${id}`),
  scriptHistory: (id, limit = 50) => request(`/scripts/${id}/history?limit=${limit}`),
  scriptVersions: (id) => request(`/scripts/${id}/versions`),
  getScriptVersion: (id, versionId) => request(`/scripts/${id}/versions/${versionId}`),
  restoreScriptVersion: (id, versionId) =>
    request(`/scripts/${id}/versions/${versionId}/restore`, { method: 'POST' }),
  updateScript: (id, fields) =>
    request(`/scripts/${id}`, { method: 'PATCH', body: JSON.stringify(fields) }),
  deleteScript: (id) => request(`/scripts/${id}`, { method: 'DELETE' }),

  importPaste: (payload) =>
    request('/scripts/import/paste', { method: 'POST', body: JSON.stringify(payload) }),
  scanPath: (path) =>
    request('/scripts/import/scan', { method: 'POST', body: JSON.stringify({ path }) }),
  confirmImport: (paths, host) =>
    request('/scripts/import/confirm', {
      method: 'POST',
      body: JSON.stringify({ paths, host }),
    }),

  remoteScan: (machine_id, path) =>
    request('/scripts/import/remote-scan', {
      method: 'POST',
      body: JSON.stringify({ machine_id, path }),
    }),
  remoteConfirmImport: (machine_id, host, items) =>
    request('/scripts/import/remote-confirm', {
      method: 'POST',
      body: JSON.stringify({ machine_id, host, items }),
    }),
  pushScript: (scriptId, { machine_id, target_path } = {}) =>
    request(`/scripts/${scriptId}/push`, {
      method: 'POST',
      body: JSON.stringify({ machine_id: machine_id ?? null, target_path: target_path ?? null }),
    }),
  rescanScript: (scriptId) => request(`/scripts/${scriptId}/rescan`, { method: 'POST' }),

  bulkTag: (ids, add, remove) =>
    request('/scripts/bulk-tag', { method: 'POST', body: JSON.stringify({ ids, add, remove }) }),
  renameTag: (oldTag, newTag) =>
    request('/scripts/tags/rename', { method: 'POST', body: JSON.stringify({ old: oldTag, new: newTag }) }),
  deleteTag: (tag) =>
    request('/scripts/tags/delete', { method: 'POST', body: JSON.stringify({ tag }) }),
  toggleFavorite: (id) => request(`/scripts/${id}/favorite`, { method: 'POST' }),
  duplicateScript: (id) => request(`/scripts/${id}/duplicate`, { method: 'POST' }),
  remoteExecAll: (scriptId, sudo_password) =>
    request(`/scripts/${scriptId}/remote-exec-all`, {
      method: 'POST',
      body: JSON.stringify({ sudo_password: sudo_password || null }),
    }),

  hosts: () => request('/scripts/meta/hosts'),
  tags: () => request('/scripts/meta/tags'),
  orphanedScripts: () => request('/scripts/meta/orphaned'),
  scheduleCheck: () => request('/scripts/meta/schedule-check'),
  settings: () => request('/settings'),

  aiStatus: () => request('/ai/status'),
  aiGenerate: (description) =>
    request('/ai/generate', { method: 'POST', body: JSON.stringify({ description }) }),
  aiReview: (name, content) =>
    request('/ai/review', { method: 'POST', body: JSON.stringify({ name, content }) }),
  aiChat: (name, content, messages) =>
    request('/ai/chat', { method: 'POST', body: JSON.stringify({ name, content, messages }) }),

  sandboxStatus: () => request('/sandbox/status'),
  sandboxRun: (content, script_type) =>
    request('/sandbox/run', { method: 'POST', body: JSON.stringify({ content, script_type }) }),

  machines: () => request('/machines'),
  availableKeys: () => request('/machines/available-keys'),
  addMachine: (payload) => request('/machines', { method: 'POST', body: JSON.stringify(payload) }),
  deleteMachine: (id) => request(`/machines/${id}`, { method: 'DELETE' }),
  remoteExec: (scriptId, { machine_id, connection, sudo_password, ssh_password }) =>
    request(`/scripts/${scriptId}/remote-exec`, {
      method: 'POST',
      body: JSON.stringify({
        machine_id: machine_id ?? null,
        connection: connection ?? null,
        sudo_password: sudo_password || null,
        ssh_password: ssh_password || null,
      }),
    }),

  auditLog: () => request('/settings/audit-log'),
  stats: () => request('/settings/stats'),
  aiConfig: () => request('/settings/ai'),
  updateAiConfig: (payload) =>
    request('/settings/ai', { method: 'PUT', body: JSON.stringify(payload) }),
  hostStatus: (machine_id) =>
    request('/settings/host-status', { method: 'POST', body: JSON.stringify({ machine_id }) }),
  appLog: (lines = 200) => request(`/settings/app-log?lines=${lines}`),
  updateAccountPassword: (current_password, new_password) =>
    request('/settings/account', {
      method: 'PUT',
      body: JSON.stringify({ current_password, new_password }),
    }),
}
