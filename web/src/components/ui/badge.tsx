import { cva, type VariantProps } from 'class-variance-authority'
import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils'

const badgeVariants = cva('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium whitespace-nowrap [&_svg]:size-3', {
  variants: {
    tone: {
      photo: 'bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200',
      farmer: 'bg-sky-50 text-sky-800 ring-1 ring-sky-200',
      edited: 'bg-sky-50 text-sky-800 ring-1 ring-sky-200',
      none: 'bg-stone-100 text-stone-600 ring-1 ring-stone-200',
      conflict: 'bg-rose-50 text-rose-800 ring-1 ring-rose-200',
      block: 'bg-rose-50 text-rose-800 ring-1 ring-rose-200',
      warning: 'bg-amber-50 text-amber-800 ring-1 ring-amber-200',
      neutral: 'bg-white text-muted ring-1 ring-line',
      brand: 'bg-brand-50 text-brand-700 ring-1 ring-brand-200',
    },
  },
  defaultVariants: { tone: 'neutral' },
})

export function Badge({ className, tone, ...props }: ComponentProps<'span'> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />
}