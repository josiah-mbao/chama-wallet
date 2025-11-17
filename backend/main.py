# backend/main.py
from fastapi import FastAPI
from backend.database import get_db
from backend.routers.users import router as users_router
from backend.routers.chamas import router as chamas_router
from backend.routers.members import router as members_router

app = FastAPI(
    title="Chama Wallet API",
)

# Include all routers
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(chamas_router, prefix="/chamas", tags=["chamas"])
app.include_router(members_router, prefix="/chamas/{chama_id}", tags=["members"])

@app.get("/", tags=["Health"])
def read_root():
    return {"message": "Welcome to the Chama Wallet API - Status: Operational"}
