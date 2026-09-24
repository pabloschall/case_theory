import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api } from '../../services/api'
import type { CaseInvitation, CurrentUser, InvitationPreview } from '../../types'
import { InvitationPage } from './InvitationPage'
import { InviteCollaborators } from './InviteCollaborators'

const preview: InvitationPreview = { case_id: 'case-1', case_title: 'Fictional River Case', inviter_name: 'Pablo', role: 'contributor', expires_at: '2026-10-01T00:00:00Z', is_available: true, requires_account: true }
const user: CurrentUser = { id: 'user-1', email: 'friend@example.com', username: 'friend', display_name: 'Friend', bio: null, avatar_url: null, is_verified: true, plan_code: 'free', tier_level: 1, permissions: [], ai_cases_remaining: 1, ai_limit_period: 'weekly', ai_resets_at: '2026-01-05T00:00:00Z', weekly_cases_remaining: 1, weekly_case_limit: 1, weekly_cases_reset_at: '2026-01-05T00:00:00Z', created_at: '2026-01-01T00:00:00Z' }
const created: CaseInvitation = { id: 'invite-1', case_id: 'case-1', case_title: preview.case_title, inviter_name: 'Pablo', role: 'contributor', invite_url: 'http://localhost:5173/invite/secure-token', message: 'Pablo invited you to collaborate on “Fictional River Case” in Game Theory. Open the invitation: http://localhost:5173/invite/secure-token', expires_at: preview.expires_at }

function queryClient() { return new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } }) }

afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('case invitations', () => {
  it('preserves the invitation through signup and login', async () => {
    vi.spyOn(api, 'invitation').mockResolvedValue(preview)
    vi.spyOn(api, 'currentUser').mockRejectedValue(new ApiError(401, 'authentication_required', 'Authentication required'))
    render(<QueryClientProvider client={queryClient()}><MemoryRouter initialEntries={['/invite/secure-token']}><Routes><Route path="/invite/:token" element={<InvitationPage/>}/></Routes></MemoryRouter></QueryClientProvider>)
    expect(await screen.findByText('Fictional River Case')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Create account/ })).toHaveAttribute('href', '/register?next=%2Finvite%2Fsecure-token%3Faccept%3D1')
    expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/login?next=%2Finvite%2Fsecure-token%3Faccept%3D1')
  })

  it('accepts an invitation for a signed-in user', async () => {
    vi.spyOn(api, 'invitation').mockResolvedValue(preview)
    vi.spyOn(api, 'currentUser').mockResolvedValue(user)
    const accept = vi.spyOn(api, 'acceptInvitation').mockResolvedValue({ case_id: 'case-1', message: 'Accepted' })
    render(<QueryClientProvider client={queryClient()}><MemoryRouter initialEntries={['/invite/secure-token']}><Routes><Route path="/invite/:token" element={<InvitationPage/>}/><Route path="/cases/:caseId" element={<p>Case workspace</p>}/></Routes></MemoryRouter></QueryClientProvider>)
    fireEvent.click(await screen.findByRole('button', { name: 'Accept invitation' }))
    await waitFor(() => expect(accept).toHaveBeenCalledWith('secure-token'))
    expect(await screen.findByText('Case workspace')).toBeInTheDocument()
  })

  it('creates native text and email links', async () => {
    vi.spyOn(api, 'createCaseInvitation').mockResolvedValue(created)
    render(<QueryClientProvider client={queryClient()}><MemoryRouter><InviteCollaborators caseId="case-1"/></MemoryRouter></QueryClientProvider>)
    fireEvent.click(screen.getByRole('button', { name: /Invite person/ }))
    fireEvent.click(screen.getByRole('button', { name: /Create invitation link/ }))
    const textLink = await screen.findByRole('link', { name: /Open text message/ })
    expect(textLink.getAttribute('href')).toContain('sms:')
    expect(textLink.getAttribute('href')).toContain('Pablo%20invited')
    expect(screen.getByRole('link', { name: /Open email/ }).getAttribute('href')).toContain('mailto:')
  })
})
