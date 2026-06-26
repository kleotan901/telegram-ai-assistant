# src/db/session.py — отримує URL бази
from src.core.config import settings

engine = create_async_engine(settings.database_url)
