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

# --- Subscription Plan Schemas ---
class SubscriptionPlanBase(BaseModel):
    name: str
    plan_type: str  # basic, premium, enterprise
    description: Optional[str] = None
    price_monthly: float
    price_yearly: float
    max_members: int  # -1 for unlimited
    max_contributions: int  # -1 for unlimited
    max_storage_gb: int
    priority_support: bool = False

class SubscriptionPlanCreate(SubscriptionPlanBase):
    pass

class SubscriptionPlan(SubscriptionPlanBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# --- Subscription Schemas ---
class SubscriptionBase(BaseModel):
    plan_id: int
    billing_cycle: str = "monthly"  # monthly, yearly

class SubscriptionCreate(SubscriptionBase):
    pass

class SubscriptionUpdate(BaseModel):
    plan_id: Optional[int] = None
    billing_cycle: Optional[str] = None
    cancel_at_period_end: Optional[bool] = None

class Subscription(SubscriptionBase):
    id: int
    chama_id: int
    status: str
    trial_ends_at: Optional[datetime] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    cancelled_at: Optional[datetime] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# --- Invoice Schemas ---
class InvoiceLineItem(BaseModel):
    description: str
    amount: float
    quantity: Optional[int] = 1

class InvoiceBase(BaseModel):
    amount: float
    currency: str = "USD"
    invoice_date: datetime
    due_date: datetime

class InvoiceCreate(InvoiceBase):
    line_items: List[InvoiceLineItem] = []
    tax_amount: float = 0.0
    discount_amount: float = 0.0

class Invoice(InvoiceBase):
    id: int
    subscription_id: int
    invoice_number: str
    status: str
    paid_at: Optional[datetime] = None
    stripe_invoice_id: Optional[str] = None
    line_items: List[InvoiceLineItem] = []
    tax_amount: float
    discount_amount: float
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Payment Method Schemas ---
class PaymentMethodBase(BaseModel):
    type: str  # card, bank_account, mpesa, paypal
    provider: str  # stripe, paypal, mpesa

class PaymentMethodCreate(PaymentMethodBase):
    # Card payment
    card_number: Optional[str] = None
    expiry_month: Optional[int] = None
    expiry_year: Optional[int] = None
    cvv: Optional[str] = None

    # Mobile money
    phone_number: Optional[str] = None

    # Bank account
    account_number: Optional[str] = None
    routing_number: Optional[str] = None

class PaymentMethod(PaymentMethodBase):
    id: int
    chama_id: int
    stripe_payment_method_id: Optional[str] = None
    paypal_billing_agreement_id: Optional[str] = None
    last_four: Optional[str] = None
    card_brand: Optional[str] = None
    expiry_month: Optional[int] = None
    expiry_year: Optional[int] = None
    phone_number: Optional[str] = None
    is_default: bool = False
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# --- Billing Analytics Schemas ---
class BillingSummary(BaseModel):
    total_revenue: float
    monthly_recurring_revenue: float
    active_subscriptions: int
    trial_subscriptions: int
    cancelled_subscriptions: int
    churn_rate: float  # Percentage
    average_revenue_per_user: float

# --- Usage and Limits Schemas ---
class UsageStats(BaseModel):
    current_members: int
    current_contributions: int
    current_storage_gb: float
    plan_limits: dict
    usage_percentages: dict

class LimitExceededError(BaseModel):
    feature: str
    current_usage: int
    limit: int
    upgrade_required: bool

# --- Error Response Schemas ---
class ErrorResponse(BaseModel):
    error_code: str
    detail: str

class ValidationErrorDetail(BaseModel):
    field: str
    message: str

class ValidationErrorResponse(BaseModel):
    error_code: str = "validation_error"
    detail: str = "Validation failed"
    errors: List[ValidationErrorDetail] = []
