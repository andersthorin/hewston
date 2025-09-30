/**
 * API routing logic for BFF vs backend endpoint selection.
 *
 * This module provides routing logic that conditionally directs API calls
 * to BFF or backend endpoints based on feature flag configuration.
 */

import { featureFlagService } from '../services/featureFlags'
import type { EndpointGroup, FeatureFlagEvaluation } from '../types/featureFlags'

export interface ApiRouterOptions {
  /** Timeout for the request in milliseconds */
  timeout?: number
  /** Whether to allow fallback to backend on BFF failure */
  allowFallback?: boolean
  /** Additional headers to include */
  headers?: HeadersInit
}

/**
 * API Client Router for conditional endpoint selection.
 */
class APIClientRouter {
  /**
   * Route API call to BFF or backend based on feature flag configuration.
   */
  routeAPICall = async <T,>(
    endpointGroup: EndpointGroup,
    endpoint: string,
    options: RequestInit & ApiRouterOptions = {}
  ): Promise<T> => {
    const { allowFallback = false, timeout = 30000, ...requestOptions } = options
    const evaluation = featureFlagService.evaluateFeatureFlag(endpointGroup)

    // Log routing decision for debugging
    this.logEndpointRouting(endpoint, evaluation.source, endpointGroup)

    try {
      return await this.makeRequest<T>(evaluation, endpoint, requestOptions, timeout)
    } catch (error) {
      // No backend fallback: propagate BFF error immediately
      throw error
    }
  };

  /**
   * Get effective base URL for specific endpoint group.
   */
  getEffectiveBaseURL = (endpointGroup: EndpointGroup): string => {
    const evaluation = featureFlagService.evaluateFeatureFlag(endpointGroup)
    return this.extractBaseUrl(evaluation.endpointUrl)
  };

  /**
   * Handle fallback to backend when BFF fails.
   */


  /**
   * Make the actual HTTP request.
   */
  makeRequest = async <T,>(
    evaluation: FeatureFlagEvaluation,
    endpoint: string,
    requestOptions: RequestInit,
    timeout: number
  ): Promise<T> => {
    const baseUrl = this.extractBaseUrl(evaluation.endpointUrl)
    const fullUrl = this.buildFullUrl(baseUrl, endpoint, evaluation.source)

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeout)

    try {
      const response = await fetch(fullUrl, {
        ...requestOptions,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...requestOptions.headers,
        },
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      return await response.json()
    } finally {
      clearTimeout(timeoutId)
    }
  };

  /**
   * Build full URL based on endpoint and source.
   */
  buildFullUrl = (baseUrl: string, endpoint: string, source: 'bff' | 'backend'): string => {
    // Remove leading slash from endpoint if present
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint

    if (source === 'bff') {
      // BFF endpoints may need path transformation
      return this.transformBffEndpoint(baseUrl, cleanEndpoint)
    } else {
      // Backend endpoints use direct path
      return `${baseUrl}/${cleanEndpoint}`
    }
  };

  /**
   * Transform endpoint for BFF routing.
   */
  transformBffEndpoint = (baseUrl: string, endpoint: string): string => {
    // Map frontend endpoints to canonical BFF endpoints
    if (endpoint.startsWith('chart-data')) {
      // Preserve any tail (e.g. ?query)
      const tail = endpoint.slice('chart-data'.length)
      return `${baseUrl}/api/v1/chart-data${tail}`
    }

    // Map backend endpoints to BFF endpoints
    if (endpoint.startsWith('bars')) {
      return `${baseUrl}/api/v1/chart-data`
    } else if (endpoint.startsWith('backtests')) {
      // Handle list routes preserving query string
      if (endpoint === 'backtests' || endpoint.startsWith('backtests?')) {
        const tail = endpoint.slice('backtests'.length) // includes leading '?' if present
        return `${baseUrl}/api/v1/backtests${tail}`
      }
      // Transform backtests/{id}[/*] to canonical BFF endpoints
      const match = endpoint.match(/^backtests\/([^\/\?]+)(?:\/(.+))?$/)
      if (match) {
        const [, id, subpath] = match
        if (!subpath) {
          // Default detail → complete aggregate
          return `${baseUrl}/api/v1/backtests/${id}/complete`
        } else if (subpath === 'complete') {
          return `${baseUrl}/api/v1/backtests/${id}/complete`
        } else if (subpath === 'stream' || subpath === 'ws') {
          // Canonical WS path under backtests
          return `${baseUrl}/api/v1/backtests/${id}/stream`
        } else {
          // Pass through other subpaths under backtests
          return `${baseUrl}/api/v1/backtests/${id}/${subpath}`
        }
      }
      // Fallback: list
      return `${baseUrl}/api/v1/backtests`
    }


    // Default: pass through
    return `${baseUrl}/${endpoint}`
  };

  /**
   * Extract base URL from full endpoint URL.
   */
  extractBaseUrl = (endpointUrl: string): string => {
    try {
      const url = new URL(endpointUrl)
      return `${url.protocol}//${url.host}`
    } catch {
      // Fallback: assume it's already a base URL
      return endpointUrl
    }
  };

  /**
   * Get backend URL for specific endpoint group.
   */
  getBackendUrl = (endpointGroup: EndpointGroup): string => {
    const backendBase = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

    switch (endpointGroup) {
      case 'chartData':
        return `${backendBase}/bars`
      case 'runData':
        return `${backendBase}/backtests`
      case 'websocket':
        return `${backendBase}/backtests`
      default:
        return backendBase
    }
  };

  /**
   * Log endpoint routing decision for debugging.
   */
  logEndpointRouting = (
    endpoint: string,
    target: 'bff' | 'backend',
    endpointGroup: EndpointGroup,
    isFallback = false
  ): void => {
    if (featureFlagService.getConfiguration().bffEnabled || import.meta.env.VITE_FEATURE_FLAG_DEBUG) {
      const prefix = isFallback ? '🔄 FALLBACK' : '🎯 ROUTING'
      console.log(`${prefix} [${endpointGroup}] ${endpoint} → ${target.toUpperCase()}`)
    }
  };

  /**
   * Validate configuration and return any issues.
   */
  validateConfiguration = (): string[] => {
    return featureFlagService.validateConfiguration()
  };
}

// Export singleton instance
export const apiRouter = new APIClientRouter()

// Export class for testing
export { APIClientRouter }
