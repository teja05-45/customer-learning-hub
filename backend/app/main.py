"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.auth import AuthMiddleware
from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.core.errors import AppError
from app.core.logging import configure_logging, get_logger
from app.models import User
configure_logging()
logger = get_logger("app.startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("API ready (environment=%s, demo_mode=%s)", settings.environment, settings.demo_mode)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Evidence-first customer research management API. Sessions are server-side and "
        "role enforcement happens in the API; see /api/v1/session and docs/auth.md."
    ),
    lifespan=lifespan,
)

# Authentication runs inside CORS so browser clients can read error responses.
app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Demo-User-Id"],
    expose_headers=["Content-Disposition", "X-Data-Origin"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {"field": ".".join(str(part) for part in error.get("loc", [])[1:]), "message": error.get("msg", "")}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Some fields need attention.",
                "details": details,
            }
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "http_error",
                "message": str(exc.detail) if exc.detail else "Request failed.",
                "details": None,
            }
        },
    )


app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health",
        "demo_mode": settings.demo_mode,
        "data": "synthetic demonstration data" if settings.demo_mode else "live workspace data",
    }
