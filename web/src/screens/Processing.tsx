import { useEffect, useState } from 'react'
import { Check, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

const STEPS = ['Проверяем качество фото', 'Распознаём текст на этикетке', 'Определяем категорию', 'Читаем поля моделью', 'Проверяем каждое значение по фото', 'Считаем готовность']

export function Processing({ failed, onRetry }: { failed?: string | null; onRetry: () => void }) {
  const [step, setStep] = useState(0)
  useEffect(() => {
    const timer = setInterval(() => setStep((current) => Math.min(current + 1, STEPS.length - 1)), 2500)
    return () => clearInterval(timer)
  }, [])
  return (
    <div className="mx-auto flex max-w-md flex-col items-center px-4 py-16 text-center">
      <div className="flex size-14 items-center justify-center rounded-2xl bg-brand-50 text-brand-700">
        {failed ? <span className="text-xl">!</span> : <Loader2 className="size-7 animate-spin" />}
      </div>
      <h2 className="mt-5 text-xl font-semibold">{failed ? 'Не получилось собрать черновик' : 'Собираем черновик'}</h2>
      {failed ? (
        <>
          <p className="mt-2 text-sm text-muted">{failed}</p>
          <button type="button" onClick={onRetry} className="mt-4 cursor-pointer text-sm font-medium text-brand-700 underline">начать заново</button>
        </>
      ) : (
        <ul className="mt-6 w-full space-y-2 text-left">
          {STEPS.map((title, index) => (
            <li key={title} className={cn('flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors', index === step ? 'bg-white shadow-sm' : 'text-muted')}>
              {index < step ? <Check className="size-4 text-brand-600" /> : index === step ? <Loader2 className="size-4 animate-spin text-brand-600" /> : <span className="size-4" />}
              {title}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}