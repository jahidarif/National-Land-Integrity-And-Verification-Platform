from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.domain.errors.conflict_error import ConflictError
from app.domain.errors.forbidden_error import ForbiddenError
from app.domain.errors.not_found_error import NotFoundError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.infrastructure.database import engine
from app.presentation.auth_router import router as auth_router
from app.presentation.chat_router import router as chat_router
from app.presentation.platform_router import router as platform_router
from app.presentation.documents_router import router as documents_router

app = FastAPI(
    title="National Land Integrity Chatbot API",
    description="National Land Integrity chatbot with optional server-side Maira and speech-to-text integration. Government record integrations are not included in this prototype.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-TOKEN", "X-Conversation-ID"],
    expose_headers=["X-Conversation-ID"],
)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(platform_router)
app.include_router(documents_router)


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ForbiddenError)
async def forbidden_handler(request: Request, exc: ForbiddenError):
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})

@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "service": "national-land-integrity-chatbot", "assistant": "demo-not-maira"}
