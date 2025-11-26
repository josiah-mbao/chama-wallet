"""
Chama Wallet API v1 - Stable Production Release
Contains the current stable feature set with billing integration.
"""

from fastapi import APIRouter
from backend.routers import users, chamas, members, billing

# Create v1 router
v1_router = APIRouter(tags=["v1"])

# Include existing routers under v1 namespace
v1_router.include_router(users.router, prefix="/users", tags=["users"])
v1_router.include_router(chamas.router, prefix="/chamas", tags=["chamas"])
v1_router.include_router(members.router, prefix="/chamas/{chama_id}", tags=["members"])
v1_router.include_router(billing.router, prefix="/billing", tags=["billing"])

# Note: WebSocket router temporarily excluded from versioning
# Will be added later when needed
