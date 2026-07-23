import asyncio
import uuid

from src.db.session import AsyncSessionLocal
from src.models.tenant import Tenant


async def create_test_tenant():
    """Створити тестовий tenant для розробки."""
    async with AsyncSessionLocal() as session:
        tenant = Tenant(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            name="Test Company",
            api_key="test-api-key-12345",
            is_active=True,
        )
        session.add(tenant)
        await session.commit()
        print(f"Created tenant: {tenant.id}")


if __name__ == "__main__":
    asyncio.run(create_test_tenant())