import { useState } from 'react'
import { Check, Copy } from 'lucide-react'
import type { Draft } from '@/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

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
  const [copied, setCopied] = useState(false)
  const text = JSON.stringify(cardJson(draft), null, 2)
  const copy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <div className="mb-6 flex items-center gap-3">
        <span className="flex size-10 items-center justify-center rounded-full bg-brand-600 text-white"><Check className="size-5" /></span>
        <div>
          <h1 className="text-xl font-semibold">Карточка подтверждена</h1>
          <p className="text-sm text-muted">Её можно отправить в модерацию площадки через API</p>
        </div>
      </div>
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <div>
            <CardTitle>Данные для площадки</CardTitle>
            <CardDescription>по контракту openapi.yaml, у каждого поля источник и место на фото</CardDescription>
          </div>
          <Button size="sm" variant="outline" onClick={copy}>{copied ? <Check /> : <Copy />}{copied ? 'скопировано' : 'скопировать'}</Button>
        </CardHeader>
        <CardContent>
          <pre className="max-h-[60vh] overflow-auto rounded-lg bg-stone-950 p-4 text-xs leading-relaxed text-stone-100">{text}</pre>
        </CardContent>
      </Card>
      <Button className="mt-6" variant="outline" onClick={onNew}>Новая карточка</Button>
    </div>
  )
}