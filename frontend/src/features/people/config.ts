import type { PersonCategory } from '../../types'

export const categoryConfig: Record<PersonCategory, { label: string; dot: string; ring: string; color: string; muted: string }> = {
  primary: { label: 'Primary', dot: 'bg-danger', ring: 'border-danger', color: 'var(--status-danger)', muted: 'rgba(201,93,93,.14)' },
  family: { label: 'Family', dot: 'bg-blue', ring: 'border-blue', color: 'var(--accent-blue)', muted: 'var(--accent-blue-muted)' },
  friend: { label: 'Friends', dot: 'bg-teal', ring: 'border-teal', color: 'var(--accent-teal)', muted: 'var(--accent-teal-muted)' },
  law_enforcement: { label: 'Law Enforcement', dot: 'bg-purple', ring: 'border-purple', color: 'var(--accent-purple)', muted: 'var(--accent-purple-muted)' },
  witness: { label: 'Witnesses', dot: 'bg-warning', ring: 'border-warning', color: 'var(--status-warning)', muted: 'rgba(215,162,76,.14)' },
  other: { label: 'Others', dot: 'bg-muted', ring: 'border-muted', color: 'var(--text-muted)', muted: 'rgba(117,129,140,.12)' },
}

export const categoryOrder: PersonCategory[] = ['primary', 'family', 'friend', 'law_enforcement', 'witness', 'other']

export function relationshipColor(type: string) {
  const value = type.toLowerCase()
  if (/mother|father|parent|family|sibling|relative/.test(value)) return 'var(--accent-blue)'
  if (/friend|neighbor|coworker|employer/.test(value)) return 'var(--accent-teal)'
  if (/partner|romantic|spouse/.test(value)) return 'var(--status-danger)'
  if (/witness|saw|reported/.test(value)) return 'var(--status-warning)'
  if (/police|investigat|interview|law/.test(value)) return 'var(--accent-purple)'
  return 'var(--text-muted)'
}
