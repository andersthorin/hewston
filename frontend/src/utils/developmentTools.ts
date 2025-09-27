/**
 * Development tools integration for feature flag visibility and debugging.
 * 
 * This module provides development tools integration to make feature flag
 * state and endpoint routing visible for debugging purposes.
 */

import { featureFlagService } from '../services/featureFlags'
import { apiRouter } from './apiRouter'
import type { FeatureFlagDebugInfo } from '../types/featureFlags'

/**
 * Configuration status for validation.
 */
export interface ConfigurationStatus {
  /** Whether configuration is valid */
  valid: boolean
  /** List of configuration issues */
  issues: string[]
  /** Configuration summary */
  summary: {
    bffEnabled: boolean
    activeEndpoints: string[]
    fallbackAvailable: boolean
  }
}

/**
 * Development tools integration for feature flags.
 */
class DevelopmentToolsIntegration {
  private isInitialized = false

  /**
   * Initialize development tools integration.
   */
  public initialize(): void {
    if (this.isInitialized || !this.isDevelopmentMode()) {
      return
    }

    this.exposeFeatureFlagState()
    this.setupConsoleCommands()
    this.logInitializationInfo()
    
    this.isInitialized = true
  }

  /**
   * Expose feature flag state to browser console.
   */
  public exposeFeatureFlagState(): void {
    if (typeof window === 'undefined') return

    const debugInfo = featureFlagService.getDebugInfo()
    
    // Expose to global window object
    ;(window as any).__FEATURE_FLAGS__ = debugInfo
    ;(window as any).__FEATURE_FLAG_SERVICE__ = featureFlagService
    ;(window as any).__API_ROUTER__ = apiRouter

    // Update debug info periodically
    setInterval(() => {
      ;(window as any).__FEATURE_FLAGS__ = featureFlagService.getDebugInfo()
    }, 5000)
  }

  /**
   * Log endpoint routing decisions.
   */
  public logEndpointRouting(endpoint: string, target: 'bff' | 'backend'): void {
    if (!this.isDevelopmentMode()) return

    const timestamp = new Date().toISOString()
    const emoji = target === 'bff' ? '🚀' : '🔧'
    
    console.log(`${emoji} [${timestamp}] API Route: ${endpoint} → ${target.toUpperCase()}`)
  }

  /**
   * Validate configuration and return status.
   */
  public validateConfiguration(): ConfigurationStatus {
    const issues = [
      ...featureFlagService.validateConfiguration(),
      ...apiRouter.validateConfiguration(),
    ]

    const config = featureFlagService.getConfiguration()
    const activeEndpoints: string[] = []

    if (config.chartDataEnabled) activeEndpoints.push('chartData')
    if (config.runDataEnabled) activeEndpoints.push('runData')
    if (config.websocketEnabled) activeEndpoints.push('websocket')

    return {
      valid: issues.length === 0,
      issues,
      summary: {
        bffEnabled: config.bffEnabled,
        activeEndpoints,
        fallbackAvailable: config.fallbackToBackend,
      },
    }
  }

  /**
   * Setup console commands for debugging.
   */
  private setupConsoleCommands(): void {
    if (typeof window === 'undefined') return

    // Add helper functions to window
    ;(window as any).__FF_HELP__ = () => {
      console.log(`
🎛️ Feature Flags Debug Commands:

__FEATURE_FLAGS__           - Current feature flag state
__FF_STATUS__()            - Configuration validation status
__FF_TOGGLE__(flag)        - Toggle feature flag (dev only)
__FF_RESET__()             - Reset to default configuration
__FF_ENDPOINTS__()         - Show current endpoint mappings
__FF_WEBSOCKET__()         - Show WebSocket configuration and routing
__FF_HELP__()              - Show this help

Available flags: bffEnabled, chartDataEnabled, runDataEnabled, websocketEnabled
      `)
    }

    ;(window as any).__FF_STATUS__ = () => {
      const status = this.validateConfiguration()
      console.log('🔍 Configuration Status:', status)
      return status
    }

    ;(window as any).__FF_ENDPOINTS__ = () => {
      const config = featureFlagService.getEndpointConfiguration()
      console.log('🎯 Endpoint Mappings:', config.endpointMappings)
      return config.endpointMappings
    }

    ;(window as any).__FF_WEBSOCKET__ = () => {
      const wsEnabled = featureFlagService.isFeatureFlagEnabled('websocket')
      const config = featureFlagService.getEndpointConfiguration()
      const wsInfo = {
        enabled: wsEnabled,
        endpoint: config.endpointMappings.websocket,
        source: wsEnabled ? 'BFF' : 'Backend',
        baseUrl: wsEnabled ? config.wsBaseUrl : config.apiBaseUrl.replace('http', 'ws'),
      }
      console.log('🔌 WebSocket Configuration:', wsInfo)
      return wsInfo
    }

    ;(window as any).__FF_RESET__ = () => {
      console.log('🔄 Resetting feature flags to defaults...')
      // Note: This would require a page reload to take effect
      console.log('⚠️ Page reload required for changes to take effect')
    }

    // Development-only toggle function
    if (import.meta.env.DEV) {
      ;(window as any).__FF_TOGGLE__ = (flag: string) => {
        console.log(`⚠️ Toggle function available in development mode only`)
        console.log(`To toggle ${flag}, update your .env.local file and reload`)
      }
    }
  }

  /**
   * Log initialization information.
   */
  private logInitializationInfo(): void {
    const config = featureFlagService.getConfiguration()
    const status = this.validateConfiguration()

    console.group('🎛️ Feature Flags Initialized')
    console.log('Configuration:', config)
    console.log('Status:', status.valid ? '✅ Valid' : '❌ Invalid')
    
    if (!status.valid) {
      console.warn('Issues:', status.issues)
    }

    console.log('Active Endpoints:', status.summary.activeEndpoints)
    console.log('Type __FF_HELP__() for debug commands')
    console.groupEnd()
  }

  /**
   * Check if we're in development mode.
   */
  private isDevelopmentMode(): boolean {
    return import.meta.env.DEV || import.meta.env.VITE_FEATURE_FLAG_DEBUG === 'true'
  }

  /**
   * Get current debug information.
   */
  public getDebugInfo(): FeatureFlagDebugInfo {
    return featureFlagService.getDebugInfo()
  }
}

// Export singleton instance
export const developmentTools = new DevelopmentToolsIntegration()

// Auto-initialize in development mode
if (typeof window !== 'undefined') {
  developmentTools.initialize()
}

// Export class for testing
export { DevelopmentToolsIntegration }
