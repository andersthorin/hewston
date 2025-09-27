/**
 * Feature flag types and configuration for BFF integration.
 * 
 * This module defines the TypeScript types for feature flag configuration
 * that controls BFF vs backend endpoint selection.
 */

/**
 * Feature flag configuration for BFF endpoint selection.
 */
export interface FeatureFlagConfiguration {
  /** Master toggle for BFF usage */
  bffEnabled: boolean
  /** Enable BFF chart data aggregation endpoint */
  chartDataEnabled: boolean
  /** Enable BFF run data aggregation endpoint */
  runDataEnabled: boolean
  /** Enable BFF WebSocket proxy */
  websocketEnabled: boolean
  /** Graceful fallback when BFF unavailable */
  fallbackToBackend: boolean
}

/**
 * Dynamic endpoint URL configuration based on feature flag state.
 */
export interface BFFEndpointConfiguration {
  /** Dynamic base URL (backend or BFF based on flags) */
  apiBaseUrl: string
  /** Dynamic WebSocket URL (backend or BFF based on flags) */
  wsBaseUrl: string
  /** Mapping of logical endpoints to actual URLs */
  endpointMappings: Record<string, string>
  /** Timeout configuration for different endpoint types */
  timeoutConfig: {
    api: number
    websocket: number
  }
}

/**
 * Endpoint groups for granular feature flag control.
 */
export type EndpointGroup = 'chartData' | 'runData' | 'websocket'

/**
 * Feature flag evaluation result.
 */
export interface FeatureFlagEvaluation {
  /** Whether the feature flag is enabled */
  enabled: boolean
  /** The effective endpoint URL to use */
  endpointUrl: string
  /** The source of the configuration (BFF or backend) */
  source: 'bff' | 'backend'
}

/**
 * Development tools integration for feature flag visibility.
 */
export interface FeatureFlagDebugInfo {
  /** Current feature flag configuration */
  configuration: FeatureFlagConfiguration
  /** Endpoint mappings for debugging */
  endpointMappings: Record<string, string>
  /** Last evaluation results */
  lastEvaluations: Record<EndpointGroup, FeatureFlagEvaluation>
  /** Timestamp of last configuration update */
  lastUpdated: number
}
