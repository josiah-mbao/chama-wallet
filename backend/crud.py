from sqlalchemy.orm import Session
import models, schemas

def get_members(db: Session):
    return db.query(models.Member).all()

def create_member(db: Session, member: schemas.MemberCreate):
    db_member = models.Member(name=member.name, email=member.email)
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

def create_contribution(db: Session, contribution: schemas.ContributionCreate):
    db_contribution = models.Contribution(**contribution.dict())
    db.add(db_contribution)
    db.commit()
    db.refresh(db_contribution)
    return db_contribution
 
