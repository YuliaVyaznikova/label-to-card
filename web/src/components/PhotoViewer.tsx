import { useState } from 'react'
import type { Evidence, Line, Photo } from '@/api'
import { cn } from '@/lib/utils'

type Props = { photos: Photo[]; lines: Line[]; highlights: Evidence[]; active: number; onActive: (number: number) => void }

export function PhotoViewer({ photos, lines, highlights, active, onActive }: Props) {
  const [showAll, setShowAll] = useState(false)
  const photo = photos.find((item) => item.number === active) ?? photos[0]
  if (!photo) return null
  const width = photo.width ?? 1000
  const height = photo.height ?? 1000
  const pad = Math.max(width, height) / 150
  const marks = highlights.filter((item) => item.photo === photo.number && item.box)
  const all = showAll ? lines.filter((line) => line.photo === photo.number) : []
  return (
    <div className="flex flex-col gap-3">
      <div className="relative overflow-hidden rounded-2xl border border-line bg-white">
        <img src={photo.url} alt={`Фото ${photo.number}`} className="block h-auto w-full" />
        <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className="pointer-events-none absolute inset-0 h-full w-full">
          {all.map((line) => (
            <rect key={line.id} x={line.box[0]} y={line.box[1]} width={line.box[2] - line.box[0]} height={line.box[3] - line.box[1]}
              fill="rgba(76,154,63,0.07)" stroke="rgba(58,127,48,0.55)" strokeWidth={width / 500} />
          ))}
          {marks.map((item, index) => {
            const [x1, y1, x2, y2] = item.box as number[]
            return (
              <rect key={index} x={x1 - pad} y={y1 - pad} width={x2 - x1 + 2 * pad} height={y2 - y1 + 2 * pad} rx={pad}
                fill="rgba(255,203,5,0.24)" stroke="#e0a800" strokeWidth={width / 200} />
            )
          })}
        </svg>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-2">
          {photos.map((item) => {
            const count = highlights.filter((mark) => mark.photo === item.number).length
            return (
              <button key={item.number} type="button" onClick={() => onActive(item.number)}
                className={cn('relative size-14 cursor-pointer overflow-hidden rounded-xl border-2 bg-white', item.number === photo.number ? 'border-brand-600' : 'border-transparent opacity-75 hover:opacity-100')}>
                <img src={item.url} alt="" className="size-full object-cover" />
                {count > 0 && <span className="absolute top-1 right-1 size-2.5 rounded-full bg-sun ring-2 ring-white" />}
              </button>
            )
          })}
        </div>
        <label className="flex cursor-pointer items-center gap-2 text-xs text-muted select-none">
          <input type="checkbox" checked={showAll} onChange={(event) => setShowAll(event.target.checked)} className="accent-brand-600" />
          весь распознанный текст
        </label>
      </div>
    </div>
  )
}