/**
 * Backtest data hooks (BFF-only).
 *
 * Canonical backtests endpoints only. No legacy "runs" support.
 */

import { useQuery, useMutation, useQueryClient, type UseQueryResult } from '@tanstack/react-query'
import { backtestDataService, type BFFAggregatedBacktestResponse, type BFFBacktestListResponse } from '../services/runData'
import { featureFlagService } from '../services/featureFlags'
import type { BacktestListQuery, CreateBacktestRequest, CreateBacktestResponse } from '../services/api'

export function useBacktestList(
  query: BacktestListQuery = {},
  enabled: boolean = true
): UseQueryResult<BFFBacktestListResponse, Error> {
  const useBFF = featureFlagService.isFeatureFlagEnabled('runData')
  return useQuery({
    queryKey: ['backtests', 'list', query, useBFF ? 'bff' : 'backend'],
    queryFn: () => backtestDataService.listBacktests(query),
    enabled,
    staleTime: 10 * 1000,
    gcTime: 5 * 60 * 1000,
    refetchOnWindowFocus: true,
    refetchInterval: (q) => {
      const items = (q.state.data as any)?.items || []
      const hasActive = Array.isArray(items) && items.some((it: any) => {
        const s = String(it?.status || '').toUpperCase()
        return s !== 'DONE' && s !== 'COMPLETED' && s !== 'ERROR' && s !== 'FAILED'
      })
      return hasActive ? 2000 : false
    },
  })
}

export function useBacktestDetail(
  backtest_id: string | undefined,
  enabled: boolean = true
): UseQueryResult<BFFAggregatedBacktestResponse, Error> {
  const useBFF = featureFlagService.isFeatureFlagEnabled('runData')
  return useQuery({
    queryKey: ['backtests', 'complete', backtest_id, useBFF ? 'bff' : 'backend'],
    queryFn: () => backtestDataService.getCompleteBacktest(backtest_id!),
    enabled: enabled && !!backtest_id,
    staleTime: 5 * 1000,
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: true,
    refetchInterval: (q) => {
      const s = String((q.state.data as any)?.status || '').toUpperCase()
      const terminal = s === 'DONE' || s === 'COMPLETED' || s === 'ERROR' || s === 'FAILED'
      return terminal ? false : 1000
    },
  })
}

export function useCreateBacktest() {
  const queryClient = useQueryClient()
  const useBFF = featureFlagService.isFeatureFlagEnabled('runData')

  return useMutation({
    mutationFn: ({ request, idempotencyKey }: { request: CreateBacktestRequest; idempotencyKey?: string }) =>
      backtestDataService.createBacktest(request, idempotencyKey),

    onSuccess: (data: CreateBacktestResponse & { backtest_id?: string }) => {
      queryClient.invalidateQueries({ queryKey: ['backtests', 'list'] })
      const id = (data as any).backtest_id
      if (id) {
        queryClient.prefetchQuery({
          queryKey: ['backtests', 'complete', id, useBFF ? 'bff' : 'backend'],
          queryFn: () => backtestDataService.getCompleteBacktest(id),
          staleTime: 2 * 60 * 1000,
        })
      }
    },
  })
}

export function useBacktestMetrics(backtest_id: string | undefined, enabled: boolean = true) {
  const result = useBacktestDetail(backtest_id, enabled)
  return { ...result, data: result.data?.metrics || null, isAggregated: result.data?.meta?.aggregated || false }
}

export function useBacktestEquity(backtest_id: string | undefined, enabled: boolean = true) {
  const result = useBacktestDetail(backtest_id, enabled)
  return { ...result, data: result.data?.equity || null, isAggregated: result.data?.meta?.aggregated || false }
}

export function useBacktestOrders(backtest_id: string | undefined, enabled: boolean = true) {
  const result = useBacktestDetail(backtest_id, enabled)
  return { ...result, data: result.data?.orders || null, isAggregated: result.data?.meta?.aggregated || false }
}

export function useBacktestDataMetrics() {
  const metrics = backtestDataService.getPerformanceMetrics()
  const debugInfo = featureFlagService.getDebugInfo()
  return {
    ...metrics,
    featureFlags: {
      bffEnabled: debugInfo.configuration.bffEnabled,
      runDataEnabled: debugInfo.configuration.runDataEnabled,
    },
    lastEvaluations: debugInfo.lastEvaluations.runData,
    isUsingAggregation: backtestDataService.isUsingAggregation(),
  }
}

export function useIsBacktestDataBFF(): boolean {
  return featureFlagService.isFeatureFlagEnabled('runData')
}
