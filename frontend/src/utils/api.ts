/**
 * API utilities for consistent HTTP request handling.
 *
 * This module centralizes common API patterns to reduce duplication
 * and ensure consistent error handling across the frontend.
 */

import { API_BASE_URL } from '../constants'
import { apiRouter } from './apiRouter'
import type { EndpointGroup } from '../types/featureFlags'

export interface ApiRequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  headers?: Record<string, string>
  body?: unknown
  idempotencyKey?: string
  /** Endpoint group for feature flag routing */
  endpointGroup?: EndpointGroup
  /** Whether to use feature flag routing (default: false for backward compatibility) */
  useFeatureFlags?: boolean
  /** Optional router timeout (ms) when using feature flags; defaults to 30000 */
  routerTimeoutMs?: number
  /** Disable backend fallback when using feature flags (default: true for diagnostics) */
  allowFallback?: boolean
}

/**
 * Make an API request with consistent error handling and base URL.
 * Supports feature flag routing when endpointGroup is specified.
 */
export async function apiRequest<T>(endpoint: string, options: ApiRequestOptions = {}): Promise<T> {
  const {
    method = 'GET',
    headers = {},
    body,
    idempotencyKey,
    endpointGroup,
    useFeatureFlags = false,
    routerTimeoutMs,
  } = options

  const requestHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...headers,
  }

  if (idempotencyKey) {
    requestHeaders['Idempotency-Key'] = idempotencyKey
  }

  const requestInit: RequestInit = {
    method,
    headers: requestHeaders,
  }

  if (body && method !== 'GET') {
    requestInit.body = JSON.stringify(body)
  }

  // Use feature flag routing if specified
  if (useFeatureFlags && endpointGroup) {
    return await apiRouter.routeAPICall<T>(endpointGroup, endpoint, {
      ...requestInit,
      // Diagnostics-first: disable fallback by default unless explicitly enabled
      allowFallback: options.allowFallback ?? false,
      timeout: routerTimeoutMs ?? 30000,
    })
  }

  // Fallback to direct API call (backward compatibility)
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`

  const response = await fetch(url, requestInit)

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Make a GET request.
 */
export async function apiGet<T>(endpoint: string, headers?: Record<string, string>): Promise<T> {
  return apiRequest<T>(endpoint, { method: 'GET', headers })
}

/**
 * Make a POST request.
 */
export async function apiPost<T>(
  endpoint: string,
  body?: unknown,
  options?: { headers?: Record<string, string>; idempotencyKey?: string },
): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: 'POST',
    body,
    headers: options?.headers,
    idempotencyKey: options?.idempotencyKey,
  })
}

/**
 * Make a PUT request.
 */
export async function apiPut<T>(
  endpoint: string,
  body?: unknown,
  headers?: Record<string, string>,
): Promise<T> {
  return apiRequest<T>(endpoint, { method: 'PUT', body, headers })
}

/**
 * Make a DELETE request.
 */
export async function apiDelete<T>(endpoint: string, headers?: Record<string, string>): Promise<T> {
  return apiRequest<T>(endpoint, { method: 'DELETE', headers })
}

// Feature flag-enabled API functions

/**
 * Make a GET request with feature flag routing.
 */
export async function apiGetWithFlags<T>(
  endpoint: string,
  endpointGroup: EndpointGroup,
  headers?: Record<string, string>,
  timeoutMs?: number,
  allowFallback?: boolean,
): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: 'GET',
    headers,
    endpointGroup,
    useFeatureFlags: true,
    routerTimeoutMs: timeoutMs,
    allowFallback,
  })
}

/**
 * Make a POST request with feature flag routing.
 */
export async function apiPostWithFlags<T>(
  endpoint: string,
  endpointGroup: EndpointGroup,
  body?: unknown,
  options?: { headers?: Record<string, string>; idempotencyKey?: string; timeoutMs?: number },
): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: 'POST',
    body,
    headers: options?.headers,
    idempotencyKey: options?.idempotencyKey,
    endpointGroup,
    useFeatureFlags: true,
    routerTimeoutMs: options?.timeoutMs,
  })
}
