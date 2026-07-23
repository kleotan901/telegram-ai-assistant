import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session
from src.services import AnalyticsService

logger = logging.getLogger(__name__)

analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])


@analytics_router.get("/pipeline/{tenant_id}")
async def get_pipeline_stats(
    tenant_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Статистика sales pipeline для tenant.

    Повертає кількість користувачів по кожній стадії,
    загальну кількість, активних та неактивних.

    Depends(get_session) — FastAPI Dependency Injection.
    Відрізняється від aiogram middleware:
    тут FastAPI автоматично передає сесію і закриває її
    після завершення запиту.
    """
    try:
        service = AnalyticsService(
            session=session,
            tenant_id=tenant_id,
        )
        stats = await service.get_pipeline_stats()
        return {
            "tenant_id": str(tenant_id),
            "stats": stats,
        }
    except Exception as e:
        logger.error(
            "Failed to get pipeline stats for tenant %s: %s",
            tenant_id, e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics",
        )


@analytics_router.get("/active-users/{tenant_id}")
async def get_active_users(
    tenant_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Кількість активних користувачів tenant."""
    service = AnalyticsService(
        session=session,
        tenant_id=tenant_id,
    )
    count = await service.get_active_users_count()
    return {
        "tenant_id": str(tenant_id),
        "active_users": count,
    }
