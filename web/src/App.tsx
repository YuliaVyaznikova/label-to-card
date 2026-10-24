import { useCallback, useEffect, useState } from 'react'
import { api, type Draft } from '@/api'
import { Done } from '@/screens/Done'
import { Processing } from '@/screens/Processing'
import { Review } from '@/screens/Review'
import { Upload } from '@/screens/Upload'

function currentId() {
  const match = window.location.hash.match(/^#\/d\/(\w+)/)
  return match ? match[1] : null
}

export default function App() {
  const [id, setId] = useState<string | null>(currentId)
  const [draft, setDraft] = useState<Draft | null>(null)
  const [failed, setFailed] = useState<string | null>(null)
  const [round, setRound] = useState(0)

  useEffect(() => {
    const onHash = () => setId(currentId())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  const open = useCallback((next: string | null) => {
    window.location.hash = next ? `/d/${next}` : ''
    setDraft(null)
    setFailed(null)
    setId(next)
  }, [])

  useEffect(() => {
    if (!id) return
    let stopped = false
    const poll = async () => {
      try {
        const next = await api.draft(id)
        if (stopped) return
        if (next.status === 'processing') {
          setTimeout(poll, 1500)
        } else if (next.status === 'failed') {
          setFailed(next.error ?? 'Ошибка обработки')
        } else {
          setDraft(next)
        }
      } catch (problem) {
        if (!stopped) setFailed((problem as Error).message)
      }
    }
    poll()
    return () => {
      stopped = true
    }
  }, [id, round])

  const reprocess = () => {
    setDraft(null)
    setRound((value) => value + 1)
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-3">
          <button type="button" onClick={() => open(null)} className="flex cursor-pointer items-center gap-2">
            <span className="flex size-7 items-center justify-center rounded-lg bg-brand-600 text-xs font-bold text-white">3′</span>
            <span className="text-sm font-semibold">Карточка за три минуты</span>
          </button>
          <span className="ml-auto hidden text-xs text-muted sm:inline">прототип для «Своё Родное»</span>
        </div>
      </header>
      {!id && <Upload onCreated={open} />}
      {id && !draft && <Processing failed={failed} onRetry={() => open(null)} />}
      {id && draft && (draft.status === 'confirmed' || draft.status === 'sent') && <Done draft={draft} onNew={() => open(null)} />}
      {id && draft && draft.status !== 'confirmed' && draft.status !== 'sent' && (
        <Review draft={draft} onDraft={setDraft} onReprocess={reprocess} onBack={() => open(null)} />
      )}
    </div>
  )
}