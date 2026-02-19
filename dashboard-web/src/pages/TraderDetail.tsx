import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import Badge from '../components/UI/Badge'
import { fmtKrw, fmtInt } from '../utils/format'
import { getTraderDetail, type TraderDetailResponse } from '../api/traderDetail'
import { startTrader, stopTrader, recreateTrader } from '../api/traders'

export default function TraderDetail() {
  const { id } = useParams()
  const traderId = Number(id)

  const [data, setData] = useState<TraderDetailResponse | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [tab, setTab] = useState<'overview'|'scores'|'orders'|'positions'|'safety'>('overview')

  async function refresh() {
    const d = await getTraderDetail(traderId)
    setData(d)
  }

  useEffect(() => {
    let mounted = true
    refresh()
      .then(() => mounted && setErr(null))
      .catch((e) => mounted && setErr((e as Error).message))

    const timer = window.setInterval(() => refresh().catch(() => void 0), 10_000)
    return () => {
      mounted = false
      window.clearInterval(timer)
    }
  }, [traderId])

  async function withAction(fn: () => Promise<void>) {
    try {
      await fn()
      await refresh()
    } catch (e) {
      setErr((e as Error).message)
    }
  }

  if (!Number.isFinite(traderId)) return <div className="card p-3">Invalid trader id</div>
  if (err) return <div className="card p-3">API Error: {err}</div>
  if (!data) return <div className="card p-3">Loading…</div>

  const t = data.trader

  return (
    <>
      <div className="d-flex align-items-end justify-content-between mb-3">
        <div>
          <div className="text-muted-2 small">Trader</div>
          <div className="h4 mb-0">
            {t.name} <span className="text-muted-2 mono">#{t.trader_id}</span>
          </div>
        </div>
        <div className="d-flex gap-2">
          <Link to="/traders" className="btn btn-sm badge-soft">Back</Link>
          <button className="btn btn-sm badge-soft" onClick={() => withAction(() => recreateTrader(traderId))}>Recreate</button>
        </div>
      </div>

      <div className="card p-3 mb-3">
        <div className="d-flex flex-wrap align-items-start justify-content-between gap-3">
          <div>
            <div className="d-flex align-items-center gap-2">
              <Badge kind={t.mode}>{t.mode}</Badge>
              <Badge kind={t.container_status}>{t.container_status}</Badge>
              <Badge kind="soft">{t.score_strategy}</Badge>
              <Badge kind="soft">{t.risk_mode}</Badge>

              {t.mode === 'LIVE' ? (
                t.live_armed ? <Badge kind="RUNNING">ARMED</Badge> : <Badge kind="STOPPED">READY</Badge>
              ) : null}
            </div>

            <div className="text-muted-2 small mt-2">
              current model <span className="mono">{t.current_model_id ?? '-'}</span> · baseline <span className="mono">{t.baseline_model_id ?? '-'}</span>
              · heartbeat <span className="mono">{t.last_heartbeat_at ?? '-'}</span>
            </div>

            <div className="mt-2 d-flex flex-wrap gap-2">
              <span className="badge badge-soft">Today net <span className="mono">{fmtKrw(data.kpi.net_today_krw)}</span> KRW</span>
              <span className="badge badge-soft">24h net <span className="mono">{fmtKrw(data.kpi.net_24h_krw)}</span> KRW</span>
              <span className="badge badge-soft">Consec loss <span className="mono">{fmtInt(data.kpi.consecutive_losses)}</span></span>
              <Badge kind={data.safety.drift_state === 'WARN' ? 'WARN' : data.safety.drift_state === 'ROLLBACK_TRIGGER' ? 'CRITICAL' : 'soft'}>
                {data.safety.drift_state}
              </Badge>
            </div>
          </div>

          <div className="d-flex flex-column gap-2">
            {t.container_status === 'RUNNING' ? (
              <button className="btn btn-sm badge-soft" onClick={() => withAction(() => stopTrader(traderId))}>Stop</button>
            ) : (
              <button className="btn btn-sm btn-accent" onClick={() => withAction(() => startTrader(traderId))}>Start</button>
            )}
          </div>
        </div>
      </div>

      <ul className="nav nav-tabs border-soft mb-3">
        {(['overview','scores','orders','positions','safety'] as const).map((k) => (
          <li className="nav-item" key={k}>
            <button className={`nav-link ${tab === k ? 'active' : ''}`} onClick={() => setTab(k)}>
              {k.toUpperCase()}
            </button>
          </li>
        ))}
      </ul>

      {tab === 'overview' ? (
        <div className="row g-3">
          <div className="col-12 col-lg-6">
            <div className="card p-3">
              <div className="fw-semibold mb-2">Current Regime</div>
              <div className="d-flex align-items-center gap-2">
                <span className="badge badge-soft mono">{data.regime_now.label} · {data.regime_now.score}</span>
                {data.regime_now.entry_allowed ? <Badge kind="RUNNING">ENTRY OK</Badge> : <Badge kind="ERROR">ENTRY BLOCK</Badge>}
              </div>
              <hr className="soft my-3" />
              <div className="table-responsive">
                <table className="table table-sm mb-0">
                  <tbody>
                    {Object.entries(data.regime_now.metrics ?? {}).map(([k,v]) => (
                      <tr key={k}>
                        <td className="text-muted-2">{k}</td>
                        <td className="mono text-end">{String(v)}</td>
                      </tr>
                    ))}
                    {(!data.regime_now.metrics || Object.keys(data.regime_now.metrics).length === 0) ? (
                      <tr><td className="text-muted-2">metrics</td><td className="mono text-end">-</td></tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="col-12 col-lg-6">
            <div className="card p-3">
              <div className="fw-semibold mb-2">Recent Alerts</div>
              <div className="d-flex flex-column gap-2" style={{ maxHeight: 360, overflow: 'auto' }}>
                {data.recent_events.map((e, idx) => (
                  <div key={`${e.event_type}-${idx}`} className="p-2 rounded-3 border border-soft bg-panel-2">
                    <div className="d-flex justify-content-between">
                      <div className="mono small">
                        <Badge kind={e.level}>{e.level}</Badge>
                        <span className="ms-1">{e.event_type}</span>
                      </div>
                      <div className="text-muted-2 small mono">{e.ts}</div>
                    </div>
                    <div className="text-muted-2 small mt-1">{e.message ?? ''}</div>
                  </div>
                ))}
                {data.recent_events.length === 0 ? (
                  <div className="text-muted-2 small">No events</div>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {tab === 'scores' ? (
        <div className="card p-3">
          <div className="d-flex align-items-center justify-content-between mb-2">
            <div className="fw-semibold">Latest Scan TopN</div>
            <div className="text-muted-2 small mono">
              scan: {data.latest_scan?.scan_id ?? '-'} · {data.latest_scan?.ts ?? '-'}
            </div>
          </div>

          <div className="table-responsive">
            <table className="table table-hover table-sm mb-0">
              <thead>
                <tr>
                  <th style={{ width: 140 }}>Scan</th>
                  <th style={{ width: 120 }}>Symbol</th>
                  <th style={{ width: 120 }} className="text-end">Base</th>
                  <th style={{ width: 120 }} className="text-end">Final</th>
                  <th style={{ width: 120 }}>Decision</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {data.snapshots.map((s, idx) => (
                  <tr key={`${s.symbol}-${idx}`}>
                    <td className="mono small">{s.scan_id}</td>
                    <td className="mono fw-semibold">{s.symbol}</td>
                    <td className="text-end mono">{s.base_score.toFixed(3)}</td>
                    <td className="text-end mono">{s.final_score.toFixed(3)}</td>
                    <td><span className="badge badge-soft">{s.decision}</span></td>
                    <td className="text-muted-2 small">{s.reason_summary}</td>
                  </tr>
                ))}
                {data.snapshots.length === 0 ? (
                  <tr><td colSpan={6} className="text-muted-2">No snapshots</td></tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {tab === 'orders' ? (
        <div className="card p-3">
          <div className="fw-semibold">Orders & Trades</div>
          <div className="text-muted-2 small mt-1">TODO</div>
        </div>
      ) : null}

      {tab === 'positions' ? (
        <div className="card p-3">
          <div className="fw-semibold">Positions</div>
          <div className="text-muted-2 small mt-1">TODO</div>
        </div>
      ) : null}

      {tab === 'safety' ? (
        <div className="row g-3">
          <div className="col-12 col-lg-6">
            <div className="card p-3">
              <div className="fw-semibold mb-2">Guardrails</div>
              <div className="table-responsive">
                <table className="table table-sm mb-0">
                  <tbody>
                    <tr><td className="text-muted-2">daily_loss_limit_pct</td><td className="mono text-end">{data.safety.daily_loss_limit_pct ?? '-'}</td></tr>
                    <tr><td className="text-muted-2">risk_stop_until</td><td className="mono text-end">{data.safety.risk_stop_until_ts ?? '-'}</td></tr>
                    <tr><td className="text-muted-2">cooldown_until</td><td className="mono text-end">{data.safety.cooldown_until_ts ?? '-'}</td></tr>
                    <tr><td className="text-muted-2">drift_warn_streak</td><td className="mono text-end">{fmtInt(data.safety.drift_warn_streak)}</td></tr>
                    <tr><td className="text-muted-2">drift_state</td><td className="mono text-end">{data.safety.drift_state}</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="col-12 col-lg-6">
            <div className="card p-3">
              <div className="fw-semibold mb-2">Policy</div>
              <div className="text-muted-2 small">
                AUTO_ROLLBACK: net_return_24h &lt; -2% 또는 drift_warn 3회 연속 또는 consec_loss ≥ 5
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}
