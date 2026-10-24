import { useEffect, useMemo, useState } from 'react'
import { ImagePlus, Loader2, X } from 'lucide-react'
import { api, type CategoryInfo, type Hints } from '@/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input, Select, Textarea } from '@/components/ui/input'
import { typograph } from '@/format'

type Props = { onCreated: (id: string) => void }

const TIPS = ['лицевая сторона с названием', 'этикетка с составом', 'таблица пищевой ценности и срок годности']
const STEPS = [
  { title: 'Читаем этикетку', text: 'распознаём текст и находим нужные поля' },
  { title: 'Проверяем каждое значение', text: 'в карточку попадает только то, что есть на фото или в Ваших словах' },
  { title: 'Подсказываем, что добавить', text: 'показываем, что осталось заполнить после автоматического распознавания' },
]

export function Upload({ onCreated }: Props) {
  const [photos, setPhotos] = useState<File[]>([])
  const [hints, setHints] = useState<Hints>({})
  const [categories, setCategories] = useState<CategoryInfo[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const previews = useMemo(() => photos.map((photo) => URL.createObjectURL(photo)), [photos])
  useEffect(() => () => previews.forEach((url) => URL.revokeObjectURL(url)), [previews])
  useEffect(() => {
    api.categories().then(setCategories).catch(() => setCategories([]))
  }, [])

  const add = (files: FileList | null) => {
    if (!files) return
    setPhotos((current) => [...current, ...Array.from(files)].slice(0, 5))
  }
  const submit = async () => {
    setBusy(true)
    setError('')
    try {
      const created = await api.create(photos, hints)
      onCreated(created.draft_id)
    } catch (problem) {
      setError((problem as Error).message)
      setBusy(false)
    }
  }
  const set = (key: keyof Hints) => (event: { target: { value: string } }) => setHints({ ...hints, [key]: event.target.value })

  return (
    <div className="mx-auto grid max-w-6xl grid-cols-1 gap-6 px-4 py-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:items-start lg:py-10">
      <section className="rounded-2xl bg-brand-700 px-6 py-7 text-white sm:px-8 sm:pb-9 lg:sticky lg:top-6 lg:px-9 lg:pt-9 lg:pb-11">
        <h1 className="text-3xl leading-tight font-semibold tracking-tight lg:text-[2.6rem]">Карточка товара за&nbsp;три минуты</h1>
        <p className="mt-4 max-w-md text-[15px] leading-relaxed text-balance text-white/80">
          {typograph('Сфотографируйте упаковку, и сервис соберёт черновик карточки, указав, откуда взято каждое значение')}
        </p>
        <ol className="mt-9 hidden space-y-6 sm:block">
          {STEPS.map(({ title, text }, index) => (
            <li key={title} className="grid grid-cols-[2rem_minmax(0,1fr)] border-t border-white/15 pt-5">
              <span className="text-xl leading-none font-semibold text-brand-300 tabular-nums">{index + 1}</span>
              <div>
                <p className="leading-tight font-semibold">{typograph(title)}</p>
                <p className="mt-1.5 text-sm leading-relaxed text-white/70">{typograph(text)}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <div className="flex flex-col gap-5">
        <Card>
          <CardHeader>
            <CardTitle>Фото упаковки</CardTitle>
            <CardDescription>{typograph(`От 1 до 5 фото: ${TIPS.join(', ')}`)}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3 sm:grid-cols-5">
              {previews.map((url, index) => (
                <div key={url} className="relative aspect-square overflow-hidden rounded-xl border border-line bg-paper">
                  <img src={url} alt={`Фото ${index + 1}`} className="size-full object-cover" />
                  <button type="button" onClick={() => setPhotos(photos.filter((_, position) => position !== index))} aria-label="Убрать фото"
                    className="absolute top-1.5 right-1.5 flex size-6 cursor-pointer items-center justify-center rounded-full bg-white/90 text-ink shadow">
                    <X className="size-3.5" />
                  </button>
                </div>
              ))}
              {photos.length < 5 && (
                <label className="flex aspect-square cursor-pointer flex-col items-center justify-center gap-1.5 rounded-xl border-2 border-dashed border-brand-200 bg-brand-50 text-brand-700 transition-colors hover:border-brand-500">
                  <ImagePlus className="size-6" />
                  <span className="text-xs font-semibold">добавить</span>
                  <input type="file" accept="image/jpeg,image/png" multiple className="hidden" onChange={(event) => add(event.target.files)} />
                </label>
              )}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Что Вы знаете о товаре</CardTitle>
            <CardDescription>{typograph('Если Вы знаете то, что не указано на упаковке, впишите это, и тогда сервис это учтёт')}</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Select value={hints.category ?? ''} onChange={set('category')}>
              <option value="">Категория</option>
              {categories.map((category) => <option key={category.key} value={category.title}>{category.title}</option>)}
            </Select>
            <Input placeholder="Цена, ₽" inputMode="decimal" value={hints.price ?? ''} onChange={set('price')} />
            <Input placeholder="Вес или объём" value={hints.weight ?? ''} onChange={set('weight')} />
            <Textarea className="sm:col-span-3" placeholder="Уточнения, например: срок годности 6 месяцев" value={hints.notes ?? ''} onChange={set('notes')} />
          </CardContent>
        </Card>
        {error && <p className="text-sm text-rose-700">{error}</p>}
        <Button size="lg" disabled={!photos.length || busy} onClick={submit} className="w-full sm:w-auto sm:self-end">
          {busy && <Loader2 className="animate-spin" />}
          Собрать черновик
        </Button>
      </div>
    </div>
  )
}