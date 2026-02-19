export type RegimeNow = {
  label: string
  score: number
  entry_allowed: boolean
  metrics?: Record<string, number | string>
}

export type OverviewKpi = {
  active_traders: number
  live_traders: number
  paper_traders: number
  net_pnl_24h_krw: number
  drift_warn_traders: number
}

export type EventRow = {
  event_id?: number
  ts: string
  trader_id?: number | null
  level: 'INFO' | 'WARN' | 'CRITICAL'
  event_type: string
  message?: string
}

export type TraderRow = {
  trader_id: number
  name: string
  mode: 'LIVE' | 'PAPER'
  live_armed: boolean
  container_status: 'RUNNING' | 'STOPPED' | 'ERROR' | 'NOT_CREATED' | string
  score_strategy: string
  risk_mode: string
  current_model_id?: number | null
  baseline_model_id?: number | null
  last_heartbeat_at?: string | null

  net_pnl_24h_krw?: number
  drift_state?: 'OK' | 'WARN' | 'ROLLBACK_TRIGGER' | string
  drift_streak?: number
}

export type OverviewResponse = {
  now_kst: string
  telegram_ok: boolean
  regime_now: RegimeNow
  kpi: OverviewKpi
  ranking: TraderRow[]
  recent_events: EventRow[]
}

export type TradersListResponse = {
  now_kst: string
  telegram_ok: boolean
  regime_now: RegimeNow
  traders: TraderRow[]
}

export type CreateTraderRequest = {
  name: string
  mode: 'LIVE' | 'PAPER'
  risk_mode: 'SAFE' | 'STANDARD' | 'PROFIT' | 'CRAZY'
  score_strategy: string
  krw_allocation_limit: number
}

export type ArmLiveRequest = {
  confirm_token?: string
}
