// Lightweight regex-based highlighter for the content block on script
// detail pages -- no new dependency, same philosophy as the hand-rolled
// diff.js already in this app (small, single-purpose, whole thing
// readable in one sitting instead of a black-box library).
//
// Recognizes, per line: line/inline comments, quoted strings, and
// "placeholder" tokens a reader needs to replace before running the
// command (IP addresses, <angle-bracket> placeholders) -- the two
// patterns that show up across virtually every cheatsheet/pentest entry
// (e.g. "192.168.1.10", "<BSSID>").
const TOKEN_RE = /(#.*)|('[^']*'|"[^"]*")|(<[^<>]+>)|(\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b)/g

const CLASS_BY_GROUP = {
  1: 'text-text-tertiary', // comment
  2: 'text-gold-soft', // quoted string
  3: 'text-warning', // <placeholder>
  4: 'text-warning', // IP[:port] placeholder
}

function highlightLine(line, lineKey) {
  const nodes = []
  let lastIndex = 0
  let match
  TOKEN_RE.lastIndex = 0
  while ((match = TOKEN_RE.exec(line))) {
    if (match.index > lastIndex) {
      nodes.push(line.slice(lastIndex, match.index))
    }
    const groupIndex = [1, 2, 3, 4].find((i) => match[i] !== undefined)
    nodes.push(
      <span key={`${lineKey}-${match.index}`} className={CLASS_BY_GROUP[groupIndex]}>
        {match[0]}
      </span>
    )
    lastIndex = match.index + match[0].length
  }
  if (lastIndex < line.length) nodes.push(line.slice(lastIndex))
  return nodes
}

export default function HighlightedContent({ content }) {
  const lines = content.split('\n')
  return (
    <>
      {lines.map((line, i) => (
        <div key={i}>{line.length > 0 ? highlightLine(line, i) : ' '}</div>
      ))}
    </>
  )
}
