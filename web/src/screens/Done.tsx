import { useState } from 'react'
import { Check, ChevronDown, Copy } from 'lucide-react'
import type { Draft } from '@/api'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { formatValue, typograph } from '@/format'
import { cn } from '@/lib/utils'

const NUTRITION = [['energy_kcal', 'Энергетическая ценность'], ['proteins_g', 'Белки'], ['fats_g', 'Жиры'], ['carbohydrates_g', 'Углеводы']] as const
const DETAILS = ['composition', 'shelf_life', 'storage', 'manufacturer', 'fat_share', 'usage']

export function cardJson(draft: Draft) {
  const fields = Object.fromEntries(
    Object.entries(draft.fields)
      .filter(([, field]) => field.source !== 'none')
      .map(([name, field]) => [name, { value: field.value, source: field.source, evidence: field.evidence.map((item) => ({ photo: item.photo, line: item.line, text: item.text })) }]),
  )
  return {
    draft_id: draft.draft_id,
    schema_version: draft.schema_version,
    status: draft.status,
    category: draft.category?.value,
    fields,
    description: draft.description?.text,
    readiness: draft.readiness?.score,
  }
}

export function Done({ draft, onNew }: { draft: Draft; onNew: () => void }) {
  const [active, setActive] = useState(1)
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const text = JSON.stringify(cardJson(draft), null, 2)
  const copy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  const value = (name: string) => {
    const field = draft.fields[name]
    return field && field.source !== 'none' ? formatValue(draft.kinds[name], field.value) : ''
  }
  const photo = draft.photos.find((item) => item.number === active) ?? draft.photos[0]
  const price = String(draft.hints.price ?? '').trim()
  const nutrition = NUTRITION.filter(([name]) => value(name))
  const details = DETAILS.filter((name) => value(name) && draft.titles[name])

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 flex items-center gap-4">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-brand-600 text-white"><Check className="size-5" /></span>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Карточка подтверждена</h1>
          <p className="mt-0.5 text-sm text-muted">{typograph('Карточка готова к отправке на площадку, так её увидят покупатели')}</p>
        </div>
      </div>

      <Card className="overflow-hidden">
        <div className="grid grid-cols-1 md:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
          <div className="border-b border-line p-5 md:border-r md:border-b-0">
            {photo && <img src={photo.url} alt={value('name')} className="aspect-square w-full rounded-xl bg-paper object-contain" />}
            {draft.photos.length > 1 && (
              <div className="mt-3 flex gap-2">
                {draft.photos.map((item) => (
                  <button key={item.number} type="button" onClick={() => setActive(item.number)}
                    className={cn('size-14 cursor-pointer overflow-hidden rounded-xl border-2 bg-white', item.number === photo?.number ? 'border-brand-600' : 'border-transparent opacity-75 hover:opacity-100')}>
                    <img src={item.url} alt="" className="size-full object-cover" />
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="p-6 sm:p-7">
            {draft.category?.value && <p className="text-xs font-semibold tracking-wide text-brand-600 uppercase">{draft.category.value}</p>}
            <h2 className="mt-1.5 text-2xl leading-tight font-semibold">{value('name')}</h2>
            {value('net_quantity') && <p className="mt-1 text-sm text-muted">{value('net_quantity')}</p>}
            {price && <p className="mt-4 text-3xl font-semibold tracking-tight">{price} ₽</p>}
            {draft.description?.text && <p className="mt-5 text-sm leading-relaxed">{typograph(draft.description.text)}</p>}
            {nutrition.length > 0 && (
              <div className="mt-6">
                <p className="text-sm font-semibold">Пищевая ценность на 100 г</p>
                <div className="mt-2.5 grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {nutrition.map(([name, title]) => (
                    <div key={name} className="rounded-xl bg-brand-50 px-3 py-2.5">
                      <p className="text-[11px] leading-tight text-muted">{title}</p>
                      <p className="mt-1 font-semibold">{value(name)}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {details.length > 0 && (
              <dl className="mt-6 divide-y divide-line border-t border-line text-sm">
                {details.map((name) => (
                  <div key={name} className="grid grid-cols-1 gap-1 py-3 sm:grid-cols-[10rem_minmax(0,1fr)] sm:gap-4">
                    <dt className="text-muted">{draft.titles[name].replace(/,\s*%$/, '')}</dt>
                    <dd className="leading-relaxed">{typograph(value(name))}</dd>
                  </div>
                ))}
              </dl>
            )}
          </div>
        </div>
      </Card>

      <div className="mt-4 rounded-2xl border border-line bg-white">
        <button type="button" onClick={() => setOpen(!open)} className="flex w-full cursor-pointer items-center justify-between px-5 py-4 text-sm font-semibold">
          Данные для разработчиков
          <ChevronDown className={cn('size-4 text-muted transition-transform', open && 'rotate-180')} />
        </button>
        {open && (
          <div className="border-t border-line px-5 pt-4 pb-5">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-muted">карточка в формате API по контракту openapi.yaml, у каждого поля источник и место на фото</p>
              <Button size="sm" variant="outline" onClick={copy}>{copied ? <Check /> : <Copy />}{copied ? 'скопировано' : 'скопировать'}</Button>
            </div>
            <pre className="max-h-[50vh] overflow-auto rounded-xl bg-brand-900 p-4 text-xs leading-relaxed text-brand-50">{text}</pre>
          </div>
        )}
      </div>

      <Button className="mt-6" variant="outline" onClick={onNew}>Новая карточка</Button>
    </div>
  )
}