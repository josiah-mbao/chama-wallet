"""
Chama Wallet API v1 - Stable Production Release
Contains the current stable feature set with billing integration.
"""

from fastapi import APIRouter
from backend.routers import users, chamas, members
from backend.routers.billing import router as billing

# Create v1 router
v1_router = APIRouter(tags=["v1"])

# Include existing routers under v1 namespace
# Note: Routers from backend.routers.__init__.py are already APIRouter instances
v1_router.include_router(users, prefix="/users", tags=["users"])
v1_router.include_router(chamas, prefix="/chamas", tags=["chamas"])
v1_router.include_router(members, prefix="/chamas/{chama_id}", tags=["members"])
v1_router.include_router(billing, prefix="/billing", tags=["billing"])

# Note: WebSocket router temporarily excluded from versioning
# Will be added later when needed
