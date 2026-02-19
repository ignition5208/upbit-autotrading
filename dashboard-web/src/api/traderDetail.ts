import { apiFetch } from './client'
import type { RegimeNow, TraderRow, EventRow } from '../types/dto'

export type TraderDetailResponse = {
  now_kst: string
  telegram_ok: boolean
  regime_now: RegimeNow

  trader: TraderRow
  kpi: { net_today_krw: number; net_24h_krw: number; consecutive_losses: number }
  safety: {
    drift_state: 'OK' | 'WARN' | 'ROLLBACK_TRIGGER' | string
    drift_warn_streak: number
    risk_stop_until_ts?: string | null
    cooldown_until_ts?: string | null
    daily_loss_limit_pct?: number | null
  }

  latest_scan: { scan_id: string; ts: string } | null
  snapshots: Array<{
    scan_id: string
    symbol: string
    base_score: number
    final_score: number
    decision: string
    reason_summary: string
  }>

  recent_events: EventRow[]
}

export function getTraderDetail(traderId: number) {
  return apiFetch<TraderDetailResponse>(`/api/traders/${traderId}/detail`)
}
