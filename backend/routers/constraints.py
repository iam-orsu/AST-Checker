import json
import hashlib
import redis
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from models import ConstraintCheckRequest, ConstraintCheckResponse
from database import get_db
from routers.auth import require_role
from ast_engine.engine import analyze_code
import os

router = APIRouter()

try:
    redis_client = redis.Redis(
        host=os.environ.get("REDIS_HOST", "redis"),
        port=int(os.environ.get("REDIS_PORT", 6379)),
        decode_responses=True,
        socket_connect_timeout=2,
    )
except Exception:
    redis_client = None

CACHE_TTL_SECONDS = 2


def get_token(authorization: Optional[str] = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    return authorization.replace("Bearer ", "")


def get_cache_key(code: str, language: str, problem_id: int) -> str:
    content = f"{problem_id}:{language}:{code}"
    return f"constraint_check:{hashlib.md5(content.encode()).hexdigest()}"


@router.post("/check-constraints", response_model=ConstraintCheckResponse)
async def check_constraints(
    request: ConstraintCheckRequest,
    authorization: Optional[str] = Header(None),
):
    token = get_token(authorization)
    require_role(token, "any")

    cache_key = get_cache_key(request.code, request.language, request.problem_id)
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                data = json.loads(cached)
                return ConstraintCheckResponse(**data)
        except Exception:
            pass

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT required_constructs, banned_constructs FROM problem_constraints WHERE problem_id = ?",
            (request.problem_id,),
        )
        constraints = await cursor.fetchone()
        if not constraints:
            return ConstraintCheckResponse(passed=True, violations=[])

        required = json.loads(constraints[0])
        banned = json.loads(constraints[1])

        cursor = await db.execute(
            "SELECT editable_ranges FROM problem_templates WHERE problem_id = ? AND language = ?",
            (request.problem_id, request.language),
        )
        template = await cursor.fetchone()
        editable_ranges = json.loads(template[0]) if template else []

        result = analyze_code(
            code=request.code,
            language=request.language,
            required_constructs=required,
            banned_constructs=banned,
            editable_ranges=editable_ranges,
        )

        response_data = {
            "passed": result["passed"],
            "violations": result["violations"],
        }

        if redis_client:
            try:
                redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(response_data))
            except Exception:
                pass

        return ConstraintCheckResponse(**response_data)
    finally:
        await db.close()
