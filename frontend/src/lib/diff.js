// Small, dependency-free line diff (classic LCS backtrack). Catalog
// scripts are at most a few hundred lines, so the O(n*m) DP table is
// cheap -- no need to pull in a diff library for this.
export function diffLines(before, after) {
  const a = before.split('\n')
  const b = after.split('\n')
  const n = a.length
  const m = b.length

  const lcs = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0))
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      lcs[i][j] = a[i] === b[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1])
    }
  }

  const result = []
  let i = 0
  let j = 0
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      result.push({ type: 'equal', line: a[i] })
      i++
      j++
    } else if (lcs[i + 1][j] >= lcs[i][j + 1]) {
      result.push({ type: 'remove', line: a[i] })
      i++
    } else {
      result.push({ type: 'add', line: b[j] })
      j++
    }
  }
  while (i < n) {
    result.push({ type: 'remove', line: a[i] })
    i++
  }
  while (j < m) {
    result.push({ type: 'add', line: b[j] })
    j++
  }
  return result
}
