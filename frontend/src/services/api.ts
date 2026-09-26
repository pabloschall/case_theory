import type { AdminCasePage, AdminUserListItem, AdminUserPage, ApiErrorBody, CaseDetail, CaseInvitation, CaseListItem, CaseListPage, CaseLocation, CaseNotebookNote, CasePerson, CaseTimelineEntry, CurrentUser, CursorPage, DirectConversation, DirectConversationSummary, DirectMessage, DiscussionThread, DiscussionThreadPage, Evidence, EvidenceComment, FBICase, FBICasePage, InvitationPreview, LocationType, MemberProfile, MessageAttachment, ModerationReport, ModerationReportPage, PersonNote, PersonRelationship, ReportReason, ReportResourceType, ResearchAction, ResearchChatResponse, TimelineEvent } from '../types'

const API_URL = import.meta.env.VITE_API_URL ?? '/api/v1'
let csrfToken: string | null = null

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public requestId?: string) { super(message) }
}

async function getCsrf(): Promise<string> {
  if (csrfToken) return csrfToken
  const response = await fetch(`${API_URL}/auth/csrf`, { credentials: 'include' })
  if (!response.ok) throw new ApiError(response.status, 'csrf_unavailable', 'Could not secure this request')
  const data = await response.json() as { csrf_token: string }
  csrfToken = data.csrf_token
  return csrfToken
}

async function parseError(response: Response): Promise<ApiError> {
  const body = await response.json().catch(() => ({})) as ApiErrorBody
  return new ApiError(response.status, body.error?.code ?? 'request_failed', body.error?.message ?? 'Something went wrong', body.error?.request_id)
}

async function request<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const method = options.method?.toUpperCase() ?? 'GET'
  const headers = new Headers(options.headers)
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) headers.set('X-CSRF-Token', await getCsrf())
  if (options.body) headers.set('Content-Type', 'application/json')
  const response = await fetch(`${API_URL}${path}`, { ...options, headers, credentials: 'include' })
  if (response.status === 401 && retry && path !== '/auth/refresh' && path !== '/auth/login') {
    const refreshed = await request<{ message: string }>('/auth/refresh', { method: 'POST' }, false).then(() => true).catch(() => false)
    if (refreshed) return request<T>(path, options, false)
  }
  if (!response.ok) throw await parseError(response)
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  currentUser: () => request<CurrentUser>('/users/me'),
  updateProfile: (data: { display_name: string; username: string; bio: string }) => request<CurrentUser>('/users/me', { method: 'PATCH', body: JSON.stringify(data) }),
  requestAvatarUpload: (data: { filename: string; content_type: string; file_size: number }) => request<{ upload_id: string; upload_url: string; upload_method: string; upload_headers: Record<string, string> }>('/users/me/avatar', { method: 'POST', body: JSON.stringify(data) }),
  completeAvatarUpload: (uploadId: string) => request<CurrentUser>(`/users/me/avatar/${uploadId}/complete`, { method: 'POST' }),
  blockedUsers: () => request<MemberProfile[]>('/users/me/blocked'),
  blockUser: (userId: string) => request<{ is_blocked: boolean }>(`/users/${userId}/block`, { method: 'POST' }),
  unblockUser: (userId: string) => request<{ is_blocked: boolean }>(`/users/${userId}/block`, { method: 'DELETE' }),
  login: (data: { email: string; password: string }) => request<{ message: string }>('/auth/login', { method: 'POST', body: JSON.stringify(data) }),
  register: (data: { email: string; username: string; display_name: string; password: string; confirm_age_18: true; accept_terms: true; accept_community_standards: true }) => request<{ message: string }>('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  requestEmailVerification: (email: string) => request<{ message: string }>('/auth/email-verification/request', { method: 'POST', body: JSON.stringify({ email }) }),
  confirmEmail: (token: string) => request<{ message: string }>('/auth/email-verification/confirm', { method: 'POST', body: JSON.stringify({ token }) }),
  forgotPassword: (email: string) => request<{ message: string }>('/auth/password/forgot', { method: 'POST', body: JSON.stringify({ email }) }),
  resetPassword: (data: { token: string; password: string }) => request<{ message: string }>('/auth/password/reset', { method: 'POST', body: JSON.stringify(data) }),
  logout: () => request<{ message: string }>('/auth/logout', { method: 'POST' }),
  searchCases: (query = '', sort: 'newest' | 'popular' = 'newest', page = 1, pageSize = 12) => {
    const params = new URLSearchParams({ sort, page: String(page), page_size: String(pageSize) })
    if (query) params.set('q', query)
    return request<CaseListPage>(`/cases?${params.toString()}`)
  },
  followingCases: () => request<CaseListItem[]>('/cases/following'),
  myCases: () => request<CaseListItem[]>('/cases/mine'),
  followCase: (id: string) => request<{ is_following: boolean }>(`/cases/${id}/follow`, { method: 'POST' }),
  unfollowCase: (id: string) => request<{ is_following: boolean }>(`/cases/${id}/follow`, { method: 'DELETE' }),
  createCase: (data: { victim_names: string; year?: number; location?: string; additional_context?: string; creation_mode: 'ai' | 'manual'; summary?: string; banner_template?: string; privacy: 'public' | 'private' }) => request<CaseDetail>('/cases', { method: 'POST', body: JSON.stringify(data) }),
  case: (id: string) => request<CaseDetail>(`/cases/${id}`),
  researchCase: (id: string) => request<{ job_id: string; status: string }>(`/cases/${id}/research`, { method: 'POST' }),
  researchChat: (id: string, data: { message: string; history: { role: 'user' | 'assistant'; content: string }[] }) => request<ResearchChatResponse>(`/cases/${id}/research-chat`, { method: 'POST', body: JSON.stringify(data) }),
  executeResearchAction: (caseId: string, action: ResearchAction) => {
    const expectedEndpoints: Record<ResearchAction['action_type'], string> = {
      timeline: `/cases/${caseId}/timeline`,
      thread: `/cases/${caseId}/discussions`,
      evidence: `/cases/${caseId}/evidence/links`,
    }
    if (action.endpoint !== expectedEndpoints[action.action_type] || action.method !== 'POST') throw new Error('The proposed research action is invalid.')
    return request<unknown>(action.endpoint, { method: action.method, body: JSON.stringify(action.payload) })
  },
  updateCasePrivacy: (id: string, privacy: 'public' | 'private') => request<CaseDetail>(`/cases/${id}/privacy`, { method: 'PATCH', body: JSON.stringify({ privacy }) }),
  createCaseInvitation: (caseId: string) => request<CaseInvitation>(`/cases/${caseId}/invitations`, { method: 'POST', body: JSON.stringify({ role: 'contributor' }) }),
  invitation: (token: string) => request<InvitationPreview>(`/invitations/${token}`),
  acceptInvitation: (token: string) => request<{ case_id: string; message: string }>(`/invitations/${token}/accept`, { method: 'POST' }),
  memberProfile: (userId: string) => request<MemberProfile>(`/users/${userId}`),
  conversations: (cursor?: string, limit = 20) => {
    const params = new URLSearchParams({ limit: String(limit) })
    if (cursor) params.set('cursor', cursor)
    return request<CursorPage<DirectConversationSummary>>(`/messages/conversations?${params.toString()}`)
  },
  unreadMessages: () => request<{ has_unread: boolean }>('/messages/unread'),
  markConversationRead: (conversationId: string, messageId: string) => request<void>(`/messages/conversations/${conversationId}/read?message_id=${messageId}`, { method: 'POST' }),
  conversation: (id: string, cursor?: string, limit = 30) => {
    const params = new URLSearchParams({ limit: String(limit) })
    if (cursor) params.set('cursor', cursor)
    return request<DirectConversation>(`/messages/conversations/${id}?${params.toString()}`)
  },
  openConversation: (recipientUserId: string) => request<DirectConversation>('/messages/conversations', { method: 'POST', body: JSON.stringify({ recipient_user_id: recipientUserId }) }),
  sendDirectMessage: (conversationId: string, data: { body: string; attachment_ids: string[] }) => request<DirectMessage>(`/messages/conversations/${conversationId}/messages`, { method: 'POST', body: JSON.stringify(data) }),
  requestMessageAttachment: (conversationId: string, data: { filename: string; content_type: string; file_size: number }) => request<{ attachment: MessageAttachment; upload_url: string; upload_method: string; upload_headers: Record<string, string> }>(`/messages/conversations/${conversationId}/attachments`, { method: 'POST', body: JSON.stringify(data) }),
  completeMessageAttachment: (conversationId: string, attachmentId: string) => request<MessageAttachment>(`/messages/conversations/${conversationId}/attachments/${attachmentId}/complete`, { method: 'POST' }),
  messageAttachmentUrl: (conversationId: string, attachmentId: string) => request<{ url: string }>(`/messages/conversations/${conversationId}/attachments/${attachmentId}/url`),
  createTimelineEvent: (caseId: string, data: { occurred_on: string; title: string; description: string; evidence_ids?: string[]; person_ids?: string[] }) => request<TimelineEvent>(`/cases/${caseId}/timeline`, { method: 'POST', body: JSON.stringify(data) }),
  discussionThreads: (caseId: string, cursor?: string, limit = 10) => {
    const params = new URLSearchParams({ limit: String(limit) })
    if (cursor) params.set('cursor', cursor)
    return request<DiscussionThreadPage>(`/cases/${caseId}/discussions?${params.toString()}`)
  },
  createDiscussionThread: (caseId: string, data: { title: string; body: string; thread_type: DiscussionThread['thread_type']; evidence_ids?: string[]; person_ids?: string[] }) => request<DiscussionThread>(`/cases/${caseId}/discussions`, { method: 'POST', body: JSON.stringify(data) }),
  toggleDiscussionVote: (caseId: string, threadId: string) => request<{ vote_count: number; voted_by_me: boolean }>(`/cases/${caseId}/discussions/${threadId}/vote`, { method: 'POST' }),
  addDiscussionComment: (caseId: string, threadId: string, data: { body: string }) => request<DiscussionThread>(`/cases/${caseId}/discussions/${threadId}/comments`, { method: 'POST', body: JSON.stringify(data) }),
  toggleDiscussionReaction: (caseId: string, threadId: string, commentId: string, emoji: string) => request<DiscussionThread>(`/cases/${caseId}/discussions/${threadId}/comments/${commentId}/reactions`, { method: 'POST', body: JSON.stringify({ emoji }) }),
  evidence: (caseId: string, cursor?: string, limit = 12) => {
    const params = new URLSearchParams({ limit: String(limit) })
    if (cursor) params.set('cursor', cursor)
    return request<CursorPage<Evidence>>(`/cases/${caseId}/evidence?${params.toString()}`)
  },
  createEvidenceLink: (caseId: string, data: { title: string; description?: string; url: string; evidence_type: string; person_ids?: string[] }) => request<Evidence>(`/cases/${caseId}/evidence/links`, { method: 'POST', body: JSON.stringify(data) }),
  requestEvidenceUpload: (caseId: string, data: { title: string; description?: string; filename: string; content_type: string; file_size: number; person_ids?: string[] }) => request<{ evidence: Evidence; upload_url: string; upload_method: 'POST' | 'PUT'; upload_headers: Record<string, string> }>(`/cases/${caseId}/evidence/uploads`, { method: 'POST', body: JSON.stringify(data) }),
  completeEvidenceUpload: (caseId: string, evidenceId: string) => request<Evidence>(`/cases/${caseId}/evidence/${evidenceId}/complete`, { method: 'POST' }),
  evidenceUrl: (caseId: string, evidenceId: string) => request<{ url: string }>(`/cases/${caseId}/evidence/${evidenceId}/url`),
  evidenceComments: (caseId: string, evidenceId: string, cursor?: string, limit = 20) => {
    const params = new URLSearchParams({ limit: String(limit) })
    if (cursor) params.set('cursor', cursor)
    return request<CursorPage<EvidenceComment>>(`/cases/${caseId}/evidence/${evidenceId}/comments?${params.toString()}`)
  },
  createEvidenceComment: (caseId: string, evidenceId: string, body: string) => request<EvidenceComment>(`/cases/${caseId}/evidence/${evidenceId}/comments`, { method: 'POST', body: JSON.stringify({ body }) }),
  deleteEvidenceComment: (caseId: string, evidenceId: string, commentId: string) => request<void>(`/cases/${caseId}/evidence/${evidenceId}/comments/${commentId}`, { method: 'DELETE' }),
  notebookNotes: (caseId: string, cursor?: string, limit = 20) => {
    const params = new URLSearchParams({ limit: String(limit) })
    if (cursor) params.set('cursor', cursor)
    return request<CursorPage<CaseNotebookNote>>(`/cases/${caseId}/notes?${params.toString()}`)
  },
  createNotebookNote: (caseId: string, data: { title: string; body: string }) => request<CaseNotebookNote>(`/cases/${caseId}/notes`, { method: 'POST', body: JSON.stringify(data) }),
  updateNotebookNote: (caseId: string, noteId: string, data: { title: string; body: string }) => request<CaseNotebookNote>(`/cases/${caseId}/notes/${noteId}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteNotebookNote: (caseId: string, noteId: string) => request<void>(`/cases/${caseId}/notes/${noteId}`, { method: 'DELETE' }),
  caseTimelineEntries: (caseId: string) => request<CaseTimelineEntry[]>(`/cases/${caseId}/my-timeline`),
  createCaseTimelineEntry: (caseId: string, data: { occurred_on: string; title: string; body: string }) => request<CaseTimelineEntry>(`/cases/${caseId}/my-timeline`, { method: 'POST', body: JSON.stringify(data) }),
  updateCaseTimelineEntry: (caseId: string, entryId: string, data: { occurred_on: string; title: string; body: string }) => request<CaseTimelineEntry>(`/cases/${caseId}/my-timeline/${entryId}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteCaseTimelineEntry: (caseId: string, entryId: string) => request<void>(`/cases/${caseId}/my-timeline/${entryId}`, { method: 'DELETE' }),
  createReport: (data: { resource_type: ReportResourceType; resource_id: string; reason_code: ReportReason; details: string }) => request<ModerationReport>('/reports', { method: 'POST', body: JSON.stringify(data) }),
  adminReports: (status = 'pending', page = 1, pageSize = 20) => request<ModerationReportPage>(`/admin/reports?${new URLSearchParams({ status, page: String(page), page_size: String(pageSize) }).toString()}`),
  moderateReport: (reportId: string, action: 'hide' | 'restore' | 'lock_user' | 'unlock_user' | 'resolve' | 'dismiss', note?: string) => request<ModerationReport>(`/admin/reports/${reportId}`, { method: 'PATCH', body: JSON.stringify({ action, note: note || null }) }),
  attachTimelineEvidence: (caseId: string, timelineEventId: string, evidenceId: string) => request<void>(`/cases/${caseId}/evidence/timeline/${timelineEventId}`, { method: 'POST', body: JSON.stringify({ evidence_id: evidenceId }) }),
  people: (caseId: string) => request<CasePerson[]>(`/cases/${caseId}/people`),
  createPerson: (caseId: string, data: { name: string; role: string; category: CasePerson['category']; entity_type: CasePerson['entity_type']; summary?: string }) => request<CasePerson>(`/cases/${caseId}/people`, { method: 'POST', body: JSON.stringify(data) }),
  relationships: (caseId: string) => request<PersonRelationship[]>(`/cases/${caseId}/relationships`),
  person: (caseId: string, personId: string) => request<CasePerson>(`/cases/${caseId}/people/${personId}`),
  personEvidence: (caseId: string, personId: string) => request<Evidence[]>(`/cases/${caseId}/people/${personId}/evidence`),
  attachPersonEvidence: (caseId: string, personId: string, evidenceId: string) => request<void>(`/cases/${caseId}/people/${personId}/evidence`, { method: 'POST', body: JSON.stringify({ evidence_id: evidenceId }) }),
  personNotes: (caseId: string, personId: string) => request<PersonNote[]>(`/cases/${caseId}/people/${personId}/notes`),
  createPersonNote: (caseId: string, personId: string, body: string) => request<PersonNote>(`/cases/${caseId}/people/${personId}/notes`, { method: 'POST', body: JSON.stringify({ body }) }),
  updatePersonNote: (caseId: string, personId: string, noteId: string, body: string) => request<PersonNote>(`/cases/${caseId}/people/${personId}/notes/${noteId}`, { method: 'PATCH', body: JSON.stringify({ body }) }),
  deletePersonNote: (caseId: string, personId: string, noteId: string) => request<void>(`/cases/${caseId}/people/${personId}/notes/${noteId}`, { method: 'DELETE' }),
  reviewRelationship: (caseId: string, relationshipId: string, review_status: 'confirmed' | 'rejected') => request<PersonRelationship>(`/cases/${caseId}/relationships/${relationshipId}`, { method: 'PATCH', body: JSON.stringify({ review_status }) }),
  locations: (caseId: string) => request<CaseLocation[]>(`/cases/${caseId}/locations`),
  createLocation: (caseId: string, data: { name: string; description: string; latitude: number; longitude: number; location_type: LocationType; occurred_on?: string | null; precision: 'exact' | 'approximate'; verification_status: 'verified' | 'source_backed' | 'unverified' | 'disputed'; source_url?: string; evidence_ids?: string[]; person_ids?: string[] }) => request<CaseLocation>(`/cases/${caseId}/locations`, { method: 'POST', body: JSON.stringify(data) }),
  reviewLocation: (caseId: string, locationId: string, review_status: 'confirmed' | 'rejected') => request<CaseLocation>(`/cases/${caseId}/locations/${locationId}`, { method: 'PATCH', body: JSON.stringify({ review_status }) }),
  adminUsers: (query = '', page = 1, pageSize = 20) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
    if (query) params.set('q', query)
    return request<AdminUserPage>(`/admin/users?${params.toString()}`)
  },
  createAdminUser: (data: { email: string; username: string; display_name: string; password: string }) => request<AdminUserListItem>('/admin/users', { method: 'POST', body: JSON.stringify(data) }),
  updateAdminUserTier: (userId: string, tierLevel: 0 | 1 | 2 | 3) => request<AdminUserListItem>(`/admin/users/${userId}/tier`, { method: 'PATCH', body: JSON.stringify({ tier_level: tierLevel }) }),
  deleteAdminUser: (userId: string) => request<{ message: string }>(`/admin/users/${userId}`, { method: 'DELETE' }),
  adminCases: (query = '', page = 1, pageSize = 20) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
    if (query) params.set('q', query)
    return request<AdminCasePage>(`/admin/cases?${params.toString()}`)
  },
  deleteCase: (id: string) => request<{ message: string }>(`/admin/cases/${id}`, { method: 'DELETE' }),
  fbiCases: (params: { page: number; q?: string; field_office?: string; classification?: string; status?: string }) => {
    const search = new URLSearchParams({ page: String(params.page) })
    if (params.q) search.set('q', params.q)
    if (params.field_office) search.set('field_office', params.field_office)
    if (params.classification) search.set('classification', params.classification)
    if (params.status) search.set('status', params.status)
    return request<FBICasePage>(`/integrations/fbi/cases?${search.toString()}`)
  },
  fbiCase: (externalId: string) => request<FBICase>(`/integrations/fbi/cases/${externalId}`),
  importFbiCase: (externalId: string) => request<{ already_imported: boolean; case_id: string; message: string }>(`/integrations/fbi/cases/${externalId}/import`, { method: 'POST' }),
  enrichFbiCase: (caseId: string) => request<{ job_id: string; status: string }>(`/integrations/fbi/imports/${caseId}/enrich`, { method: 'POST' }),
}
