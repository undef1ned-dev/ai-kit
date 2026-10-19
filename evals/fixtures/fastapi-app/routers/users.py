import time

import requests
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from settings import settings

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/search")
async def search_users(name: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(text(f"SELECT * FROM users WHERE name LIKE '%{name}%'"))
    return [dict(row._mapping) for row in result]


@router.get("/{user_id}/avatar")
async def get_avatar(user_id: int):
    for _ in range(3):
        try:
            response = requests.get(f"{settings.avatar_service_url}/avatars/{user_id}")
            return response.json()
        except:
            time.sleep(1)
    return None
