import type { components } from './schema'

type Schemas = components['schemas']
export type Draft = Schemas['DraftOut']
export type FieldOut = Schemas['FieldOut']
export type Evidence = Schemas['Evidence']
export type Photo = Schemas['PhotoOut']
export type Line = Schemas['LineOut']
export type Issue = Schemas['IssueOut']
export type LogEntry = Schemas['LogOut']
export type CategoryInfo = Schemas['CategoryInfo']
export type Created = Schemas['Created']
export type Hints = { category?: string; price?: string; weight?: string; notes?: string }

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(typeof body.detail === 'string' ? body.detail : `Ошибка ${response.status}`)
  }
  return response.json() as Promise<T>
}

export const api = {
  categories: () => request<CategoryInfo[]>('/v1/categories'),
  create: (photos: File[], hints: Hints) => {
    const form = new FormData()
    photos.forEach((photo) => form.append('photos', photo))
    form.append('hints', JSON.stringify(hints))
    return request<Created>('/v1/drafts', { method: 'POST', body: form })
  },
  draft: (id: string) => request<Draft>(`/v1/drafts/${id}`),
  edit: (id: string, fields: Record<string, string>) =>
    request<Draft>(`/v1/drafts/${id}/fields`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ fields }) }),
  addPhoto: (id: string, photo: File) => {
    const form = new FormData()
    form.append('photo', photo)
    return request<Created>(`/v1/drafts/${id}/photos`, { method: 'POST', body: form })
  },
  confirm: (id: string) => request<Draft>(`/v1/drafts/${id}/confirm`, { method: 'POST' }),
}