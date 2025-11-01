from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from . import models, schemas, crud
from .database import SessionLocal, engine, Base

Base.metadat.create_all(bind=engine)

app = FastAPI(title="Chama Wallet API")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/members", response_model=list[schemas.Member])
def list_members(db: Session = Depends(get_db)):
    return crud.get_members(db)

@app.post("/members", response_model=schemas.Member)
def add_member(member: schemas.MemberCreate, db: Sesion = Depends(get_db)):
    return crud.create_member(db, member)

@app.post("/contributions", response_model=schemas.Contribution)
def add_contribution(contribution: schemas.ContributionCreate, db: Session = Depends(get_db)):
    return crud.create_contribution(db, contribution)
