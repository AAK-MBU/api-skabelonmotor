"""
Main
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import letter_handler


class UTF8JSONResponse(JSONResponse):
    """Class docstring"""
    media_type = "application/json; charset=utf-8"


app = FastAPI(
    title="Skabelonmotor API",
    description="Simple API for Skabelonmotor",
    version="1.0.0",
    default_response_class=UTF8JSONResponse
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(letter_handler.router)


@app.get("/")
def root():
    """Default endpoint"""
    return {"message": "Skabelonmotor is running"}


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}
