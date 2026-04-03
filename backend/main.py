import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db, seed_db
from routers import auth, admin, problems, constraints, submit


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_db()
    # Pre-pull Docker images in background so first execution doesn't timeout
    threading.Thread(target=_pull_images, daemon=True).start()
    yield


def _pull_images():
    """Pull required Docker images on startup (runs in background thread)."""
    try:
        from executor.docker_runner import pull_required_images
        print("Pre-pulling Docker execution images...")
        pull_required_images()
        print("Docker image pre-pull complete.")
    except Exception as e:
        print(f"Docker image pre-pull skipped: {e}")


app = FastAPI(
    title="AST-Compiler API",
    description="Coding platform with AST-based constraint validation",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(problems.router, prefix="/api", tags=["problems"])
app.include_router(constraints.router, prefix="/api", tags=["constraints"])
app.include_router(submit.router, prefix="/api", tags=["submit"])


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "ast-compiler-backend"}
