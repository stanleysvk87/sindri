// navigator.clipboard only exists in secure contexts (HTTPS or
// localhost) -- undefined when this app is reached over plain HTTP on
// a LAN IP, which is exactly how it's normally accessed before/without
// Caddy+HTTPS in front of it. Falls back to the legacy
// execCommand('copy') approach, which still works in insecure contexts.
export async function copyToClipboard(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.focus()
  textarea.select()
  try {
    const ok = document.execCommand('copy')
    if (!ok) throw new Error('execCommand copy failed')
  } finally {
    document.body.removeChild(textarea)
  }
}
