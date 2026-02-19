import type { RegimeNow } from '../../types/dto'

export default function Topbar({
  nowKst,
  telegramOk,
  regimeNow,
  error
}: {
  nowKst: string
  telegramOk: boolean
  regimeNow: RegimeNow
  error: string | null
}) {
  return (
    <div className="topbar d-flex align-items-center px-3 px-lg-4">
      <div className="d-flex align-items-center gap-2">
        <div className="text-muted-2 small">Market Regime</div>
        <div className="badge badge-soft mono">
          {regimeNow.label} · {regimeNow.score}
        </div>
        {regimeNow.entry_allowed ? <span className="badge badge-run">ENTRY OK</span> : <span className="badge badge-err">ENTRY BLOCK</span>}
      </div>

      <div className="ms-auto d-flex align-items-center gap-2">
        <span className="badge badge-soft">{telegramOk ? 'TG OK' : 'TG FAIL'}</span>
        <span className="text-muted-2 small mono">{nowKst}</span>
        {error ? <span className="badge badge-stop">API</span> : null}
      </div>
    </div>
  )
}
