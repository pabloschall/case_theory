export type CurrentUser = {
  id: string
  email: string
  username: string
  display_name: string
  bio: string | null
  avatar_url: string | null
  is_verified: boolean
  plan_code: string
  tier_level: number
  permissions: string[]
  ai_cases_remaining: number | null
  ai_limit_period: string
  ai_resets_at: string | null
  weekly_cases_remaining: number | null
  weekly_case_limit: number
  weekly_cases_reset_at: string | null
  created_at: string
}

export type ProgressionRank = { code: string; name: string; threshold: number; icon_key: string }
export type ProgressionBadge = { code: string; name: string; description: string; criteria: string; category: string; icon_key: string; earned_at: string | null }
export type XpReceipt = { id: string; xp: number; reason: string; created_at: string }
export type ProgressionSummary = { lifetime_xp: number; show_rank: boolean; show_badges: boolean; rank: ProgressionRank; next_rank: ProgressionRank | null; progress_percent: number; xp_to_next_rank: number | null; badges: ProgressionBadge[]; pending_badges: ProgressionBadge[]; pending_receipts: XpReceipt[] }
export type ProgressionLedgerPage = { items: { id: string; rule_code: string; xp: number; reason: string; resource_type: string | null; resource_id: string | null; created_at: string }[]; page: number; page_size: number; total: number; total_pages: number }

export type ApiErrorBody = { error?: { code?: string; message?: string; request_id?: string } }

export type CursorPage<T> = {
  items: T[]
  next_cursor: string | null
  has_more: boolean
  total: number
}

export type DiscussionThreadPage = CursorPage<DiscussionThread> & {
  active_count: number
  source_link_count: number
  comment_count: number
}

export type CaseInvitation = {
  id: string
  case_id: string
  case_title: string
  inviter_name: string
  role: 'contributor'
  invite_url: string
  message: string
  expires_at: string
}

export type InvitationPreview = {
  case_id: string
  case_title: string
  inviter_name: string
  role: 'contributor'
  expires_at: string
  is_available: boolean
  requires_account: boolean
}

export type MemberProfile = {
  id: string
  username: string
  display_name: string
  bio: string | null
  avatar_url: string | null
  is_blocked_by_me: boolean
}

export type DirectMessage = {
  id: string
  sender: MemberProfile
  body: string
  attachments: MessageAttachment[]
  created_at: string
}

export type DirectConversationSummary = {
  id: string
  other_user: MemberProfile
  last_message: string | null
  updated_at: string
  has_unread: boolean
}

export type DirectConversation = DirectConversationSummary & {
  messages: DirectMessage[]
  next_cursor: string | null
  has_more: boolean
  total_messages: number
}

export type MessageAttachment = {
  id: string
  original_filename: string
  mime_type: string
  file_size: number
  status: string
}

export type CaseListItem = {
  id: string
  slug: string
  title: string
  victim_names: string
  year: number | null
  location: string | null
  privacy: 'public' | 'private'
  is_owner: boolean
  is_following: boolean
  ai_research_status: string
  cover_image_url: string | null
  discussion_count: number
  created_at: string
  updated_at: string
}

export type CaseListPage = {
  items: CaseListItem[]
  page: number
  page_size: number
  total: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

export type TimelineEvent = {
  id: string
  date_label: string
  occurred_on: string | null
  occurred_time: string | null
  position: number | null
  date_precision: 'exact' | 'month' | 'year' | 'approximate' | 'unknown' | string
  title: string
  description: string
  verification_status: string
  confidence: string
  source_note: string
  ai_generated: boolean
  created_by_user_id: string | null
  sources: Source[]
  evidence: Evidence[]
  people: LinkedPerson[]
}

type ResearchActionBase = {
  label: string
  method: 'POST'
  endpoint: string
}

export type ResearchAction = ResearchActionBase & (
  | {
      action_type: 'timeline'
      payload: {
        occurred_on: string
        occurred_time: string | null
        title: string
        description: string
        evidence_ids: string[]
        person_ids: string[]
      }
    }
  | {
      action_type: 'thread'
      payload: {
        title: string
        body: string
        thread_type: 'question' | 'theory' | 'evidence' | 'dispute'
        evidence_ids: string[]
        person_ids: string[]
      }
    }
  | {
      action_type: 'evidence'
      payload: {
        title: string
        description: string | null
        url: string
        evidence_type: 'document' | 'image' | 'video' | 'audio' | 'link' | 'article' | 'other'
        person_ids: string[]
      }
    }
)

export type ResearchChatResponse = {
  answer: string
  sources: { title: string; url: string }[]
  action: ResearchAction | null
}

export type Evidence = {
  id: string
  title: string
  description: string | null
  evidence_type: string
  original_filename: string | null
  mime_type: string | null
  file_size: number | null
  source_url: string | null
  source_id: string | null
  verification_status: string
  processing_status: string
  ai_generated: boolean
  review_status: string
  comment_count: number
  created_at: string
}

export type EvidenceComment = {
  id: string
  body: string
  author: {
    id: string
    username: string
    display_name: string
  }
  can_delete: boolean
  created_at: string
  updated_at: string
}

export type CaseNotebookNote = {
  id: string
  case_id: string
  title: string
  body: string
  author: {
    id: string
    username: string
    display_name: string
  }
  can_edit: boolean
  created_at: string
  updated_at: string
}

export type CaseTimelineEntry = {
  id: string
  case_id: string
  occurred_on: string
  occurred_time: string | null
  title: string
  body: string
  author: {
    id: string
    username: string
    display_name: string
  }
  can_edit: boolean
  created_at: string
  updated_at: string
}

export type ReportResourceType = 'discussion_comment' | 'evidence_comment' | 'evidence' | 'user'
export type ReportReason = 'harassment' | 'hate_speech' | 'doxxing' | 'illegal_material' | 'misinformation' | 'spam' | 'other'

export type ModerationReport = {
  id: string
  reporter_user_id: string
  reporter_email: string
  resource_type: ReportResourceType
  resource_id: string
  target_user_id: string | null
  target_summary: string
  reason_code: ReportReason
  details: string
  status: 'pending' | 'resolved' | 'dismissed'
  resolution_note: string | null
  created_at: string
  reviewed_at: string | null
}

export type ModerationReportPage = {
  items: ModerationReport[]
  page: number
  page_size: number
  total: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

export type Source = {
  id: string
  title: string
  url: string
  publisher: string | null
  source_type: string
  retrieved_at: string
}

export type CaseDetail = CaseListItem & {
  public_id: string
  status: string
  owner: { id: string; username: string; display_name: string }
  ai_error_message: string | null
  summary: { body: string; source: string; ai_model: string | null } | null
  timeline: TimelineEvent[]
  sources: Source[]
  external_sources: {
    source_type: string
    external_id: string
    source_url: string
    source_name: string
    source_published_at: string | null
    source_updated_at: string | null
  }[]
  created_at: string
}

export type AdminCaseListItem = {
  id: string
  title: string
  status: string
  privacy: string
  ai_research_status: string
  cover_image_url: string | null
  owner_id: string
  owner_email: string
  owner_username: string
  owner_display_name: string
  created_at: string
  updated_at: string
}

export type AdminCasePage = {
  items: AdminCaseListItem[]
  page: number
  page_size: number
  total: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

export type AdminUserListItem = {
  id: string
  email: string
  username: string
  display_name: string
  is_active: boolean
  moderation_status: string
  is_verified: boolean
  is_admin: boolean
  tier_level: 0 | 1 | 2 | 3
  plan_code: string
  plan_name: string
  case_count: number
  created_at: string
}

export type AdminUserPage = {
  items: AdminUserListItem[]
  page: number
  page_size: number
  total: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

export type DiscussionAuthor = {
  id: string
  username: string
  display_name: string
}

export type DiscussionReaction = {
  emoji: '👍' | '❤️' | '🤔' | '🔎' | '❓'
  count: number
  reacted_by_me: boolean
}

export type DiscussionComment = {
  id: string
  body: string
  author: DiscussionAuthor
  created_at: string
  reactions: DiscussionReaction[]
}

export type DiscussionThread = {
  id: string
  title: string
  body: string
  thread_type: 'question' | 'theory' | 'evidence' | 'dispute'
  author: DiscussionAuthor
  created_at: string
  updated_at: string
  comments: DiscussionComment[]
  evidence: Evidence[]
  people: LinkedPerson[]
  sources: Source[]
  ai_generated: boolean
  review_status: string
  vote_count: number
  voted_by_me: boolean
}

export type PersonCategory = 'primary' | 'family' | 'friend' | 'law_enforcement' | 'witness' | 'other'
export type EntityType = 'person' | 'organization' | 'location' | 'other'
export type ReviewStatus = 'suggested' | 'confirmed' | 'rejected'

export type CasePerson = {
  id: string
  case_id: string
  name: string
  slug: string
  role: string
  category: PersonCategory
  entity_type: EntityType
  photo_url: string | null
  date_of_birth: string | null
  place_of_birth: string | null
  relationship_to_primary: string | null
  summary: string | null
  is_primary: boolean
  ai_suggested: boolean
  review_status: ReviewStatus
  connection_count: number
  evidence_count: number
  notes_count: number
  created_at: string
  updated_at: string
}

export type LinkedPerson = Pick<CasePerson, 'id' | 'name' | 'role' | 'category' | 'entity_type' | 'photo_url'>

export type PersonRelationship = {
  id: string
  case_id: string
  source_person_id: string
  target_person_id: string
  relationship_type: string
  label: string
  description: string | null
  confidence: number | null
  source_type: string | null
  source_id: string | null
  source_url: string | null
  source_title: string | null
  ai_suggested: boolean
  review_status: ReviewStatus
  created_at: string
  updated_at: string
}

export type PersonNote = {
  id: string
  body: string
  author_user_id: string
  author_name: string
  created_at: string
  updated_at: string
}

export type LocationType = 'primary' | 'event' | 'evidence' | 'last_seen' | 'sighting' | 'search_area' | 'law_enforcement' | 'other'

export type CaseLocation = {
  id: string
  case_id: string
  name: string
  description: string
  latitude: number | null
  longitude: number | null
  location_type: LocationType
  occurred_on: string | null
  precision: 'exact' | 'approximate'
  verification_status: 'verified' | 'source_backed' | 'unverified' | 'disputed'
  source_id: string | null
  source_url: string | null
  source_title: string | null
  ai_suggested: boolean
  review_status: ReviewStatus
  created_by_user_id: string | null
  created_at: string
  updated_at: string
  evidence: Evidence[]
  people: LinkedPerson[]
}

export type FBICase = {
  external_id: string
  title: string
  description: string | null
  details: string | null
  remarks: string | null
  caution: string | null
  warning_message: string | null
  reward_text: string | null
  status: string | null
  classification: string | null
  subjects: string[]
  aliases: string[]
  dates_of_birth: string[]
  place_of_birth: string | null
  nationality: string | null
  sex: string | null
  race: string | null
  hair: string | null
  eyes: string | null
  field_offices: string[]
  locations: string[]
  publication: string | null
  modified: string | null
  source_url: string
  image_url: string | null
  already_imported: boolean
  imported_case_id: string | null
}

export type FBICasePage = {
  items: FBICase[]
  page: number
  total: number
  has_next: boolean
}
