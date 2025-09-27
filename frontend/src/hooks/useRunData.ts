/**
 * Run data hooks with BFF integration and feature flag support.
 * 
 * These hooks provide a unified interface for fetching run data that
 * automatically routes to BFF or backend based on feature flag configuration.
 */

import { useQuery, useMutation, useQueryClient, type UseQueryResult } from '@tanstack/react-query'
import { 
  runDataService, 
  type BFFAggregatedRunResponse, 
  type BFFRunListResponse 
} from '../services/runData'
import { featureFlagService } from '../services/featureFlags'
import type { ListRunsQuery, CreateRunRequest, CreateRunResponse } from '../services/api'

/**
 * Hook for listing runs with BFF integration.
 */
export function useRunList(
  query: ListRunsQuery = {},
  enabled: boolean = true
): UseQueryResult<BFFRunListResponse, Error> {
  const useBFF = featureFlagService.isFeatureFlagEnabled('runData')
  
  return useQuery({
    queryKey: ['runs', 'list', query, useBFF ? 'bff' : 'backend'],
    queryFn: () => runDataService.listRuns(query),
    enabled,
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Hook for fetching complete run data with BFF aggregation.
 */
export function useCompleteRunData(
  run_id: string | undefined,
  enabled: boolean = true
): UseQueryResult<BFFAggregatedRunResponse, Error> {
  const useBFF = featureFlagService.isFeatureFlagEnabled('runData')
  
  return useQuery({
    queryKey: ['runs', 'complete', run_id, useBFF ? 'bff' : 'backend'],
    queryFn: () => runDataService.getCompleteRunData(run_id!),
    enabled: enabled && !!run_id,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000,   // 10 minutes
  })
}

/**
 * Hook for creating runs with BFF integration.
 */
export function useCreateRun() {
  const queryClient = useQueryClient()
  const useBFF = featureFlagService.isFeatureFlagEnabled('runData')
  
  return useMutation({
    mutationFn: ({ request, idempotencyKey }: { 
      request: CreateRunRequest
      idempotencyKey?: string 
    }) => runDataService.createRun(request, idempotencyKey),
    
    onSuccess: (data: CreateRunResponse) => {
      // Invalidate run list queries to refresh the list
      queryClient.invalidateQueries({ queryKey: ['runs', 'list'] })
      
      // Optionally prefetch the new run data
      queryClient.prefetchQuery({
        queryKey: ['runs', 'complete', data.run_id, useBFF ? 'bff' : 'backend'],
        queryFn: () => runDataService.getCompleteRunData(data.run_id),
        staleTime: 2 * 60 * 1000,
      })
    },
  })
}

/**
 * Hook for getting run data performance metrics.
 */
export function useRunDataMetrics() {
  const metrics = runDataService.getPerformanceMetrics()
  const debugInfo = featureFlagService.getDebugInfo()
  
  return {
    ...metrics,
    featureFlags: {
      bffEnabled: debugInfo.configuration.bffEnabled,
      runDataEnabled: debugInfo.configuration.runDataEnabled,
    },
    lastEvaluations: debugInfo.lastEvaluations.runData,
    isUsingAggregation: runDataService.isUsingAggregation(),
  }
}

/**
 * Hook for checking if run data is using BFF aggregation.
 */
export function useIsRunDataBFF(): boolean {
  return featureFlagService.isFeatureFlagEnabled('runData')
}

/**
 * Legacy compatibility hooks - these maintain the same interface as the original hooks
 * but internally use the new BFF-aware services.
 */

/**
 * Legacy hook for run list - maintains backward compatibility.
 */
export function useBacktestList(
  query: ListRunsQuery = {},
  enabled: boolean = true
) {
  const result = useRunList(query, enabled)
  
  // Transform BFF response to legacy format for backward compatibility
  return {
    ...result,
    data: result.data ? {
      items: result.data.items.map(item => ({
        run_id: item.run_id,
        created_at: item.created_at,
        strategy_id: item.strategy_id,
        status: item.status,
        symbol: item.symbol,
        run_from: item.run_from,
        run_to: item.run_to,
        duration_ms: item.duration_ms,
      })),
      total: result.data.total,
      limit: result.data.limit,
      offset: result.data.offset,
    } : undefined,
  }
}

/**
 * Legacy hook for run detail - maintains backward compatibility.
 */
export function useRunDetail(
  run_id: string | undefined,
  enabled: boolean = true
) {
  const result = useCompleteRunData(run_id, enabled)
  
  // Transform BFF response to legacy format for backward compatibility
  return {
    ...result,
    data: result.data ? {
      run_id: result.data.run_id,
      dataset_id: result.data.dataset_id,
      strategy_id: result.data.strategy_id,
      status: result.data.status,
      code_hash: result.data.code_hash,
      seed: result.data.seed,
      speed: result.data.speed,
      duration_ms: result.data.duration_ms,
      params: result.data.params,
      slippage_fees: result.data.slippage_fees,
      run_from: result.data.run_from,
      run_to: result.data.run_to,
      // Legacy format doesn't include aggregated data
      artifacts: null,
      manifest: null,
    } : undefined,
  }
}

/**
 * Hook for accessing aggregated run metrics (BFF-specific).
 */
export function useRunMetrics(
  run_id: string | undefined,
  enabled: boolean = true
) {
  const result = useCompleteRunData(run_id, enabled)
  
  return {
    ...result,
    data: result.data?.metrics || null,
    isAggregated: result.data?.meta?.aggregated || false,
  }
}

/**
 * Hook for accessing aggregated equity curve data (BFF-specific).
 */
export function useRunEquity(
  run_id: string | undefined,
  enabled: boolean = true
) {
  const result = useCompleteRunData(run_id, enabled)
  
  return {
    ...result,
    data: result.data?.equity || null,
    isAggregated: result.data?.meta?.aggregated || false,
  }
}

/**
 * Hook for accessing aggregated orders data (BFF-specific).
 */
export function useRunOrders(
  run_id: string | undefined,
  enabled: boolean = true
) {
  const result = useCompleteRunData(run_id, enabled)
  
  return {
    ...result,
    data: result.data?.orders || null,
    isAggregated: result.data?.meta?.aggregated || false,
  }
}

/**
 * Hook for creating backtests - maintains backward compatibility.
 */
export function useCreateBacktest() {
  const createRunMutation = useCreateRun()
  
  return {
    ...createRunMutation,
    mutate: (variables: { request: CreateRunRequest; idempotencyKey?: string }) =>
      createRunMutation.mutate(variables),
    mutateAsync: (variables: { request: CreateRunRequest; idempotencyKey?: string }) =>
      createRunMutation.mutateAsync(variables),
  }
}
