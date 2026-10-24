import { cn } from '@/lib/utils'

const STRIPES = [
  ['#2b6030', 18], ['#238441', 9], ['#6aa744', 14], ['#a6ce39', 7], ['#ffcb05', 4], ['#6aa744', 11], ['#238441', 22], ['#a6ce39', 15],
] as const

export function Logo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden="true">
      <rect x="2" y="2" width="60" height="60" rx="15" fill="#2b6030" />
      <g stroke="#ffcb05" strokeWidth="4.5" fill="none" strokeLinecap="round">
        <path d="M12 22 V17 Q12 12 17 12 H22" />
        <path d="M42 12 H47 Q52 12 52 17 V22" />
        <path d="M52 42 V47 Q52 52 47 52 H42" />
        <path d="M22 52 H17 Q12 52 12 47 V42" />
      </g>
      <path d="M32 45 V31" stroke="#a6ce39" strokeWidth="3.2" strokeLinecap="round" />
      <path d="M32 33 C32 26 37 21 44 21 C44 28 39 33 32 33 Z" fill="#a6ce39" />
      <path d="M32 37 C32 31 28 27 21 27 C21 33 25 37 32 37 Z" fill="#6aa744" />
    </svg>
  )
}

export function Stripes({ className }: { className?: string }) {
  return (
    <div className={cn('brand-stripes flex h-1', className)} aria-hidden="true">
      {STRIPES.map(([color, width], index) => <span key={index} style={{ background: color, flex: width }} />)}
    </div>
  )
}