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
  public async routeAPICall<T>(
    endpointGroup: EndpointGroup,
    endpoint: string,
    options: RequestInit & ApiRouterOptions = {}
  ): Promise<T> {
    const { allowFallback = true, timeout = 30000, ...requestOptions } = options
    const evaluation = featureFlagService.evaluateFeatureFlag(endpointGroup)
    
    // Log routing decision for debugging
    this.logEndpointRouting(endpoint, evaluation.source, endpointGroup)
    
    try {
      return await this.makeRequest<T>(evaluation, endpoint, requestOptions, timeout)
    } catch (error) {
      // Attempt fallback if enabled and we were using BFF
      if (allowFallback && evaluation.source === 'bff') {
        console.warn(`BFF request failed for ${endpoint}, falling back to backend:`, error)
        return await this.handleFallback<T>(endpointGroup, endpoint, requestOptions, timeout)
      }
      throw error
    }
  }

  /**
   * Get effective base URL for specific endpoint group.
   */
  public getEffectiveBaseURL(endpointGroup: EndpointGroup): string {
    const evaluation = featureFlagService.evaluateFeatureFlag(endpointGroup)
    return this.extractBaseUrl(evaluation.endpointUrl)
  }

  /**
   * Handle fallback to backend when BFF fails.
   */
  private async handleFallback<T>(
    endpointGroup: EndpointGroup,
    endpoint: string,
    requestOptions: RequestInit,
    timeout: number
  ): Promise<T> {
    // Force backend evaluation
    const backendUrl = this.getBackendUrl(endpointGroup)
    const fallbackEvaluation: FeatureFlagEvaluation = {
      enabled: false,
      endpointUrl: backendUrl,
      source: 'backend'
    }
    
    this.logEndpointRouting(endpoint, 'backend', endpointGroup, true)
    return await this.makeRequest<T>(fallbackEvaluation, endpoint, requestOptions, timeout)
  }

  /**
   * Make the actual HTTP request.
   */
  private async makeRequest<T>(
    evaluation: FeatureFlagEvaluation,
    endpoint: string,
    requestOptions: RequestInit,
    timeout: number
  ): Promise<T> {
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
  }

  /**
   * Build full URL based on endpoint and source.
   */
  private buildFullUrl(baseUrl: string, endpoint: string, source: 'bff' | 'backend'): string {
    // Remove leading slash from endpoint if present
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint
    
    if (source === 'bff') {
      // BFF endpoints may need path transformation
      return this.transformBffEndpoint(baseUrl, cleanEndpoint)
    } else {
      // Backend endpoints use direct path
      return `${baseUrl}/${cleanEndpoint}`
    }
  }

  /**
   * Transform endpoint for BFF routing.
   */
  private transformBffEndpoint(baseUrl: string, endpoint: string): string {
    // Map backend endpoints to BFF endpoints
    if (endpoint.startsWith('bars')) {
      return `${baseUrl}/api/v1/chart-data`
    } else if (endpoint.startsWith('backtests')) {
      // Transform /backtests/{id} to /api/v1/runs/{id}/complete for aggregated data
      const match = endpoint.match(/^backtests\/([^\/]+)(?:\/(.+))?$/)
      if (match) {
        const [, id, subpath] = match
        if (!subpath) {
          return `${baseUrl}/api/v1/runs/${id}/complete`
        } else if (subpath === 'ws') {
          return `${baseUrl}/api/v1/runs/${id}/stream`
        }
      }
      return `${baseUrl}/api/v1/runs`
    }
    
    // Default: pass through
    return `${baseUrl}/${endpoint}`
  }

  /**
   * Extract base URL from full endpoint URL.
   */
  private extractBaseUrl(endpointUrl: string): string {
    try {
      const url = new URL(endpointUrl)
      return `${url.protocol}//${url.host}`
    } catch {
      // Fallback: assume it's already a base URL
      return endpointUrl
    }
  }

  /**
   * Get backend URL for specific endpoint group.
   */
  private getBackendUrl(endpointGroup: EndpointGroup): string {
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
  }

  /**
   * Log endpoint routing decision for debugging.
   */
  private logEndpointRouting(
    endpoint: string, 
    target: 'bff' | 'backend', 
    endpointGroup: EndpointGroup,
    isFallback = false
  ): void {
    if (featureFlagService.getConfiguration().bffEnabled || import.meta.env.VITE_FEATURE_FLAG_DEBUG) {
      const prefix = isFallback ? '🔄 FALLBACK' : '🎯 ROUTING'
      console.log(`${prefix} [${endpointGroup}] ${endpoint} → ${target.toUpperCase()}`)
    }
  }

  /**
   * Validate configuration and return any issues.
   */
  public validateConfiguration(): string[] {
    return featureFlagService.validateConfiguration()
  }
}

// Export singleton instance
export const apiRouter = new APIClientRouter()

// Export class for testing
export { APIClientRouter }
