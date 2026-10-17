import { getLang } from './i18n'

const TZ = 'Asia/Almaty'
const SYMBOL: Record<string, string> = { KZT: '₸', KGS: 'сом' }
const locale = () => (getLang() === 'kk' ? 'kk-KZ' : 'ru-RU')

/** 84000 → «84 000 ₸» (неразрывные пробелы, целые). */
export function money(amount: number, currency = 'KZT'): string {
  const grouped = Math.round(amount).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
  return `${grouped} ${SYMBOL[currency] ?? currency}`
}

/** «18 окт» / «18 окт 2026» — календарь Алматы. Принимает ISO-дату или время. */
export function shortDate(value: string, withYear = false): string {
  const d = value.length === 10 ? new Date(`${value}T12:00:00+05:00`) : new Date(value)
  return new Intl.DateTimeFormat(locale(), { day: 'numeric', month: 'short', ...(withYear ? { year: 'numeric' } : {}), timeZone: TZ }).format(d).replace('.', '')
}

/** «18 окт, 14:30» по Алматы. */
export function dateTime(value: string): string {
  return new Intl.DateTimeFormat(locale(), { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: TZ }).format(new Date(value)).replace('.', '')
}

/** Сегодня по Алматы, YYYY-MM-DD. */
export function todayAlmaty(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(new Date())
}

/** Неразрывные пробелы внутри сумм в готовом тексте с сервера: «250 000 ₸» не рвётся на строке. */
export function keepMoneyTogether(text: string): string {
  return text.replace(/(\d) (?=\d{3}\b)/g, '$1\u00a0').replace(/(\d) (₸|сом)/g, '$1\u00a0$2')
}
