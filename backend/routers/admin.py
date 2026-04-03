import json
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from models import (
    ProblemCreate,
    ProblemUpdate,
    ProblemDetail,
    ProblemSummary,
    TemplateResponse,
    EditableRange,
    TestCaseCreate,
)
from database import get_db
from routers.auth import require_role

router = APIRouter()


def get_token(authorization: Optional[str] = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    return authorization.replace("Bearer ", "")


@router.get("/problems")
async def list_problems(authorization: Optional[str] = Header(None)):
    token = get_token(authorization)
    require_role(token, "admin")

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, title, description, topic_tags, difficulty FROM problems ORDER BY id DESC"
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            results.append(
                {
                    "id": row[0],
                    "title": row[1],
                    "description": row[2],
                    "topic_tags": json.loads(row[3]),
                    "difficulty": row[4],
                }
            )
        return {"problems": results}
    finally:
        await db.close()


@router.get("/problems/{problem_id}")
async def get_problem(problem_id: int, authorization: Optional[str] = Header(None)):
    token = get_token(authorization)
    require_role(token, "admin")

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
            "SELECT language, template_code, editable_ranges FROM problem_templates WHERE problem_id = ?",
            (problem_id,),
        )
        templates = await cursor.fetchall()

        cursor = await db.execute(
            "SELECT required_constructs, banned_constructs FROM problem_constraints WHERE problem_id = ?",
            (problem_id,),
        )
        constraints = await cursor.fetchone()

        cursor = await db.execute(
            "SELECT id, input_data, expected_output, is_sample FROM test_cases WHERE problem_id = ?",
            (problem_id,),
        )
        test_cases = await cursor.fetchall()

        return {
            "id": problem[0],
            "title": problem[1],
            "description": problem[2],
            "topic_tags": json.loads(problem[3]),
            "difficulty": problem[4],
            "required_constructs": json.loads(constraints[0]) if constraints else [],
            "banned_constructs": json.loads(constraints[1]) if constraints else [],
            "templates": [
                {
                    "language": t[0],
                    "template_code": t[1],
                    "editable_ranges": json.loads(t[2]),
                }
                for t in templates
            ],
            "test_cases": [
                {
                    "id": tc[0],
                    "input_data": tc[1],
                    "expected_output": tc[2],
                    "is_sample": tc[3],
                }
                for tc in test_cases
            ],
        }
    finally:
        await db.close()


@router.post("/problems")
async def create_problem(
    problem: ProblemCreate, authorization: Optional[str] = Header(None)
):
    token = get_token(authorization)
    require_role(token, "admin")

    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO problems (title, description, topic_tags, difficulty) VALUES (?, ?, ?, ?)",
            (
                problem.title,
                problem.description,
                json.dumps(problem.topic_tags),
                problem.difficulty,
            ),
        )
        problem_id = cursor.lastrowid

        await db.execute(
            "INSERT INTO problem_constraints (problem_id, required_constructs, banned_constructs) VALUES (?, ?, ?)",
            (
                problem_id,
                json.dumps(problem.required_constructs),
                json.dumps(problem.banned_constructs),
            ),
        )

        for template in problem.templates:
            editable_ranges = [
                {"startLine": er.startLine, "endLine": er.endLine}
                for er in template.editable_ranges
            ]
            await db.execute(
                "INSERT INTO problem_templates (problem_id, language, template_code, editable_ranges) VALUES (?, ?, ?, ?)",
                (
                    problem_id,
                    template.language,
                    template.template_code,
                    json.dumps(editable_ranges),
                ),
            )

        for test_case in problem.test_cases:
            await db.execute(
                "INSERT INTO test_cases (problem_id, input_data, expected_output, is_sample) VALUES (?, ?, ?, ?)",
                (
                    problem_id,
                    test_case.input_data,
                    test_case.expected_output,
                    test_case.is_sample,
                ),
            )

        await db.commit()
        return {"success": True, "problem_id": problem_id, "message": "Problem created"}
    finally:
        await db.close()


@router.put("/problems/{problem_id}")
async def update_problem(
    problem_id: int,
    problem: ProblemUpdate,
    authorization: Optional[str] = Header(None),
):
    token = get_token(authorization)
    require_role(token, "admin")

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id FROM problems WHERE id = ?", (problem_id,)
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Problem not found")

        if problem.title is not None or problem.description is not None or problem.topic_tags is not None or problem.difficulty is not None:
            updates = []
            values = []
            if problem.title is not None:
                updates.append("title = ?")
                values.append(problem.title)
            if problem.description is not None:
                updates.append("description = ?")
                values.append(problem.description)
            if problem.topic_tags is not None:
                updates.append("topic_tags = ?")
                values.append(json.dumps(problem.topic_tags))
            if problem.difficulty is not None:
                updates.append("difficulty = ?")
                values.append(problem.difficulty)
            values.append(problem_id)
            await db.execute(
                f"UPDATE problems SET {', '.join(updates)} WHERE id = ?", values
            )

        if problem.required_constructs is not None or problem.banned_constructs is not None:
            cursor = await db.execute(
                "SELECT id FROM problem_constraints WHERE problem_id = ?",
                (problem_id,),
            )
            existing = await cursor.fetchone()
            if existing:
                updates = []
                values = []
                if problem.required_constructs is not None:
                    updates.append("required_constructs = ?")
                    values.append(json.dumps(problem.required_constructs))
                if problem.banned_constructs is not None:
                    updates.append("banned_constructs = ?")
                    values.append(json.dumps(problem.banned_constructs))
                values.append(problem_id)
                await db.execute(
                    f"UPDATE problem_constraints SET {', '.join(updates)} WHERE problem_id = ?",
                    values,
                )
            else:
                await db.execute(
                    "INSERT INTO problem_constraints (problem_id, required_constructs, banned_constructs) VALUES (?, ?, ?)",
                    (
                        problem_id,
                        json.dumps(problem.required_constructs or []),
                        json.dumps(problem.banned_constructs or []),
                    ),
                )

        if problem.templates is not None:
            await db.execute(
                "DELETE FROM problem_templates WHERE problem_id = ?", (problem_id,)
            )
            for template in problem.templates:
                editable_ranges = [
                    {"startLine": er.startLine, "endLine": er.endLine}
                    for er in template.editable_ranges
                ]
                await db.execute(
                    "INSERT INTO problem_templates (problem_id, language, template_code, editable_ranges) VALUES (?, ?, ?, ?)",
                    (
                        problem_id,
                        template.language,
                        template.template_code,
                        json.dumps(editable_ranges),
                    ),
                )

        if problem.test_cases is not None:
            await db.execute(
                "DELETE FROM test_cases WHERE problem_id = ?", (problem_id,)
            )
            for test_case in problem.test_cases:
                await db.execute(
                    "INSERT INTO test_cases (problem_id, input_data, expected_output, is_sample) VALUES (?, ?, ?, ?)",
                    (
                        problem_id,
                        test_case.input_data,
                        test_case.expected_output,
                        test_case.is_sample,
                    ),
                )

        await db.commit()
        return {"success": True, "message": "Problem updated"}
    finally:
        await db.close()


@router.delete("/problems/{problem_id}")
async def delete_problem(
    problem_id: int, authorization: Optional[str] = Header(None)
):
    token = get_token(authorization)
    require_role(token, "admin")

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id FROM problems WHERE id = ?", (problem_id,)
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Problem not found")

        await db.execute("DELETE FROM problem_templates WHERE problem_id = ?", (problem_id,))
        await db.execute("DELETE FROM problem_constraints WHERE problem_id = ?", (problem_id,))
        await db.execute("DELETE FROM test_cases WHERE problem_id = ?", (problem_id,))
        await db.execute("DELETE FROM submissions WHERE problem_id = ?", (problem_id,))
        await db.execute("DELETE FROM problems WHERE id = ?", (problem_id,))
        await db.commit()
        return {"success": True, "message": "Problem deleted"}
    finally:
        await db.close()
