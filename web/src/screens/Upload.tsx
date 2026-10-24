import { useEffect, useMemo, useState } from 'react'
import { ImagePlus, Loader2, ScanText, ShieldCheck, Sparkles, X } from 'lucide-react'
import { api, type CategoryInfo, type Hints } from '@/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input, Select, Textarea } from '@/components/ui/input'

type Props = { onCreated: (id: string) => void }

const TIPS = ['лицевая сторона с названием', 'этикетка с составом', 'таблица пищевой ценности и срок годности']
const STEPS = [
  { icon: ScanText, title: 'Читаем этикетку', text: 'распознаём текст и находим нужные поля' },
  { icon: ShieldCheck, title: 'Проверяем каждое значение', text: 'в карточку попадает только то, что есть на фото или в ваших словах' },
  { icon: Sparkles, title: 'Подсказываем, что добавить', text: 'готовность карточки и список того, чего не хватает' },
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
    <div className="mx-auto grid max-w-5xl grid-cols-1 gap-6 px-4 py-8 lg:grid-cols-[1fr_340px]">
      <div className="flex flex-col gap-5">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Карточка товара за три минуты</h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted">
            Сфотографируйте упаковку, и сервис соберёт черновик карточки для «Своё Родное». У каждого значения будет отметка, откуда оно взято, а то, чего нет на фото, сервис не придумывает, а спрашивает у вас.
          </p>
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Фото упаковки</CardTitle>
            <CardDescription>От 1 до 5 фото: {TIPS.join(', ')}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3 sm:grid-cols-5">
              {previews.map((url, index) => (
                <div key={url} className="group relative aspect-square overflow-hidden rounded-lg border border-line bg-stone-100">
                  <img src={url} alt={`Фото ${index + 1}`} className="size-full object-cover" />
                  <button type="button" onClick={() => setPhotos(photos.filter((_, position) => position !== index))}
                    className="absolute top-1 right-1 flex size-6 cursor-pointer items-center justify-center rounded-full bg-white/90 text-ink shadow">
                    <X className="size-3.5" />
                  </button>
                </div>
              ))}
              {photos.length < 5 && (
                <label className="flex aspect-square cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed border-brand-200 bg-brand-50/40 text-brand-700 transition-colors hover:bg-brand-50">
                  <ImagePlus className="size-6" />
                  <span className="text-xs font-medium">добавить</span>
                  <input type="file" accept="image/jpeg,image/png" multiple className="hidden" onChange={(event) => add(event.target.files)} />
                </label>
              )}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Что вы знаете о товаре</CardTitle>
            <CardDescription>Необязательно. Эти слова сервис тоже считает источником.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Select value={hints.category ?? ''} onChange={set('category')}>
              <option value="">Категория</option>
              {categories.map((category) => <option key={category.key} value={category.title}>{category.title}</option>)}
            </Select>
            <Input placeholder="Цена, ₽" inputMode="decimal" value={hints.price ?? ''} onChange={set('price')} />
            <Input placeholder="Вес или объём, например 500 г" value={hints.weight ?? ''} onChange={set('weight')} />
            <Textarea className="sm:col-span-3" placeholder="Уточнения, например: срок годности 6 месяцев, хранить в прохладном месте" value={hints.notes ?? ''} onChange={set('notes')} />
          </CardContent>
        </Card>
        {error && <p className="text-sm text-rose-700">{error}</p>}
        <Button size="lg" disabled={!photos.length || busy} onClick={submit} className="self-start">
          {busy && <Loader2 className="animate-spin" />}
          Собрать черновик
        </Button>
      </div>
      <div className="flex flex-col gap-3 lg:pt-24">
        {STEPS.map(({ icon: Icon, title, text }) => (
          <div key={title} className="flex gap-3 rounded-xl border border-line bg-white p-4">
            <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-700"><Icon className="size-5" /></span>
            <div>
              <p className="text-sm font-medium">{title}</p>
              <p className="mt-0.5 text-xs leading-relaxed text-muted">{text}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}