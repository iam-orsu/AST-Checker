import os
import json
import aiosqlite
from seed_problems import get_seed_problems

DATABASE_PATH = os.environ.get("DATABASE_PATH", "/app/data/ast_compiler.db")

# Ensure the database directory exists on startup
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS problems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    topic_tags TEXT NOT NULL DEFAULT '[]',
    difficulty TEXT NOT NULL DEFAULT 'Easy',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS problem_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id INTEGER NOT NULL,
    language TEXT NOT NULL,
    template_code TEXT NOT NULL,
    editable_ranges TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE,
    UNIQUE(problem_id, language)
);

CREATE TABLE IF NOT EXISTS problem_constraints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id INTEGER NOT NULL UNIQUE,
    required_constructs TEXT NOT NULL DEFAULT '[]',
    banned_constructs TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS test_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id INTEGER NOT NULL,
    input_data TEXT NOT NULL,
    expected_output TEXT NOT NULL,
    is_sample INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id INTEGER NOT NULL,
    user TEXT NOT NULL,
    language TEXT NOT NULL,
    code TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    results TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE
);
"""


async def get_db():
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    db = await get_db()
    try:
        await db.executescript(SCHEMA_SQL)
        await db.commit()
    finally:
        await db.close()


async def seed_db():
    db = await get_db()
    try:
        cursor = await db.execute("SELECT COUNT(*) as count FROM problems")
        row = await cursor.fetchone()
        if row[0] > 0:
            return

        seed_data = get_seed_problems()
        for problem in seed_data:
            cursor = await db.execute(
                "INSERT INTO problems (title, description, topic_tags, difficulty) VALUES (?, ?, ?, ?)",
                (
                    problem["title"],
                    problem["description"],
                    json.dumps(problem["topic_tags"]),
                    problem["difficulty"],
                ),
            )
            problem_id = cursor.lastrowid

            await db.execute(
                "INSERT INTO problem_constraints (problem_id, required_constructs, banned_constructs) VALUES (?, ?, ?)",
                (
                    problem_id,
                    json.dumps(problem["required_constructs"]),
                    json.dumps(problem["banned_constructs"]),
                ),
            )

            for template in problem["templates"]:
                await db.execute(
                    "INSERT INTO problem_templates (problem_id, language, template_code, editable_ranges) VALUES (?, ?, ?, ?)",
                    (
                        problem_id,
                        template["language"],
                        template["template_code"],
                        json.dumps(template["editable_ranges"]),
                    ),
                )

            for test_case in problem["test_cases"]:
                await db.execute(
                    "INSERT INTO test_cases (problem_id, input_data, expected_output, is_sample) VALUES (?, ?, ?, ?)",
                    (
                        problem_id,
                        test_case["input_data"],
                        test_case["expected_output"],
                        test_case.get("is_sample", 1),
                    ),
                )

        await db.commit()
        print(f"Seeded {len(seed_data)} problems into database.")
    finally:
        await db.close()
