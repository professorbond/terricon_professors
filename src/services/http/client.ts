import type { RequestOptions, ServiceProblem, ServiceResult } from '../contracts'

/** HTTP-транспорт к бэкенду JanaМен. Токен — в sessionStorage вкладки (как и демо-роль). */
const TOKEN_KEY = 'jana.api-token.v1'
let memoryToken: string | null = null

export const apiBaseUrl = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ?? ''
export const apiEnabled = apiBaseUrl !== ''

export const tokenStore = {
  read(): string | null {
    try { return sessionStorage.getItem(TOKEN_KEY) } catch { return memoryToken }
  },
  write(token: string | null) {
    memoryToken = token
    try { if (token) sessionStorage.setItem(TOKEN_KEY, token); else sessionStorage.removeItem(TOKEN_KEY) } catch { /* память до перезагрузки */ }
  },
}

/** Ревизия данных: растёт после изменений и периодически — экраны перечитывают данные с сервера. */
const listeners = new Set<() => void>()
let revision = 0
export const revisionStore = {
  subscribe(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener) } },
  getRevision: () => revision,
  bump() { revision += 1; listeners.forEach((listener) => listener()) },
}
if (typeof window !== 'undefined' && apiEnabled) {
  window.setInterval(() => { if (document.visibilityState === 'visible' && tokenStore.read()) revisionStore.bump() }, 20_000)
  window.addEventListener('focus', () => { if (tokenStore.read()) revisionStore.bump() })
}

const KINDS: ReadonlySet<ServiceProblem['kind']> = new Set(['unauthenticated', 'forbidden', 'not-found', 'validation', 'conflict', 'unavailable'])

export interface ApiProblem extends ServiceProblem { readonly code?: string; readonly data?: Readonly<Record<string, unknown>> }

/** Один запрос. Ошибки бэкенда ({kind, code, message, fieldErrors, data}) → ServiceProblem; изменения поднимают ревизию. */
export async function request<T>(method: string, path: string, body?: unknown, options?: RequestOptions): Promise<ServiceResult<T> & { problem?: ApiProblem }> {
  const token = tokenStore.read()
  let response: Response
  try {
    response = await fetch(`${apiBaseUrl}/api${path}`, {
      method,
      ...(options?.signal ? { signal: options.signal } : {}),
      headers: { ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    })
  } catch (error) {
    if (options?.signal?.aborted) throw error
    return { ok: false, problem: { kind: 'unavailable', message: 'Сервер JanaМен недоступен. Проверьте подключение и попробуйте ещё раз.' } }
  }
  const payload: unknown = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) {
    const p = (payload ?? {}) as { kind?: string; code?: string; message?: string; fieldErrors?: Record<string, string[]>; data?: Record<string, unknown> }
    const kind = (KINDS.has(p.kind as ServiceProblem['kind']) ? p.kind : response.status >= 500 ? 'unavailable' : 'validation') as ServiceProblem['kind']
    if (kind === 'unauthenticated') tokenStore.write(null)
    return { ok: false, problem: { kind, message: p.message ?? 'Не удалось выполнить действие.', ...(p.code ? { code: p.code } : {}), ...(p.data ? { data: p.data } : {}), ...(p.fieldErrors ? { fieldErrors: p.fieldErrors } : {}) } }
  }
  if (method !== 'GET') revisionStore.bump()
  return { ok: true, data: payload as T }
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) => request<T>('GET', path, undefined, options),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) => request<T>('POST', path, body ?? {}, options),
  put: <T>(path: string, body: unknown, options?: RequestOptions) => request<T>('PUT', path, body, options),
}
