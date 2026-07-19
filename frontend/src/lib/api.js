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
    throw new Error(body.detail || `Request failed: ${res.status}`)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  login: (password) =>
    request('/auth/login', { method: 'POST', body: JSON.stringify({ password }) }),
  logout: () => request('/auth/logout', { method: 'POST' }),

  listScripts: ({ host, tags, q } = {}) => {
    const params = new URLSearchParams()
    if (host) params.set('host', host)
    for (const t of tags || []) params.append('tag', t)
    if (q) params.set('q', q)
    const qs = params.toString()
    return request(`/scripts${qs ? `?${qs}` : ''}`)
  },
  getScript: (id) => request(`/scripts/${id}`),
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

  hosts: () => request('/scripts/meta/hosts'),
  tags: () => request('/scripts/meta/tags'),
  settings: () => request('/settings'),

  aiStatus: () => request('/ai/status'),
  aiGenerate: (description) =>
    request('/ai/generate', { method: 'POST', body: JSON.stringify({ description }) }),
  aiReview: (name, content) =>
    request('/ai/review', { method: 'POST', body: JSON.stringify({ name, content }) }),

  sandboxStatus: () => request('/sandbox/status'),
  sandboxRun: (content, script_type) =>
    request('/sandbox/run', { method: 'POST', body: JSON.stringify({ content, script_type }) }),

  machines: () => request('/machines'),
  availableKeys: () => request('/machines/available-keys'),
  addMachine: (payload) => request('/machines', { method: 'POST', body: JSON.stringify(payload) }),
  deleteMachine: (id) => request(`/machines/${id}`, { method: 'DELETE' }),
  remoteExec: (scriptId, machine_id, sudo_password) =>
    request(`/scripts/${scriptId}/remote-exec`, {
      method: 'POST',
      body: JSON.stringify({ machine_id, sudo_password: sudo_password || null }),
    }),

  auditLog: () => request('/settings/audit-log'),
  stats: () => request('/settings/stats'),
}
