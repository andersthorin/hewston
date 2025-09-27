/**
 * API utilities for consistent HTTP request handling.
 * 
 * This module centralizes common API patterns to reduce duplication
 * and ensure consistent error handling across the frontend.
 */

import { API_BASE_URL } from '../constants'

export interface ApiRequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  headers?: Record<string, string>
  body?: unknown
  idempotencyKey?: string
}

/**
 * Make an API request with consistent error handling and base URL.
 */
export async function apiRequest<T>(
  endpoint: string,
  options: ApiRequestOptions = {}
): Promise<T> {
  const { method = 'GET', headers = {}, body, idempotencyKey } = options

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
  options?: { headers?: Record<string, string>; idempotencyKey?: string }
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
  headers?: Record<string, string>
): Promise<T> {
  return apiRequest<T>(endpoint, { method: 'PUT', body, headers })
}

/**
 * Make a DELETE request.
 */
export async function apiDelete<T>(
  endpoint: string,
  headers?: Record<string, string>
): Promise<T> {
  return apiRequest<T>(endpoint, { method: 'DELETE', headers })
}
