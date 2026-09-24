import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api } from '../../services/api'
import type { FBICase, FBICasePage, CurrentUser } from '../../types'
import { FBICaseBrowserPage } from './FBICaseBrowserPage'

const user: CurrentUser = { id: 'user-1', email: 'paid@example.com', username: 'paid', display_name: 'Paid User', bio: null, avatar_url: null, is_verified: true, plan_code: 'lead', tier_level: 3, permissions: ['case.import'], ai_cases_remaining: 5, ai_limit_period: 'weekly', ai_resets_at: '2026-01-05T00:00:00Z', weekly_cases_remaining: 5, weekly_case_limit: 5, weekly_cases_reset_at: '2026-01-05T00:00:00Z', created_at: '2026-01-01T00:00:00Z' }
const fbiCase: FBICase = { external_id: 'fbi-1', title: 'Taylor Example', description: 'Seeking information in a public case.', details: 'Official case details.', remarks: null, caution: null, warning_message: null, reward_text: null, status: 'na', classification: 'Victim', subjects: ['Missing Person'], aliases: [], dates_of_birth: [], place_of_birth: null, nationality: null, sex: null, race: null, hair: null, eyes: null, field_offices: ['phoenix'], locations: [], publication: '2025-01-01T00:00:00Z', modified: null, source_url: 'https://www.fbi.gov/wanted/example', image_url: null, already_imported: false, imported_case_id: null }
const page = (overrides: Partial<FBICasePage> = {}): FBICasePage => ({ items: [fbiCase], page: 1, total: 1, has_next: false, ...overrides })

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter><FBICaseBrowserPage /></MemoryRouter></QueryClientProvider>)
}

afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('FBI case browser', () => {
  it('shows the investigative loading state', async () => {
    vi.spyOn(api, 'currentUser').mockResolvedValue(user)
    vi.spyOn(api, 'fbiCases').mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(await screen.findByText('Searching FBI case files...')).toBeInTheDocument()
  })

  it('shows empty and upstream error states', async () => {
    vi.spyOn(api, 'currentUser').mockResolvedValue(user)
    vi.spyOn(api, 'fbiCases').mockResolvedValueOnce(page({ items: [], total: 0 }))
    const view = renderPage()
    expect(await screen.findByText('No matching case files')).toBeInTheDocument()
    view.unmount()
    vi.mocked(api.fbiCases).mockRejectedValueOnce(new ApiError(503, 'fbi_api_unavailable', 'FBI case discovery is temporarily unavailable'))
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent('temporarily unavailable')
  })

  it('debounces search and supports pagination', async () => {
    vi.spyOn(api, 'currentUser').mockResolvedValue(user)
    const list = vi.spyOn(api, 'fbiCases').mockResolvedValue(page({ has_next: true, total: 40 }))
    renderPage()
    await screen.findByText('Taylor Example')
    fireEvent.change(screen.getByLabelText('Search FBI cases'), { target: { value: 'Taylor' } })
    await waitFor(() => expect(list).toHaveBeenCalledWith(expect.objectContaining({ q: 'Taylor' })), { timeout: 1000 })
    fireEvent.click(screen.getByRole('button', { name: /Next/ }))
    await waitFor(() => expect(list).toHaveBeenCalledWith(expect.objectContaining({ page: 2 })))
  })

  it('opens a preview and imports a case', async () => {
    vi.spyOn(api, 'currentUser').mockResolvedValue(user)
    vi.spyOn(api, 'fbiCases').mockResolvedValue(page())
    const importer = vi.spyOn(api, 'importFbiCase').mockResolvedValue({ already_imported: false, case_id: 'case-1', message: 'Imported' })
    renderPage()
    await screen.findByText('Taylor Example')
    fireEvent.click(screen.getByRole('button', { name: 'View' }))
    expect(screen.getByRole('dialog')).toHaveTextContent('Official case details.')
    fireEvent.click(screen.getAllByRole('button', { name: 'Import Case' }).at(-1)!)
    await waitFor(() => expect(importer).toHaveBeenCalledWith('fbi-1'))
  })

  it('shows an already-imported case instead of an import action', async () => {
    vi.spyOn(api, 'currentUser').mockResolvedValue(user)
    vi.spyOn(api, 'fbiCases').mockResolvedValue(page({ items: [{ ...fbiCase, already_imported: true, imported_case_id: 'case-existing' }] }))
    renderPage()
    const link = await screen.findByRole('link', { name: /Imported/ })
    expect(link).toHaveAttribute('href', '/cases/case-existing')
  })
})
