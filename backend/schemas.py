# backend/schemas.py

from pydantic import BaseModel, ConfigDict, EmailStr
from backend.models.user import UserRole
from typing import List, Optional
from datetime import datetime

# --- JWT Utility Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str
    role: Optional[UserRole] = UserRole.member

class User(UserBase):
    id: int
    is_active: bool = True
    role: UserRole
    model_config = ConfigDict(from_attributes=True)

# --- Chama Schemas ---
class ChamaBase(BaseModel):
    name: str
    description: Optional[str] = None

class ChamaCreate(ChamaBase):
    pass  # JWT provides creator_id

class Chama(ChamaBase):
    id: int
    created_at: datetime
    created_by_user_id: int
    model_config = ConfigDict(from_attributes=True)

# --- Membership Schemas ---
class Membership(BaseModel):
    user_id: int
    chama_id: Optional[int] = None  # Make this optional
    role: str
    model_config = ConfigDict(from_attributes=True)

# Chama with memberships
class ChamaWithMembers(Chama):
    memberships: List[Membership] = []
    model_config = ConfigDict(from_attributes=True)

# --- Contribution Schemas ---
class ContributionBase(BaseModel):
    amount: float

class ContributionCreate(ContributionBase):
    pass  # user_id and chama_id derived from JWT and route

class Contribution(ContributionBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Request Schemas ---
class AddMemberRequest(BaseModel):
    member_email: str

# --- Summary and Analytics Schemas ---
class LatestContribution(BaseModel):
    amount: float
    member: str
    timestamp: str  # ISO8601 datetime string

class ChamaSummary(BaseModel):
    chama_id: int
    name: str
    total_members: int
    total_contributions: float
    total_contributions_count: int
    latest_contribution: Optional[LatestContribution] = None
    last_updated: str  # ISO8601 datetime string
    status: Optional[str] = None

class MonthlyContribution(BaseModel):
    month: str  # YYYY-MM format
    total: float
    transactions: int

class TopContributor(BaseModel):
    member: str
    total_contributed: float

class ContributionFrequency(BaseModel):
    weekly: int
    monthly: int

class ChamaAnalytics(BaseModel):
    chama_id: int
    monthly_contributions: List[MonthlyContribution]
    top_contributors: List[TopContributor]
    average_contribution: float
    contribution_frequency: ContributionFrequency
    growth_rate: str  # Percentage string like "12.5%"
    trend: str  # "increasing", "stable", "decreasing"
    last_updated: str  # ISO8601 datetime string
    status: Optional[str] = None

# --- WebSocket Event Schemas ---
class WebSocketEventPayload(BaseModel):
    summary: Optional[ChamaSummary] = None
    analytics: Optional[ChamaAnalytics] = None
    contribution: Optional[Contribution] = None

class WebSocketEvent(BaseModel):
    event_type: str  # "CONTRIBUTION_CREATED", "MEMBER_ADDED", "CHAMA_UPDATED", "ANALYTICS_UPDATED"
    timestamp: str  # ISO8601 datetime string
    payload: WebSocketEventPayload

# --- WebSocket Event Schemas ---
class WebSocketEventPayload(BaseModel):
    summary: Optional[ChamaSummary] = None
    analytics: Optional[ChamaAnalytics] = None
    contribution: Optional[Contribution] = None

class WebSocketEvent(BaseModel):
    event_type: str  # "CONTRIBUTION_CREATED", "MEMBER_ADDED", "CHAMA_UPDATED", "ANALYTICS_UPDATED"
    timestamp: str  # ISO8601 datetime string

class ValidationErrorResponse(BaseModel):
    error_code: str = "validation_error"
    detail: str = "Validation failed"
    errors: List[ValidationErrorDetail] = []

# --- WebSocket Event Schemas ---
class WebSocketEventPayload(BaseModel):
    summary: Optional[ChamaSummary] = None
    analytics: Optional[ChamaAnalytics] = None
    contribution: Optional[Contribution] = None

class WebSocketEvent(BaseModel):
    event_type: str  # "CONTRIBUTION_CREATED", "MEMBER_ADDED", "CHAMA_UPDATED", "ANALYTICS_UPDATED"
    timestamp: str  # ISO8601 datetime string
