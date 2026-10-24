import { useMemo, useState } from 'react'
import { ArrowLeft, Check, CircleAlert, ImagePlus, ListChecks, Loader2, OctagonAlert, TriangleAlert, X } from 'lucide-react'
import { api, type Draft } from '@/api'
import { FieldRow } from '@/components/FieldRow'
import { PhotoViewer } from '@/components/PhotoViewer'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { percent, typograph } from '@/format'
import { cn } from '@/lib/utils'

type Props = { draft: Draft; onDraft: (draft: Draft) => void; onReprocess: () => void; onBack: () => void }

const METHODS: Record<string, string> = {
  model: 'написано моделью только по проверенным полям',
  template: 'собрано по шаблону из проверенных полей',
  edited: 'исправлено Вами',
  empty: 'пока не из чего писать',
}

export function Review({ draft, onDraft, onReprocess, onBack }: Props) {
  const names = useMemo(() => [...draft.required, ...Object.keys(draft.titles).filter((name) => !draft.required.includes(name))], [draft])
  const [selected, setSelected] = useState(names[0])
  const [active, setActive] = useState(1)
  const [pending, setPending] = useState(0)
  const busy = pending > 0
  const [error, setError] = useState('')
  const [description, setDescription] = useState(draft.description?.text ?? '')
  const blocks = draft.moderation.filter((issue) => issue.severity === 'block')
  const warnings = draft.moderation.filter((issue) => issue.severity === 'warning')
  const highlights = draft.fields[selected]?.evidence ?? []
  const readiness = draft.readiness

  const run = async (action: () => Promise<Draft>) => {
    setPending((count) => count + 1)
    setError('')
    try {
      const next = await action()
      onDraft(next)
      setDescription(next.description?.text ?? '')
    } catch (problem) {
      setError((problem as Error).message)
    } finally {
      setPending((count) => count - 1)
    }
  }
  const save = (fields: Record<string, string>) => run(() => api.edit(draft.draft_id, fields))
  const select = (name: string) => {
    setSelected(name)
    const photo = draft.fields[name]?.evidence.find((item) => item.photo)?.photo
    if (photo) setActive(photo)
  }
  const addPhoto = async (file: File | undefined) => {
    if (!file) return
    setPending((count) => count + 1)
    await api.addPhoto(draft.draft_id, file).catch((problem) => setError(problem.message))
    setPending((count) => count - 1)
    onReprocess()
  }
  const reason = blocks.length ? 'Сначала исправьте блокирующие замечания' : draft.status !== 'ready' ? 'Заполните обязательные поля' : ''

  return (
    <div className="mx-auto max-w-6xl px-4 pt-6 pb-28">
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <Button variant="ghost" size="icon" onClick={onBack} aria-label="Назад"><ArrowLeft /></Button>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-2xl font-semibold tracking-tight">{draft.fields.name?.value ? String(draft.fields.name.value.value) : 'Черновик карточки'}</h1>
          <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-muted">
            {draft.category && <Badge tone="brand">{draft.category.value} · {percent(draft.category.confidence)}</Badge>}
            <span>обработка {String(draft.timings?.total ?? '?')} с</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <div className="flex flex-col gap-4 lg:sticky lg:top-4 lg:self-start">
          <PhotoViewer photos={draft.photos} lines={draft.lines} highlights={highlights} active={active} onActive={setActive} />
          {draft.photos.length < 5 && (
            <label className="flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-brand-200 bg-white py-3 text-sm font-semibold text-brand-700 transition-colors hover:bg-brand-50">
              <ImagePlus className="size-4" /> Добавить ещё фото этикетки
              <input type="file" accept="image/jpeg,image/png" className="hidden" onChange={(event) => addPhoto(event.target.files?.[0])} />
            </label>
          )}
        </div>

        <div className="flex flex-col gap-4">
          {readiness && (
            <Card>
              <CardContent className="pt-5">
                <div className="flex items-end justify-between gap-4">
                  <div>
                    <p className="text-xs text-muted">Готовность карточки</p>
                    <p className="text-4xl font-semibold text-brand-700 tabular-nums">{readiness.score}<span className="text-lg font-medium text-muted">/100</span></p>
                  </div>
                  <div className="grid w-56 gap-1.5 text-xs">
                    {([['поля', readiness.fields], ['фото', readiness.photos], ['текст', readiness.text]] as const).map(([label, value]) => (
                      <div key={label} className="flex items-center gap-2">
                        <span className="w-10 text-muted">{label}</span>
                        <Progress value={value * 100} />
                        <span className="w-9 text-right tabular-nums">{percent(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
                {draft.missing.length > 0 && (
                  <div className="mt-4 border-t border-line pt-3">
                    <p className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted"><ListChecks className="size-3.5" />Что осталось сделать</p>
                    <ul className="space-y-1.5">
                      {draft.missing.map((item) => (
                        <li key={item.action}>
                          <button type="button" onClick={() => item.field && select(item.field)} className={cn('flex w-full items-start gap-2 text-left text-sm', item.field && 'cursor-pointer hover:text-brand-700')}>
                            <CircleAlert className="mt-0.5 size-4 shrink-0 text-[#e0a800]" />{typograph(item.action)}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {draft.moderation.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Предварительная модерация</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {[...blocks, ...warnings].map((issue, index) => (
                  <div key={index} className={cn('flex gap-2.5 rounded-xl px-3.5 py-2.5 text-sm leading-relaxed', issue.severity === 'block' ? 'bg-rose-50 text-rose-900' : 'bg-sun-50 text-ink')}>
                    {issue.severity === 'block' ? <OctagonAlert className="mt-0.5 size-4 shrink-0" /> : <TriangleAlert className="mt-0.5 size-4 shrink-0 text-sun-700" />}
                    <span>{typograph(issue.message)}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          <Tabs defaultValue="fields">
            <TabsList>
              <TabsTrigger value="fields">Поля</TabsTrigger>
              <TabsTrigger value="description">Описание</TabsTrigger>
              <TabsTrigger value="log">Журнал проверки</TabsTrigger>
            </TabsList>
            <TabsContent value="fields">
              <Card>
                <CardContent className="space-y-1 pt-3">
                  {names.map((name) => draft.fields[name] && (
                    <FieldRow key={name} name={name} title={draft.titles[name]} kind={draft.kinds[name]} field={draft.fields[name]}
                      required={draft.required.includes(name)} selected={selected === name} onSelect={() => select(name)}
                      onSave={(value) => save({ [name]: value })} />
                  ))}
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="description">
              <Card>
                <CardHeader>
                  <CardTitle>Описание для карточки</CardTitle>
                  <CardDescription>{METHODS[draft.description?.method ?? 'empty']}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Textarea rows={6} value={description} onChange={(event) => setDescription(event.target.value)} />
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    {draft.description?.checked
                      ? <Badge tone="photo"><Check />каждое число и утверждение опирается на поля карточки</Badge>
                      : <Badge tone="warning"><TriangleAlert />{draft.description?.problems.join('; ') || 'не проверено'}</Badge>}
                    <Button size="sm" variant="outline" disabled={description === draft.description?.text} onClick={() => save({ description })}>Сохранить описание</Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="log">
              <Card>
                <CardHeader>
                  <CardTitle>Что предложила модель и что прошло проверку</CardTitle>
                  <CardDescription>{typograph('Значение попадает в карточку, только если его текст найден на фото или в Ваших словах')}</CardDescription>
                </CardHeader>
                <CardContent className="divide-y divide-line">
                  {draft.log.map((entry, index) => (
                    <div key={index} className="flex items-start gap-3 py-2 text-sm">
                      {entry.decision === 'accepted' ? <Check className="mt-0.5 size-4 shrink-0 text-brand-600" /> : <X className="mt-0.5 size-4 shrink-0 text-rose-600" />}
                      <div className="min-w-0 flex-1">
                        <p className="text-xs text-muted">{draft.titles[entry.field] ?? entry.field}</p>
                        <p className="break-words">«{typograph(entry.proposed ?? '')}»</p>
                        {entry.decision === 'rejected' && <p className="text-xs text-rose-700">отброшено: {typograph(entry.reason ?? '')}</p>}
                      </div>
                      {entry.score != null && <span className="text-xs text-muted tabular-nums">{percent(entry.score)}</span>}
                    </div>
                  ))}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
          {error && <p className="text-sm text-rose-700">{error}</p>}
        </div>
      </div>

      <div className="fixed inset-x-0 bottom-0 border-t border-line bg-white shadow-[0_-6px_20px_rgba(29,42,31,0.06)]">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3">
          <p className="text-sm text-muted">{reason || 'Карточка готова к отправке на площадку'}</p>
          <Button size="lg" disabled={!!reason || busy} onClick={() => run(() => api.confirm(draft.draft_id))}>
            {busy ? <Loader2 className="animate-spin" /> : <Check />}
            Подтвердить
          </Button>
        </div>
      </div>
    </div>
  )
}