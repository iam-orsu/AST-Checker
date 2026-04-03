from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    role: Optional[str] = None
    token: Optional[str] = None
    message: Optional[str] = None


class EditableRange(BaseModel):
    startLine: int
    endLine: int


class TemplateCreate(BaseModel):
    language: str
    template_code: str
    editable_ranges: list[EditableRange] = []


class TestCaseCreate(BaseModel):
    input_data: str
    expected_output: str
    is_sample: int = 1


class ProblemCreate(BaseModel):
    title: str
    description: str
    topic_tags: list[str] = []
    difficulty: str = "Easy"
    required_constructs: list[str] = []
    banned_constructs: list[str] = []
    templates: list[TemplateCreate] = []
    test_cases: list[TestCaseCreate] = []


class ProblemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    topic_tags: Optional[list[str]] = None
    difficulty: Optional[str] = None
    required_constructs: Optional[list[str]] = None
    banned_constructs: Optional[list[str]] = None
    templates: Optional[list[TemplateCreate]] = None
    test_cases: Optional[list[TestCaseCreate]] = None


class ProblemSummary(BaseModel):
    id: int
    title: str
    description: str
    topic_tags: list[str]
    difficulty: str


class TemplateResponse(BaseModel):
    language: str
    template_code: str
    editable_ranges: list[EditableRange]


class ProblemDetail(BaseModel):
    id: int
    title: str
    description: str
    topic_tags: list[str]
    difficulty: str
    required_constructs: list[str]
    banned_constructs: list[str]
    templates: list[TemplateResponse]
    test_cases: list[TestCaseCreate]


class ConstraintCheckRequest(BaseModel):
    code: str
    language: str
    problem_id: int


class ConstraintViolation(BaseModel):
    line: int
    message: str
    construct: str
    violation_type: str  # "banned_used" or "required_missing"


class ConstraintCheckResponse(BaseModel):
    passed: bool
    violations: list[dict] = []


class SubmitRequest(BaseModel):
    code: str
    language: str
    problem_id: int


class TestCaseResult(BaseModel):
    test_case_id: int
    input_data: str
    expected_output: str
    actual_output: str
    passed: bool
    error: Optional[str] = None


class SubmitResponse(BaseModel):
    status: str  # "accepted", "wrong_answer", "constraint_failed", "runtime_error", "timeout"
    constraint_check: ConstraintCheckResponse
    total_passed: int = 0
    total_failed: int = 0
    total_tests: int = 0
    test_results: list[TestCaseResult] = []
    execution_time: Optional[float] = None


class RunRequest(BaseModel):
    code: str
    language: str
    stdin: str = ""


class RunResponse(BaseModel):
    status: str  # "success", "error", "timeout"
    stdout: str = ""
    stderr: str = ""
    execution_time: Optional[float] = None
