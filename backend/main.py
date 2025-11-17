# backend/main.py
from fastapi import FastAPI
from backend.database import get_db 
from backend.routers import users, chamas, members

app = FastAPI(
    title="Chama Wallet API",
)

# Include all routers
app.include_router(users, tags=["users"])
app.include_router(chamas, tags=["chamas"])
app.include_router(members, tags=["members"])

@app.get("/", tags=["Health"])
def read_root():
    return {"message": "Welcome to the Chama Wallet API - Status: Operational"}
