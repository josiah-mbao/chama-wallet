# backend/main.py

from fastapi import FastAPI
# Note: get_db is assumed to be defined in database.py
from database import get_db 

# 1. Import all router instances
from routers import users, chamas, members # Added chamas and members for completeness

# 2. Create the FastAPI app instance
app = FastAPI(
    title="Chama Wallet API", 
    # Use your proposed versioning (optional, but good practice)
    # prefix="/api/v1" if you want to include versioning here
)

# 3. Mount (Include) the routers
app.include_router(users.router)
app.include_router(chamas.router)
# NOTE: The old 'members' router should be cleaned up or its functionality moved
# to /chamas/{id}/members, as per your new plan. We'll leave the include for now.
# app.include_router(members.router)


# Optional: Keep a simple root route for status checks (Milestone 6).
@app.get("/", tags=["Health"])
def read_root():
    return {"message": "Welcome to the Chama Wallet API - Status: Operational"}
