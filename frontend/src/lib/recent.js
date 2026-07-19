const KEY = 'sindri_recent_ids'
const MAX = 8

export function getRecentIds() {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function recordVisit(id) {
  try {
    const current = getRecentIds().filter((x) => x !== id)
    current.unshift(id)
    localStorage.setItem(KEY, JSON.stringify(current.slice(0, MAX)))
  } catch {
    // localStorage unavailable (private mode etc.) -- silently skip, not essential
  }
}
