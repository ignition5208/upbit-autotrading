export function fmtInt(n?: number | null) {
  if (n === null || n === undefined) return '-'
  return new Intl.NumberFormat('ko-KR').format(Math.trunc(n))
}

export function fmtKrw(n?: number | null) {
  if (n === null || n === undefined) return '-'
  return `${new Intl.NumberFormat('ko-KR').format(Math.round(n))}`
}
