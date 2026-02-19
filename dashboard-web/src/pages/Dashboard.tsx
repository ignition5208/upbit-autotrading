import { useEffect, useState } from 'react'
import { getOverview } from '../api/overview'
import type { OverviewResponse } from '../types/dto'
import KpiCard from '../components/UI/KpiCard'
import Badge from '../components/UI/Badge'
import { fmtKrw, fmtInt } from '../utils/format'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const [data, setData] = useState<OverviewResponse | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    getOverview()
      .then((o) => {
        if (!mounted) return
        setData(o)
        setErr(null)
      })
      .catch((e) => setErr((e as Error).message))
    const id = window.setInterval(() => {
      getOverview().then((o) => mounted && setData(o)).catch(() => void 0)
    }, 10_000)
    return () => {
      mounted = false
      window.clearInterval(id)
    }
  }, [])

  if (err) return <div className="card p-3">API Error: {err}</div>
  if (!data) return <div className="card p-3">Loading…</div>

  return (
    <>
      <div className="d-flex align-items-end justify-content-between mb-3">
        <div>
          <div className="text-muted-2 small">Overview</div>
          <div className="h4 mb-0">Dashboard</div>
        </div>
        <div className="d-flex gap-2">
          <Link to="/traders" className="btn btn-sm btn-accent">Manage Traders</Link>
          <Link to="/events" className="btn btn-sm badge-soft">View Events</Link>
        </div>
      </div>

      <div className="row g-3">
        <div className="col-12 col-md-3">
          <KpiCard
            title="Active Traders"
            value={fmtInt(data.kpi.active_traders)}
            footer={
              <div className="d-flex gap-2">
                <Badge kind="LIVE">LIVE {fmtInt(data.kpi.live_traders)}</Badge>
                <Badge kind="PAPER">PAPER {fmtInt(data.kpi.paper_traders)}</Badge>
              </div>
            }
          />
        </div>
        <div className="col-12 col-md-3">
          <KpiCard title="24h Net PnL" value={`${fmtKrw(data.kpi.net_pnl_24h_krw)} KRW`} sub="Sum of traders (net)" />
        </div>
        <div className="col-12 col-md-3">
          <KpiCard title="Drift WARN" value={fmtInt(data.kpi.drift_warn_traders)} sub="streak tracked" />
        </div>
        <div className="col-12 col-md-3">
          <KpiCard title="Current Regime" value={data.regime_now.label} sub={`score: ${data.regime_now.score}`} />
        </div>
      </div>

      <div className="row g-3 mt-1">
        <div className="col-12 col-lg-7">
          <div className="card p-3">
            <div className="d-flex align-items-center justify-content-between mb-2">
              <div className="fw-semibold">Trader Ranking (24h)</div>
              <Link to="/traders" className="small">See all</Link>
            </div>
            <div className="table-responsive">
              <table className="table table-hover table-sm mb-0">
                <thead>
                  <tr>
                    <th style={{ width: 80 }}>ID</th>
                    <th>Trader</th>
                    <th style={{ width: 90 }}>Mode</th>
                    <th style={{ width: 120 }}>Status</th>
                    <th style={{ width: 140 }} className="text-end">24h Net</th>
                    <th style={{ width: 100 }} className="text-end">Drift</th>
                  </tr>
                </thead>
                <tbody>
                  {data.ranking.map((t) => (
                    <tr key={t.trader_id}>
                      <td className="mono">{t.trader_id}</td>
                      <td>
                        <div className="fw-semibold">
                          <Link to={`/traders/${t.trader_id}`}>{t.name}</Link>
                        </div>
                        <div className="text-muted-2 small">
                          {t.score_strategy} · {t.risk_mode} · model <span className="mono">{t.current_model_id ?? '-'}</span>
                        </div>
                      </td>
                      <td><Badge kind={t.mode}>{t.mode}</Badge></td>
                      <td>
                        <Badge kind={t.container_status}>{t.container_status}</Badge>
                        {t.mode === 'LIVE' ? (
                          t.live_armed ? <span className="ms-1"><Badge kind="RUNNING">ARMED</Badge></span>
                                      : <span className="ms-1"><Badge kind="STOPPED">READY</Badge></span>
                        ) : null}
                      </td>
                      <td className="text-end mono">{fmtKrw(t.net_pnl_24h_krw ?? 0)}</td>
                      <td className="text-end">
                        <Badge kind={t.drift_state ?? 'soft'}>{t.drift_state ?? 'OK'}</Badge>
                      </td>
                    </tr>
                  ))}
                  {data.ranking.length === 0 ? (
                    <tr><td colSpan={6} className="text-muted-2">No traders yet</td></tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="col-12 col-lg-5">
          <div className="card p-3">
            <div className="d-flex align-items-center justify-content-between mb-2">
              <div className="fw-semibold">Alerts Feed</div>
              <Link to="/events" className="small">All events</Link>
            </div>
            <div className="d-flex flex-column gap-2" style={{ maxHeight: 420, overflow: 'auto' }}>
              {data.recent_events.map((e, idx) => (
                <div key={`${e.event_type}-${idx}`} className="p-2 rounded-3 border border-soft bg-panel-2">
                  <div className="d-flex justify-content-between">
                    <div className="mono small">
                      <Badge kind={e.level}>{e.level}</Badge>
                      <span className="ms-1">{e.event_type}</span>
                    </div>
                    <div className="text-muted-2 small mono">{e.ts}</div>
                  </div>
                  <div className="text-muted-2 small mt-1">
                    {e.trader_id ? `trader ${e.trader_id} · ` : ''}{e.message ?? ''}
                  </div>
                </div>
              ))}
              {data.recent_events.length === 0 ? (
                <div className="text-muted-2 small">No events</div>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
