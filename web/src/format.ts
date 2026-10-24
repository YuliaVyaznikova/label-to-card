import type { FieldOut } from './api'

const UNITS: Record<string, string> = { g: 'г', ml: 'мл', pcs: 'шт' }
const DURATIONS: Record<string, string> = { days: 'сут.', months: 'мес.', years: 'г.', hours: 'ч' }

export const SOURCE_LABELS: Record<FieldOut['source'], string> = {
  photo: 'с фото',
  farmer: 'с Ваших слов',
  edited: 'введено Вами',
  none: 'нет данных',
  conflict: 'расхождение',
}

export function number(value: unknown) {
  return typeof value === 'number' ? value.toLocaleString('ru-RU', { maximumFractionDigits: 2 }) : String(value ?? '')
}

export function formatValue(kind: string, value: Record<string, unknown> | null | undefined) {
  if (!value) return ''
  const main = value.value
  if (kind === 'quantity') return `${number(main)} ${UNITS[String(value.unit)] ?? value.unit}`
  if (kind === 'duration' && value.unit === 'unlimited') return 'не ограничен'
  if (kind === 'duration') return `${number(main)} ${DURATIONS[String(value.unit)] ?? value.unit}`
  if (kind === 'energy') return `${number(main)} ккал`
  if (kind === 'number') return `${number(main)} г`
  if (kind === 'percent') return `${number(main)} %`
  return String(main ?? '')
}

export function percent(value: number) {
  return `${Math.round(value * 100)}%`
}