# backend/main.py

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
# Note: You only need to import 'models' here if you still rely on 
# Base.metadata.create_all(bind=engine) outside of Alembic, but it's often imported for side effects.
import models
# You no longer need to import schemas or crud here.

from database import get_db 
# Note: We import get_db, but we don't define it here anymore (it belongs in database.py).

# 1. Import the router instances
from routers import members, users

# 2. Create the FastAPI app instance
app = FastAPI(title="Chama Wallet API")

# 3. Mount (Include) the routers
# This routes all endpoints from routers/users.py and routers/members.py 
# to the main application.
app.include_router(users.router)
app.include_router(members.router)

# Optional: Keep a simple root route for status checks.
@app.get("/")
def read_root():
    return {"message": "Welcome to the Chama Wallet API - Status: Operational"}