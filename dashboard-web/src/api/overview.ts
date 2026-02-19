import { apiFetch } from './client'
import type { OverviewResponse } from '../types/dto'

export function getOverview() {
  return apiFetch<OverviewResponse>('/api/overview')
}
