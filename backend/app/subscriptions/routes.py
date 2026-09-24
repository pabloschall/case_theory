from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.subscriptions.models import SubscriptionPlan
from app.subscriptions.schemas import PlanRead

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/plans", response_model=list[PlanRead])
async def list_plans(db: AsyncSession = Depends(get_db)) -> list[SubscriptionPlan]:
    result = await db.execute(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.is_active.is_(True))
        .order_by(SubscriptionPlan.active_case_limit)
    )
    return list(result.scalars())
