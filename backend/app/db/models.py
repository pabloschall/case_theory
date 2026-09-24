"""Import all models so Alembic can discover metadata."""

from app.admin.models import AuditLog
from app.auth.models import AccountActionToken, LegalAcceptance, RefreshSession
from app.cases.models import (
    Case,
    CaseFollower,
    CaseGenerationJob,
    CaseMember,
    CaseSource,
    CaseSummary,
    Source,
    SourceCitation,
    TimelineEvent,
    TimelineEventSource,
)
from app.discussions.models import (
    DiscussionComment,
    DiscussionReaction,
    DiscussionThread,
    DiscussionThreadSource,
    DiscussionThreadVote,
)
from app.evidence.models import (
    DiscussionThreadEvidence,
    Evidence,
    EvidenceComment,
    TimelineEventEvidence,
)
from app.invitations.models import CaseInvitation
from app.maps.models import CaseLocation, CaseLocationEvidence, CaseLocationPerson
from app.messaging.models import DirectConversation, DirectMessage, MessageAttachment
from app.moderation.models import ModerationAction, Report
from app.notes.models import CaseNotebookNote, CaseTimelineEntry
from app.people.models import (
    DiscussionThreadPerson,
    Person,
    PersonEvidence,
    PersonNote,
    PersonRelationship,
    TimelineEventPerson,
)
from app.subscriptions.models import (
    AIUsageRecord,
    Permission,
    PlanPermission,
    SubscriptionPlan,
    UserSubscription,
)
from app.users.models import User, UserAvatarUpload, UserBlock, UserProfile

__all__ = [
    "AuditLog",
    "Permission",
    "PlanPermission",
    "RefreshSession",
    "AccountActionToken",
    "LegalAcceptance",
    "SubscriptionPlan",
    "User",
    "UserProfile",
    "UserBlock",
    "UserAvatarUpload",
    "UserSubscription",
    "AIUsageRecord",
    "Case",
    "CaseFollower",
    "CaseGenerationJob",
    "CaseMember",
    "CaseSummary",
    "CaseSource",
    "SourceCitation",
    "TimelineEvent",
    "TimelineEventSource",
    "Source",
    "DiscussionComment",
    "DiscussionReaction",
    "DiscussionThread",
    "DiscussionThreadSource",
    "DiscussionThreadVote",
    "Evidence",
    "EvidenceComment",
    "DiscussionThreadEvidence",
    "TimelineEventEvidence",
    "CaseLocation",
    "CaseLocationEvidence",
    "CaseLocationPerson",
    "CaseInvitation",
    "DirectConversation",
    "DirectMessage",
    "MessageAttachment",
    "CaseNotebookNote",
    "CaseTimelineEntry",
    "Report",
    "ModerationAction",
    "Person",
    "PersonRelationship",
    "PersonEvidence",
    "PersonNote",
    "TimelineEventPerson",
    "DiscussionThreadPerson",
]
