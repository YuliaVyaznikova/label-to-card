import { useEffect, useState } from 'react'
import { Check, Loader2 } from 'lucide-react'
import { Logo } from '@/components/Brand'
import { cn } from '@/lib/utils'

const STEPS = ['Проверяем качество фото', 'Распознаём текст на этикетке', 'Определяем категорию', 'Читаем поля моделью', 'Проверяем каждое значение по фото', 'Считаем готовность']

export function Processing({ failed, onRetry }: { failed?: string | null; onRetry: () => void }) {
  const [step, setStep] = useState(0)
  useEffect(() => {
    const timer = setInterval(() => setStep((current) => Math.min(current + 1, STEPS.length - 1)), 2500)
    return () => clearInterval(timer)
  }, [])
  return (
    <div className="mx-auto max-w-lg px-4 py-12">
      <div className="rounded-2xl border border-line bg-white p-7 shadow-[0_1px_3px_rgba(29,42,31,0.05)] sm:p-9">
        <div className="flex items-center gap-4">
          <Logo className={cn('size-12 shrink-0', !failed && 'animate-pulse')} />
          <div>
            <h2 className="text-xl font-semibold">{failed ? 'Не получилось собрать черновик' : 'Собираем черновик'}</h2>
            <p className="mt-0.5 text-sm text-muted">{failed ? failed : 'обычно это занимает меньше минуты'}</p>
          </div>
        </div>
        {failed ? (
          <button type="button" onClick={onRetry} className="mt-6 cursor-pointer text-sm font-semibold text-brand-700 underline underline-offset-4">начать заново</button>
        ) : (
          <ol className="mt-7 space-y-1">
            {STEPS.map((title, index) => (
              <li key={title} className={cn('flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors',
                index === step ? 'bg-brand-50 font-semibold text-brand-700' : index < step ? 'text-ink' : 'text-muted')}>
                <span className={cn('flex size-6 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold',
                  index < step ? 'bg-brand-600 text-white' : index === step ? 'bg-white text-brand-700 ring-1 ring-brand-200' : 'bg-paper text-muted')}>
                  {index < step ? <Check className="size-3.5" /> : index === step ? <Loader2 className="size-3.5 animate-spin" /> : index + 1}
                </span>
                {title}
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  )
}