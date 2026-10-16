import { useSyncExternalStore } from 'react'
import { api, tokenStore } from '@/services/http/client'

/** RU/KZ для экранов ext-фич. Язык хранится в браузере и синхронизируется с бэкендом
 * (PUT /api/auth/me/lang) — тогда и уведомления приходят на том же языке. */
export type Lang = 'ru' | 'kk'
type Dict = Record<string, string>

const KEY = 'jana.lang.v1'
const dictionaries: Record<Lang, Dict> = { ru: {}, kk: {} }
const listeners = new Set<() => void>()
let lang: Lang = (() => { try { return localStorage.getItem(KEY) === 'kk' ? 'kk' : 'ru' } catch { return 'ru' } })()

export function registerDictionary(ru: Dict, kk: Dict) {
  Object.assign(dictionaries.ru, ru)
  Object.assign(dictionaries.kk, kk)
}

export function getLang(): Lang { return lang }

export function setLang(next: Lang) {
  lang = next
  try { localStorage.setItem(KEY, next) } catch { /* только память */ }
  document.documentElement.lang = next === 'kk' ? 'kk' : 'ru'
  listeners.forEach((l) => l())
  if (tokenStore.read()) void api.put('/auth/me/lang', { lang: next })
}

export function translate(key: string, params?: Record<string, string | number>, l: Lang = lang): string {
  const template = dictionaries[l][key] ?? dictionaries.ru[key] ?? key
  return params ? template.replace(/\{(\w+)\}/g, (_, name: string) => String(params[name] ?? `{${name}}`)) : template
}

export function useLang(): Lang {
  return useSyncExternalStore((l) => { listeners.add(l); return () => { listeners.delete(l) } }, () => lang)
}

/** const t = useT(); t('ext.wage.title', { amount }) */
export function useT() {
  const l = useLang()
  return (key: string, params?: Record<string, string | number>) => translate(key, params, l)
}

registerDictionary(
  {
    'common.loading': 'Загружаем…', 'common.retry': 'Попробовать ещё раз', 'common.empty': 'Пока пусто', 'common.error': 'Не удалось загрузить данные',
    'common.save': 'Сохранить', 'common.cancel': 'Отмена', 'common.back': 'Назад', 'common.close': 'Закрыть', 'common.confirm': 'Подтвердить',
    'common.sending': 'Отправляем…', 'common.lang': 'Язык', 'common.country.KZ': 'Казахстан', 'common.country.KG': 'Кыргызстан',
    'common.all': 'Все', 'common.days': 'дн.', 'common.open': 'Открыть', 'nav.ext.group': 'Сервисы JanaМен',
  },
  {
    'common.loading': 'Жүктелуде…', 'common.retry': 'Қайталап көру', 'common.empty': 'Әзірге бос', 'common.error': 'Деректерді жүктеу мүмкін болмады',
    'common.save': 'Сақтау', 'common.cancel': 'Бас тарту', 'common.back': 'Артқа', 'common.close': 'Жабу', 'common.confirm': 'Растау',
    'common.sending': 'Жіберілуде…', 'common.lang': 'Тіл', 'common.country.KZ': 'Қазақстан', 'common.country.KG': 'Қырғызстан',
    'common.all': 'Барлығы', 'common.days': 'күн', 'common.open': 'Ашу', 'nav.ext.group': 'JanaМен қызметтері',
  },
)
