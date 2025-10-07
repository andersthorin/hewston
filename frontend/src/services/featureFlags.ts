/**
 * Feature flag service for BFF endpoint selection and configuration management.
 *
 * This service provides centralized feature flag evaluation and configuration
 * management for BFF vs backend endpoint selection.
 */

import type {
  FeatureFlagConfiguration,
  BFFEndpointConfiguration,
  EndpointGroup,
  FeatureFlagEvaluation,
  FeatureFlagDebugInfo,
} from '../types/featureFlags'

/**
 * Feature flag service for centralized configuration management.
 */
class FeatureFlagService {
  private configuration: FeatureFlagConfiguration
  private endpointConfig: BFFEndpointConfiguration
  private debugInfo: FeatureFlagDebugInfo

  constructor() {
    this.configuration = this.loadConfiguration()
    this.endpointConfig = this.buildEndpointConfiguration()
    this.debugInfo = this.initializeDebugInfo()

    // Expose debug info to browser console if enabled
    if (this.isDebugEnabled()) {
      this.exposeDebugInfo()
    }
  }

  /**
   * Load feature flag configuration from environment variables.
   */
  private loadConfiguration(): FeatureFlagConfiguration {
    return {
      bffEnabled: this.getEnvBoolean('VITE_BFF_ENABLED', true),
      chartDataEnabled: this.getEnvBoolean('VITE_BFF_CHART_DATA_ENABLED', true),
      runDataEnabled: this.getEnvBoolean('VITE_BFF_RUN_DATA_ENABLED', true),
      websocketEnabled: this.getEnvBoolean('VITE_BFF_WEBSOCKET_ENABLED', true),
      // Fallback is disabled by default and env-gated for emergencies only
      fallbackToBackend: this.getEnvBoolean('VITE_BFF_FALLBACK_ENABLED', false),
    }
  }

  /**
   * Build endpoint configuration based on feature flags.
   */
  private buildEndpointConfiguration(): BFFEndpointConfiguration {
    const backendUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
    const bffUrl = import.meta.env.VITE_BFF_BASE_URL || 'http://127.0.0.1:8001'
    const backendWsUrl = import.meta.env.VITE_WS_BASE_URL || 'ws://127.0.0.1:8000'
    const bffWsUrl = import.meta.env.VITE_BFF_WS_BASE_URL || 'ws://127.0.0.1:8001'

    return {
      apiBaseUrl: this.configuration.bffEnabled ? bffUrl : backendUrl,
      wsBaseUrl:
        this.configuration.bffEnabled && this.configuration.websocketEnabled
          ? bffWsUrl
          : backendWsUrl,
      endpointMappings: {
        // Chart data endpoints
        chartData:
          this.configuration.bffEnabled && this.configuration.chartDataEnabled
            ? `${bffUrl}/api/v1/chart-data`
            : `${backendUrl}/bars`,
        // Backtest data endpoints
        runData:
          this.configuration.bffEnabled && this.configuration.runDataEnabled
            ? `${bffUrl}/api/v1/backtests`
            : `${backendUrl}/backtests`,
        // WebSocket endpoints
        websocket:
          this.configuration.bffEnabled && this.configuration.websocketEnabled
            ? `${bffWsUrl}/api/v1/backtests/{id}/stream`
            : `${backendWsUrl}/backtests/{id}/ws`,
        // Health check
        health: `${backendUrl}/healthz`,
      },
      timeoutConfig: {
        api: 30000, // 30 seconds
        websocket: 5000, // 5 seconds
      },
    }
  }

  /**
   * Initialize debug information.
   */
  private initializeDebugInfo(): FeatureFlagDebugInfo {
    return {
      configuration: this.configuration,
      endpointMappings: this.endpointConfig.endpointMappings,
      lastEvaluations: {} as Record<EndpointGroup, FeatureFlagEvaluation>,
      lastUpdated: Date.now(),
    }
  }

  /**
   * Get environment variable as boolean with default value.
   */
  private getEnvBoolean(key: string, defaultValue: boolean): boolean {
    const value = import.meta.env[key]
    if (value === undefined || value === null) return defaultValue
    return value === 'true' || value === '1'
  }

  /**
   * Check if debug mode is enabled.
   */
  private isDebugEnabled(): boolean {
    return this.getEnvBoolean('VITE_FEATURE_FLAG_DEBUG', false)
  }

  /**
   * Expose debug information to browser console.
   */
  private exposeDebugInfo(): void {
    if (typeof window !== 'undefined') {
      ;(window as any).__FEATURE_FLAGS__ = this.debugInfo
      console.log('🎛️ Feature Flags Debug Info:', this.debugInfo)
    }
  }

  /**
   * Evaluate feature flag for specific endpoint group.
   */
  public evaluateFeatureFlag(flagName: EndpointGroup): FeatureFlagEvaluation {
    let enabled = false
    let endpointUrl = ''
    let source: 'bff' | 'backend' = 'backend'

    switch (flagName) {
      case 'chartData':
        enabled = this.configuration.bffEnabled && this.configuration.chartDataEnabled
        endpointUrl = this.endpointConfig.endpointMappings.chartData
        source = enabled ? 'bff' : 'backend'
        break
      case 'runData':
        enabled = this.configuration.bffEnabled && this.configuration.runDataEnabled
        endpointUrl = this.endpointConfig.endpointMappings.runData
        source = enabled ? 'bff' : 'backend'
        break
      case 'websocket':
        enabled = this.configuration.bffEnabled && this.configuration.websocketEnabled
        endpointUrl = this.endpointConfig.endpointMappings.websocket
        source = enabled ? 'bff' : 'backend'
        break
    }

    const evaluation: FeatureFlagEvaluation = { enabled, endpointUrl, source }

    // Update debug info
    this.debugInfo.lastEvaluations[flagName] = evaluation
    this.debugInfo.lastUpdated = Date.now()

    return evaluation
  }

  /**
   * Get endpoint configuration.
   */
  public getEndpointConfiguration(): BFFEndpointConfiguration {
    return this.endpointConfig
  }

  /**
   * Check if specific feature flag is enabled.
   */
  public isFeatureFlagEnabled(feature: EndpointGroup): boolean {
    return this.evaluateFeatureFlag(feature).enabled
  }

  /**
   * Get effective base URL for API requests.
   */
  public getEffectiveApiBaseUrl(): string {
    return this.endpointConfig.apiBaseUrl
  }

  /**
   * Get effective WebSocket base URL.
   */
  public getEffectiveWsBaseUrl(): string {
    return this.endpointConfig.wsBaseUrl
  }

  /**
   * Get current feature flag configuration.
   */
  public getConfiguration(): FeatureFlagConfiguration {
    return { ...this.configuration }
  }

  /**
   * Get debug information for development tools.
   */
  public getDebugInfo(): FeatureFlagDebugInfo {
    return { ...this.debugInfo }
  }

  /**
   * Validate configuration and return any issues.
   */
  public validateConfiguration(): string[] {
    const issues: string[] = []

    // Check if BFF URL is accessible when BFF is enabled
    if (this.configuration.bffEnabled) {
      const bffUrl = import.meta.env.VITE_BFF_BASE_URL
      if (!bffUrl) {
        issues.push('VITE_BFF_BASE_URL is required when BFF is enabled')
      }
    }

    // Check for conflicting configurations
    if (
      !this.configuration.bffEnabled &&
      (this.configuration.chartDataEnabled ||
        this.configuration.runDataEnabled ||
        this.configuration.websocketEnabled)
    ) {
      issues.push('Individual endpoint flags require VITE_BFF_ENABLED=true')
    }

    return issues
  }
}

// Export singleton instance
export const featureFlagService = new FeatureFlagService()

// Export class for testing
export { FeatureFlagService }
