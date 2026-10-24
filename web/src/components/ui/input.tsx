import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils'

const base = 'w-full rounded-xl border border-line bg-white px-3.5 text-sm text-ink placeholder:text-stone-400 focus-visible:border-brand-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/20 disabled:opacity-60'

export function Input({ className, ...props }: ComponentProps<'input'>) {
  return <input className={cn(base, 'h-11', className)} {...props} />
}

export function Textarea({ className, ...props }: ComponentProps<'textarea'>) {
  return <textarea className={cn(base, 'min-h-20 py-2 leading-relaxed', className)} {...props} />
}

export function Select({ className, ...props }: ComponentProps<'select'>) {
  return <select className={cn(base, 'h-11 cursor-pointer', className)} {...props} />
}