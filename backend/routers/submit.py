import json
import time
import asyncio
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from models import SubmitRequest, SubmitResponse, ConstraintCheckResponse, TestCaseResult, RunRequest, RunResponse
from database import get_db
from routers.auth import require_role
from ast_engine.engine import analyze_code
from executor.docker_runner import execute_code

router = APIRouter()


def get_token(authorization: Optional[str] = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    return authorization.replace("Bearer ", "")


@router.post("/submit", response_model=SubmitResponse)
async def submit_code(
    request: SubmitRequest,
    authorization: Optional[str] = Header(None),
):
    token = get_token(authorization)
    token_data = require_role(token, "any")
    username = token_data["username"]

    # Reject empty code submissions early
    if not request.code or not request.code.strip():
        return SubmitResponse(
            status="error",
            constraint_check=ConstraintCheckResponse(
                passed=False,
                violations=[{"line": 0, "message": "Cannot submit empty code", "construct": "empty", "violation_type": "error"}],
            ),
            total_passed=0,
            total_failed=0,
            total_tests=0,
            test_results=[],
        )

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id FROM problems WHERE id = ?", (request.problem_id,)
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Problem not found")

        cursor = await db.execute(
            "SELECT required_constructs, banned_constructs FROM problem_constraints WHERE problem_id = ?",
            (request.problem_id,),
        )
        constraints = await cursor.fetchone()
        required = json.loads(constraints[0]) if constraints else []
        banned = json.loads(constraints[1]) if constraints else []

        cursor = await db.execute(
            "SELECT editable_ranges FROM problem_templates WHERE problem_id = ? AND language = ?",
            (request.problem_id, request.language),
        )
        template = await cursor.fetchone()
        editable_ranges = json.loads(template[0]) if template else []

        constraint_result = analyze_code(
            code=request.code,
            language=request.language,
            required_constructs=required,
            banned_constructs=banned,
            editable_ranges=editable_ranges,
        )

        constraint_response = ConstraintCheckResponse(
            passed=constraint_result["passed"],
            violations=constraint_result["violations"],
        )

        if not constraint_result["passed"]:
            await db.execute(
                "INSERT INTO submissions (problem_id, user, language, code, status, results) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    request.problem_id,
                    username,
                    request.language,
                    request.code,
                    "constraint_failed",
                    json.dumps(constraint_result),
                ),
            )
            await db.commit()

            return SubmitResponse(
                status="constraint_failed",
                constraint_check=constraint_response,
                total_passed=0,
                total_failed=0,
                total_tests=0,
                test_results=[],
            )

        cursor = await db.execute(
            "SELECT id, input_data, expected_output FROM test_cases WHERE problem_id = ?",
            (request.problem_id,),
        )
        test_cases = await cursor.fetchall()

        if not test_cases:
            await db.execute(
                "INSERT INTO submissions (problem_id, user, language, code, status, results) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    request.problem_id,
                    username,
                    request.language,
                    request.code,
                    "accepted",
                    json.dumps({"message": "No test cases defined"}),
                ),
            )
            await db.commit()

            return SubmitResponse(
                status="accepted",
                constraint_check=constraint_response,
                total_passed=0,
                total_failed=0,
                total_tests=0,
                test_results=[],
            )

        start_time = time.time()

        test_results = []
        total_passed = 0
        total_failed = 0
        has_error = False
        has_timeout = False

        for tc in test_cases:
            tc_id = tc[0]
            tc_input = tc[1]
            tc_expected = tc[2]

            exec_result = await asyncio.to_thread(
                execute_code,
                code=request.code,
                language=request.language,
                input_data=tc_input,
            )

            if exec_result["status"] == "timeout":
                has_timeout = True
                test_results.append(
                    TestCaseResult(
                        test_case_id=tc_id,
                        input_data=tc_input,
                        expected_output=tc_expected,
                        actual_output="",
                        passed=False,
                        error="Time Limit Exceeded (5 seconds)",
                    )
                )
                total_failed += 1
            elif exec_result["status"] == "error":
                has_error = True
                test_results.append(
                    TestCaseResult(
                        test_case_id=tc_id,
                        input_data=tc_input,
                        expected_output=tc_expected,
                        actual_output=exec_result.get("stderr", ""),
                        passed=False,
                        error=exec_result.get("stderr", "Runtime error"),
                    )
                )
                total_failed += 1
            else:
                actual = exec_result.get("stdout", "").strip()
                expected = tc_expected.strip()
                passed = actual == expected

                if passed:
                    total_passed += 1
                else:
                    total_failed += 1

                test_results.append(
                    TestCaseResult(
                        test_case_id=tc_id,
                        input_data=tc_input,
                        expected_output=tc_expected,
                        actual_output=actual,
                        passed=passed,
                    )
                )

        execution_time = round(time.time() - start_time, 3)

        if has_timeout:
            status = "timeout"
        elif has_error:
            status = "runtime_error"
        elif total_failed > 0:
            status = "wrong_answer"
        else:
            status = "accepted"

        submission_results = {
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_tests": len(test_cases),
            "test_results": [tr.model_dump() for tr in test_results],
        }

        await db.execute(
            "INSERT INTO submissions (problem_id, user, language, code, status, results) VALUES (?, ?, ?, ?, ?, ?)",
            (
                request.problem_id,
                username,
                request.language,
                request.code,
                status,
                json.dumps(submission_results),
            ),
        )
        await db.commit()

        return SubmitResponse(
            status=status,
            constraint_check=constraint_response,
            total_passed=total_passed,
            total_failed=total_failed,
            total_tests=len(test_cases),
            test_results=test_results,
            execution_time=execution_time,
        )
    finally:
        await db.close()


@router.post("/run", response_model=RunResponse)
async def run_code(
    request: RunRequest,
    authorization: Optional[str] = Header(None),
):
    """Run code and return stdout/stderr — no constraint check, no test cases."""
    token = get_token(authorization)
    require_role(token, "any")

    if not request.code or not request.code.strip():
        return RunResponse(status="error", stderr="No code to run")

    start_time = time.time()

    result = await asyncio.to_thread(
        execute_code,
        code=request.code,
        language=request.language,
        input_data=request.stdin,
    )

    execution_time = round(time.time() - start_time, 3)

    return RunResponse(
        status=result["status"],
        stdout=result.get("stdout", ""),
        stderr=result.get("stderr", ""),
        execution_time=execution_time,
    )
