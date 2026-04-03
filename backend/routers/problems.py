import json
from fastapi import APIRouter, HTTPException, Header, Query
from typing import Optional
from database import get_db
from routers.auth import require_role

router = APIRouter()


def get_token(authorization: Optional[str] = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    return authorization.replace("Bearer ", "")


@router.get("/problems")
async def list_problems(
    difficulty: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
):
    token = get_token(authorization)
    require_role(token, "any")

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, title, description, topic_tags, difficulty FROM problems ORDER BY id"
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            topic_tags = json.loads(row[3])

            if difficulty and row[4].lower() != difficulty.lower():
                continue

            if tag and tag.lower() not in [t.lower() for t in topic_tags]:
                continue

            results.append(
                {
                    "id": row[0],
                    "title": row[1],
                    "description": row[2][:200] + ("..." if len(row[2]) > 200 else ""),
                    "topic_tags": topic_tags,
                    "difficulty": row[4],
                }
            )
        return {"problems": results}
    finally:
        await db.close()


@router.get("/problems/{problem_id}")
async def get_problem(
    problem_id: int,
    language: Optional[str] = Query("python"),
    authorization: Optional[str] = Header(None),
):
    token = get_token(authorization)
    require_role(token, "any")

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, title, description, topic_tags, difficulty FROM problems WHERE id = ?",
            (problem_id,),
        )
        problem = await cursor.fetchone()
        if not problem:
            raise HTTPException(status_code=404, detail="Problem not found")

        cursor = await db.execute(
            "SELECT language, template_code, editable_ranges FROM problem_templates WHERE problem_id = ? AND language = ?",
            (problem_id, language),
        )
        template = await cursor.fetchone()

        cursor = await db.execute(
            "SELECT language FROM problem_templates WHERE problem_id = ?",
            (problem_id,),
        )
        available_languages = [row[0] for row in await cursor.fetchall()]

        cursor = await db.execute(
            "SELECT required_constructs, banned_constructs FROM problem_constraints WHERE problem_id = ?",
            (problem_id,),
        )
        constraints = await cursor.fetchone()

        cursor = await db.execute(
            "SELECT id, input_data, expected_output, is_sample FROM test_cases WHERE problem_id = ? AND is_sample = 1",
            (problem_id,),
        )
        sample_tests = await cursor.fetchall()

        result = {
            "id": problem[0],
            "title": problem[1],
            "description": problem[2],
            "topic_tags": json.loads(problem[3]),
            "difficulty": problem[4],
            "available_languages": available_languages,
            "required_constructs": json.loads(constraints[0]) if constraints else [],
            "banned_constructs": json.loads(constraints[1]) if constraints else [],
            "template": None,
            "sample_tests": [
                {
                    "id": tc[0],
                    "input_data": tc[1],
                    "expected_output": tc[2],
                }
                for tc in sample_tests
            ],
        }

        if template:
            result["template"] = {
                "language": template[0],
                "template_code": template[1],
                "editable_ranges": json.loads(template[2]),
            }

        return result
    finally:
        await db.close()


@router.get("/problems/{problem_id}/template/{language}")
async def get_template(
    problem_id: int,
    language: str,
    authorization: Optional[str] = Header(None),
):
    token = get_token(authorization)
    require_role(token, "any")

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT language, template_code, editable_ranges FROM problem_templates WHERE problem_id = ? AND language = ?",
            (problem_id, language),
        )
        template = await cursor.fetchone()
        if not template:
            raise HTTPException(
                status_code=404,
                detail=f"No template found for language: {language}",
            )

        return {
            "language": template[0],
            "template_code": template[1],
            "editable_ranges": json.loads(template[2]),
        }
    finally:
        await db.close()
