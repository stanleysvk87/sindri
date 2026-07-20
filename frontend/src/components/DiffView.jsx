import { diffLines } from '../lib/diff'

export default function DiffView({ before, after }) {
  const lines = diffLines(before, after)
  return (
    <pre className="max-h-96 overflow-auto rounded border border-border bg-ink p-3 font-mono text-xs">
      {lines.map((l, i) => (
        <div
          key={i}
          className={
            l.type === 'add'
              ? 'bg-success/10 text-success'
              : l.type === 'remove'
                ? 'bg-warning/10 text-warning'
                : 'text-text-tertiary'
          }
        >
          {l.type === 'add' ? '+ ' : l.type === 'remove' ? '- ' : '  '}
          {l.line}
        </div>
      ))}
    </pre>
  )
}
