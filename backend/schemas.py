from pydantic import BaseModel, ConfigDict
from typing import List

class ContributionBase(BaseModel):
    amount: float


class ContributionCreate(ContributionBase):
    member_id: int


class Contribution(ContributionBase):
    id: int
    member_id: int

    model_config = ConfigDict(from_attributes=True)


class MemberBase(BaseModel):
    name: str
    email: str


class MemberCreate(MemberBase):
    pass


class Member(MemberBase):
    id: int
    contributions: List[Contribution] = []

    model_config = ConfigDict(from_attributes=True)
