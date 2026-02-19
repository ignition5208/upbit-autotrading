import Badge from '../UI/Badge'
import type { TraderRow } from '../../types/dto'
import { fmtKrw } from '../../utils/format'
import { Link } from 'react-router-dom'

export default function TraderCard({
  t,
  onStart,
  onStop,
  onRecreate,
  onArm
}: {
  t: TraderRow
  onStart: (id: number) => void
  onStop: (id: number) => void
  onRecreate: (id: number) => void
  onArm: (id: number) => void
}) {
  return (
    <div className="card p-3">
      <div className="d-flex align-items-start justify-content-between">
        <div>
          <div className="d-flex align-items-center gap-2">
            <div className="h5 mb-0">
              <Link to={`/traders/${t.trader_id}`}>{t.name}</Link>
            </div>

            <Badge kind={t.mode}>{t.mode}</Badge>
            <Badge kind={t.container_status}>{t.container_status}</Badge>

            {t.mode === 'LIVE' ? (
              t.live_armed ? <Badge kind="RUNNING">ARMED</Badge> : <Badge kind="STOPPED">READY</Badge>
            ) : null}
          </div>

          <div className="text-muted-2 small mt-1">
            <span className="mono">#{t.trader_id}</span> · {t.score_strategy} · {t.risk_mode}
            · model <span className="mono">{t.current_model_id ?? '-'}</span>
            · baseline <span className="mono">{t.baseline_model_id ?? '-'}</span>
          </div>

          <div className="mt-2 d-flex flex-wrap gap-2">
            <span className="badge badge-soft">24h Net <span className="mono">{fmtKrw(t.net_pnl_24h_krw ?? 0)}</span></span>
            <Badge kind={t.drift_state ?? 'soft'}>{t.drift_state ?? 'OK'}</Badge>
            <span className="badge badge-soft">HB <span className="mono">{t.last_heartbeat_at ?? '-'}</span></span>
          </div>
        </div>

        <div className="d-flex flex-column gap-2">
          <div className="btn-group">
            <Link className="btn btn-sm badge-soft" to={`/traders/${t.trader_id}`}>Detail</Link>
            {t.container_status === 'RUNNING' ? (
              <button className="btn btn-sm badge-soft" onClick={() => onStop(t.trader_id)}>Stop</button>
            ) : (
              <button className="btn btn-sm badge-soft" onClick={() => onStart(t.trader_id)}>Start</button>
            )}
          </div>
          <div className="btn-group">
            <button className="btn btn-sm badge-soft" onClick={() => onRecreate(t.trader_id)}>Recreate</button>
            {t.mode === 'LIVE' ? (
              <button className="btn btn-sm badge-soft" onClick={() => onArm(t.trader_id)}>Arm Live</button>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}
