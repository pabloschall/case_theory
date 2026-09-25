import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Evidence } from '../../types'
import { EvidenceCard } from './EvidenceCard'

const evidence: Evidence = {
  id: 'evidence-1',
  title: 'Public interview recording',
  description: 'An official public interview preserved as a case reference.',
  evidence_type: 'video',
  original_filename: null,
  mime_type: null,
  file_size: null,
  source_url: 'https://www.youtube.com/watch?v=abcdefghijk',
  source_id: null,
  verification_status: 'source_backed',
  processing_status: 'available',
  ai_generated: false,
  review_status: 'confirmed',
  comment_count: 0,
  created_at: '2026-09-23T12:00:00Z',
}

afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('EvidenceCard', () => {
  it('opens evidence in the in-app viewer and keeps the original as a secondary link', () => {
    const externalOpen = vi.spyOn(window, 'open')
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(<QueryClientProvider client={queryClient}><EvidenceCard caseId="case-1" item={evidence}/></QueryClientProvider>)

    fireEvent.click(screen.getByRole('button', { name: /Public interview recording/ }))

    const dialog = screen.getByRole('dialog', { name: 'Public interview recording' })
    expect(dialog).toBeInTheDocument()
    const preview = screen.getByTitle('Public interview recording evidence preview')
    expect(preview).toHaveAttribute('src', 'https://www.youtube-nocookie.com/embed/abcdefghijk')
    expect(preview).toHaveAttribute('referrerpolicy', 'strict-origin-when-cross-origin')
    expect(screen.getByRole('link', { name: /Open original source/ })).toHaveAttribute('href', evidence.source_url)
    expect(externalOpen).not.toHaveBeenCalled()
  })

  it('opens generic web evidence through the publisher instead of a blocked iframe', () => {
    const article = {
      ...evidence,
      id: 'evidence-article',
      title: 'AP News report',
      evidence_type: 'article',
      source_url: 'https://apnews.com/article/example',
    }
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(<QueryClientProvider client={queryClient}><EvidenceCard caseId="case-1" item={article}/></QueryClientProvider>)

    fireEvent.click(screen.getByRole('button', { name: /AP News report/ }))

    expect(screen.getByText('View this source on its website')).toBeInTheDocument()
    expect(screen.queryByTitle('AP News report evidence preview')).not.toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /Open original source/ })).toHaveLength(2)
    for (const link of screen.getAllByRole('link', { name: /Open original source/ })) {
      expect(link).toHaveAttribute('href', article.source_url)
    }
  })
})
