from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.core.exceptions import (
    http_exception_handler,
    registration_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import configure_logging
from app.core.middleware import request_logging_middleware
from app.core.responses import success_response
from app.database import init_db
from app.api.routes.auth import router as auth_router
from app.api.routes.care_plans import router as care_plans_router
from app.api.routes.consent import router as consent_router
from app.api.routes.me import router as me_router
from app.api.routes.postoffice import router as postoffice_router
from app.api.routes.relationships import router as relationships_router
from app.auth.auth_service import RegistrationError


configure_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(request_logging_middleware)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RegistrationError, registration_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.get("/")
def health_check():
    return success_response({
        "status": "success",
        "message": "SVASTRA+ Authentication Service Running"
    })


app.include_router(auth_router)
app.include_router(care_plans_router)
app.include_router(consent_router)
app.include_router(me_router)
app.include_router(relationships_router)
app.include_router(postoffice_router)
