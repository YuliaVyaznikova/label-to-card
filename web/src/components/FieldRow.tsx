import { useEffect, useState } from 'react'
import { AlertTriangle, Camera, CircleDashed, PencilLine, User } from 'lucide-react'
import type { FieldOut } from '@/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input, Textarea } from '@/components/ui/input'
import { SOURCE_LABELS, formatValue, percent } from '@/format'
import { cn } from '@/lib/utils'

const ICONS = { photo: Camera, farmer: User, edited: PencilLine, none: CircleDashed, conflict: AlertTriangle }
const LONG = new Set(['composition', 'manufacturer', 'storage', 'usage'])

type Props = {
  name: string
  title: string
  kind: string
  field: FieldOut
  required: boolean
  selected: boolean
  onSelect: () => void
  onSave: (value: string) => void
}

export function FieldRow({ name, title, kind, field, required, selected, onSelect, onSave }: Props) {
  const shown = field.source === 'none' ? '' : formatValue(kind, field.value)
  const [text, setText] = useState(shown)
  useEffect(() => setText(shown), [shown])
  const Icon = ICONS[field.source]
  const commit = () => {
    if (text.trim() !== shown.trim()) onSave(text.trim())
  }
  const evidence = field.evidence.find((item) => item.source === 'photo')
  const placeholder = field.source === 'none' ? 'нет на фото, впишите сами' : ''
  return (
    <div onClick={onSelect}
      className={cn('rounded-lg border px-3 py-2.5 transition-colors', selected ? 'border-brand-500 bg-brand-50/60' : 'border-transparent hover:bg-stone-50')}>
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-muted">
          {title}
          {required && <span className="ml-0.5 text-rose-500">*</span>}
        </span>
        <span className="flex items-center gap-2">
          {field.source === 'photo' && <span className="text-[11px] text-muted">уверенность {percent(field.confidence)}</span>}
          <Badge tone={field.source}>
            <Icon />
            {SOURCE_LABELS[field.source]}
          </Badge>
        </span>
      </div>
      {field.source === 'conflict' ? (
        <div className="flex flex-wrap gap-2">
          {field.alternatives.map((item, index) => {
            const value = formatValue(kind, item.value as Record<string, unknown>)
            return (
              <Button key={index} size="sm" variant="outline" onClick={() => onSave(value)}>
                {item.source === 'photo' ? 'На этикетке' : 'У вас'}: {value}
              </Button>
            )
          })}
        </div>
      ) : LONG.has(name) ? (
        <Textarea value={text} placeholder={placeholder} onChange={(event) => setText(event.target.value)} onBlur={commit} rows={name === 'composition' ? 4 : 2} />
      ) : (
        <Input value={text} placeholder={placeholder} onChange={(event) => setText(event.target.value)} onBlur={commit}
          onKeyDown={(event) => event.key === 'Enter' && (event.target as HTMLInputElement).blur()} />
      )}
      {evidence && (
        <p className="mt-1.5 truncate text-[11px] text-muted">
          фото {evidence.photo}: «{evidence.text}»
        </p>
      )}
    </div>
  )
}