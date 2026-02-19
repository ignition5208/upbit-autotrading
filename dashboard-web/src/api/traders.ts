import { apiFetch } from './client'
import type { TradersListResponse, CreateTraderRequest, ArmLiveRequest } from '../types/dto'

export function listTraders() {
  return apiFetch<TradersListResponse>('/api/traders')
}

export function createTrader(body: CreateTraderRequest) {
  return apiFetch<{ trader_id: number }>('/api/traders', { method: 'POST', body: JSON.stringify(body) })
}

export function startTrader(traderId: number) {
  return apiFetch<void>(`/api/traders/${traderId}/start`, { method: 'POST' })
}

export function stopTrader(traderId: number) {
  return apiFetch<void>(`/api/traders/${traderId}/stop`, { method: 'POST' })
}

export function recreateTrader(traderId: number) {
  return apiFetch<void>(`/api/traders/${traderId}/recreate`, { method: 'POST' })
}

export function armLive(traderId: number, body: ArmLiveRequest) {
  return apiFetch<void>(`/api/traders/${traderId}/arm_live`, { method: 'POST', body: JSON.stringify(body) })
}
