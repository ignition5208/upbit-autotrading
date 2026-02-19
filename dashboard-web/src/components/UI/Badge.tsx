export default function Badge({ kind, children }: { kind: string; children: React.ReactNode }) {
  const cls =
    kind === 'LIVE' ? 'badge badge-live'
    : kind === 'PAPER' ? 'badge badge-paper'
    : kind === 'RUNNING' ? 'badge badge-run'
    : kind === 'STOPPED' ? 'badge badge-stop'
    : kind === 'ERROR' ? 'badge badge-err'
    : kind === 'WARN' ? 'badge badge-stop'
    : kind === 'CRITICAL' ? 'badge badge-err'
    : kind === 'soft' ? 'badge badge-soft'
    : 'badge badge-soft'
  return <span className={cls}>{children}</span>
}
