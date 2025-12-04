from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Query

from ..db.database import memories_col

router = APIRouter()


@router.get("/users/profile")
async def get_profile(user_id: Optional[str] = Query(None)):
    if not user_id:
        # anonymous profile
        return {"profile": {}}
    mem = memories_col().find_one({"userId": user_id}) or {}
    profile = mem.get("profile") or {}
    return {"profile": profile}


@router.put("/users/profile")
async def update_profile(body: Dict[str, Any] = Body(...)):
    user_id = body.get("userId") or body.get("user_id")
    profile = body.get("profile") or {}
    if not user_id:
        return {"error": "userId required"}
    memories_col().update_one({"userId": user_id}, {"$set": {"profile": profile}}, upsert=True)
    return {"profile": profile}
