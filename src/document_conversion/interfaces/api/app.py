from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from document_conversion.infrastructure.runtime import start_platform_runtime

from .router import ctx, router


@asynccontextmanager
async def lifespan(_: FastAPI):
    start_platform_runtime(ctx)
    yield


app = FastAPI(title="document-conversion-platform", lifespan=lifespan)
app.include_router(router)
