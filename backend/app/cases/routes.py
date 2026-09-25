import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from openai import OpenAIError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from app.ai.chat_research import ChatResearchRequest, ChatResearchResponse, OpenAIChatResearcher
from app.auth.dependencies import get_current_user, get_optional_current_user, verify_csrf
from app.cases.dependencies import require_case_access, require_public_case_access
from app.cases.models import CaseSummary
from app.cases.schemas import (
    CaseCreate,
    CaseListItem,
    CaseListPage,
    CaseRead,
    FollowState,
    PrivacyPatch,
    TimelineEventCreate,
    TimelineEventRead,
)
from app.cases.service import CaseService, to_case_read, to_list_item
from app.cases.tasks import generate_case
from app.common.errors import AppError
from app.config.settings import get_settings
from app.db.session import get_db
from app.storage.base import StorageProvider
from app.storage.provider import get_storage_provider
from app.subscriptions.dependencies import require_permission
from app.subscriptions.permissions import PermissionService
from app.users.models import User

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=CaseListPage)
async def search_cases(
    q: str | None = Query(default=None, max_length=200),
    sort: Literal["newest", "popular"] = Query(default="newest"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> CaseListPage:
    service = CaseService(db)
    cases, total = await service.search(q, sort, page=page, page_size=page_size)
    counts = await service.discussion_counts([case.id for case in cases])
    user_id = user.id if user is not None else None
    following_ids = (
        await service.following_case_ids([case.id for case in cases], user.id) if user is not None else set()
    )
    items = [
        to_list_item(
            case,
            user_id,
            counts[case.id],
            is_following=case.id in following_ids,
        )
        for case in cases
    ]
    total_pages = max(1, (total + page_size - 1) // page_size)
    return CaseListPage(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )


@router.get("/following", response_model=list[CaseListItem])
async def following_cases(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[CaseListItem]:
    service = CaseService(db)
    cases = await service.following(user.id)
    counts = await service.discussion_counts([case.id for case in cases])
    return [to_list_item(case, user.id, counts[case.id], is_following=True) for case in cases]


@router.get("/mine", response_model=list[CaseListItem])
async def my_cases(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[CaseListItem]:
    service = CaseService(db)
    cases = await service.mine(user.id)
    counts = await service.discussion_counts([case.id for case in cases])
    following_ids = await service.following_case_ids([case.id for case in cases], user.id)
    return [
        to_list_item(
            case,
            user.id,
            counts[case.id],
            is_following=case.id in following_ids,
        )
        for case in cases
    ]


@router.post(
    "",
    response_model=CaseRead,
    status_code=202,
    dependencies=[Depends(verify_csrf)],
)
async def create_case(
    data: CaseCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CaseRead:
    case, job = await CaseService(db).create(data, user)
    if job is not None:
        generate_case.delay(str(case.id), str(job.id))
    include_evidence = await PermissionService(db).allows(user.id, "evidence.read", is_admin=user.is_admin)
    return to_case_read(
        await CaseService(db).get(case.id),
        user.id,
        is_following=False,
        include_evidence_details=include_evidence,
    )


@router.get("/{case_id}", response_model=CaseRead)
async def get_case(
    case_id: uuid.UUID,
    user: User | None = Depends(get_optional_current_user),
    __: None = Depends(require_public_case_access),
    db: AsyncSession = Depends(get_db),
) -> CaseRead:
    service = CaseService(db)
    case = await service.get(case_id)
    is_following = await service.is_following(case_id, user.id) if user is not None else False
    include_evidence = (
        await PermissionService(db).allows(user.id, "evidence.read", is_admin=user.is_admin)
        if user is not None
        else False
    )
    return to_case_read(
        case,
        user.id if user is not None else None,
        is_following=is_following,
        include_evidence_details=include_evidence,
    )


@router.get(
    "/{case_id}/cover",
    response_class=RedirectResponse,
    dependencies=[Depends(require_public_case_access)],
)
async def get_case_cover(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> RedirectResponse:
    object_key = await CaseService(db).cover_object_key(case_id)
    return RedirectResponse(await storage.create_download_url(object_key), status_code=307)


@router.post(
    "/{case_id}/follow",
    response_model=FollowState,
    dependencies=[Depends(verify_csrf), Depends(require_permission("case.follow", required_tier=1))],
)
async def follow_case(
    case_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FollowState:
    await CaseService(db).follow(case_id, user.id)
    return FollowState(is_following=True)


@router.delete(
    "/{case_id}/follow",
    response_model=FollowState,
    dependencies=[Depends(verify_csrf), Depends(require_permission("case.follow", required_tier=1))],
)
async def unfollow_case(
    case_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FollowState:
    await CaseService(db).unfollow(case_id, user.id)
    return FollowState(is_following=False)


@router.patch("/{case_id}/privacy", response_model=CaseRead, dependencies=[Depends(verify_csrf)])
async def update_case_privacy(
    case_id: uuid.UUID,
    data: PrivacyPatch,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CaseRead:
    service = CaseService(db)
    case = await service.update_privacy(case_id, data.privacy, user)
    return to_case_read(
        case,
        user.id,
        is_following=await service.is_following(case_id, user.id),
        include_evidence_details=True,
    )


@router.post(
    "/{case_id}/timeline",
    response_model=TimelineEventRead,
    status_code=201,
    dependencies=[Depends(verify_csrf), Depends(require_permission("timeline.write"))],
)
async def create_timeline_event(
    case_id: uuid.UUID,
    data: TimelineEventCreate,
    user: User = Depends(get_current_user),
    _: None = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
) -> TimelineEventRead:
    return await CaseService(db).create_timeline_event(case_id, data, user)


@router.post("/{case_id}/research", status_code=202, dependencies=[Depends(verify_csrf)])
async def research_case(
    case_id: uuid.UUID,
    user: User = Depends(get_current_user),
    __: None = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    job = await CaseService(db).queue_research(case_id, user)
    generate_case.delay(str(case_id), str(job.id))
    return {"job_id": str(job.id), "status": "queued"}


@router.post(
    "/{case_id}/research-chat",
    response_model=ChatResearchResponse,
    dependencies=[
        Depends(verify_csrf),
        Depends(require_case_access),
        Depends(require_permission("ai.research", required_tier=2)),
    ],
)
async def research_chat(
    case_id: uuid.UUID,
    data: ChatResearchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResearchResponse:
    context = await PermissionService(db).for_user(user.id, is_admin=user.is_admin)
    if not user.is_admin and context.tier_level < 2:
        raise AppError(
            403,
            "researcher_upgrade_required",
            "Researcher requires a paid plan",
            {"required_tier": 2},
        )
    case = await CaseService(db).get(case_id)
    summary = await db.scalar(
        select(CaseSummary.body).where(CaseSummary.case_id == case_id, CaseSummary.is_current.is_(True))
    )
    try:
        return await OpenAIChatResearcher(get_settings()).answer(
            case_title=case.title,
            case_summary=summary or "",
            message=data.message.strip(),
            history=data.history,
        )
    except (OpenAIError, RuntimeError) as exc:
        raise AppError(503, "ai_research_unavailable", "Researcher is unavailable. Please try again later.") from exc
