import { useSyncExternalStore } from 'react'
import { api, revisionStore, tokenStore } from '@/services/http/client'

/** Флаги фич с бэкенда (GET /api/settings). До ответа считаем включёнными (в демо включено всё). */
export interface AppSettings { features: string[] | null; demoMode: boolean; country: string; lang: string; llmAvailable: boolean }
let settings: AppSettings = { features: null, demoMode: false, country: 'KZ', lang: 'ru', llmAvailable: false }
const listeners = new Set<() => void>()
let lastToken: string | null = null

async function load() {
  const token = tokenStore.read()
  if (!token) { lastToken = null; return }
  if (token === lastToken && settings.features) return
  lastToken = token
  const r = await api.get<AppSettings>('/settings')
  if (r.ok) { settings = r.data; listeners.forEach((l) => l()) }
}
revisionStore.subscribe(() => { void load() })
void load()

export function featureEnabled(feature: string | undefined): boolean {
  return !feature || settings.features === null || settings.features.includes(feature)
}

export function useSettings(): AppSettings {
  return useSyncExternalStore((l) => { listeners.add(l); return () => { listeners.delete(l) } }, () => settings)
}
