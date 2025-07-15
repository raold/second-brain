from fastapi import APIRouter

from . import ws

api_router = APIRouter()
api_router.include_router(ws.router)
