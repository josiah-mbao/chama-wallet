from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Enum, JSON
from sqlalchemy.sql import func
from backend.database import Base
import enum


class SubscriptionPlanEnum(str, enum.Enum):
    basic = "basic"
    premium = "premium"
    enterprise = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    cancelled = "cancelled"
    past_due = "past_due"
    trial = "trial"


class BillingCycle(str, enum.Enum):
    monthly = "monthly"
    yearly = "yearly"


class SubscriptionPlan(Base):
    """Global subscription plans available to all tenants"""
    __tablename__ = "subscription_plans"
    __table_args__ = {"schema": "public"} if __import__('os').getenv('DATABASE_URL', '').startswith('postgresql') else {}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    plan_type = Column(Enum(SubscriptionPlanEnum), nullable=False)
    description = Column(String)
    price_monthly = Column(Float, nullable=False)
    price_yearly = Column(Float, nullable=False)

    # Feature limits and entitlements
    max_members = Column(Integer, nullable=False)  # -1 for unlimited
    max_contributions = Column(Integer, nullable=False)  # -1 for unlimited
    max_storage_gb = Column(Integer, nullable=False)  # Storage quota in GB
    priority_support = Column(Boolean, default=False)
    custom_features = Column(JSON)  # JSON for custom feature flags

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Subscription(Base):
    """Tenant-specific subscription tracking"""
    __tablename__ = "subscriptions"
    __table_args__ = {"schema": "public"} if __import__('os').getenv('DATABASE_URL', '').startswith('postgresql') else {}

    id = Column(Integer, primary_key=True, index=True)
    chama_id = Column(Integer, ForeignKey("public.chamas.id"), nullable=False, unique=True)

    # Plan and billing info
    plan_id = Column(Integer, ForeignKey("public.subscription_plans.id"), nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.trial)
    billing_cycle = Column(Enum(BillingCycle), default=BillingCycle.monthly)

    # Dates
    trial_ends_at = Column(DateTime(timezone=True))  # When trial expires
    current_period_start = Column(DateTime(timezone=True))  # Start of current billing period
    current_period_end = Column(DateTime(timezone=True))  # End of current billing period
    cancel_at_period_end = Column(Boolean, default=False)  # Cancel at end of period
    cancelled_at = Column(DateTime(timezone=True))  # When subscription was cancelled

    # Stripe/external service IDs
    stripe_customer_id = Column(String, unique=True)
    stripe_subscription_id = Column(String, unique=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Invoice(Base):
    """Billing history and invoice records"""
    __tablename__ = "invoices"
    __table_args__ = {"schema": "public"} if __import__('os').getenv('DATABASE_URL', '').startswith('postgresql') else {}

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("public.subscriptions.id"), nullable=False)

    # Invoice details
    invoice_number = Column(String, unique=True, nullable=False)  # e.g., INV-001
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD", nullable=False)
    status = Column(String, nullable=False)  # draft, open, paid, void, uncollectible

    # Dates
    invoice_date = Column(DateTime(timezone=True), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    paid_at = Column(DateTime(timezone=True))

    # Stripe/external service IDs
    stripe_invoice_id = Column(String, unique=True)

    # Invoice data
    line_items = Column(JSON)  # Detailed breakdown of charges
    tax_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PaymentMethod(Base):
    """Stored payment methods for subscriptions"""
    __tablename__ = "payment_methods"
    __table_args__ = {"schema": "public"} if __import__('os').getenv('DATABASE_URL', '').startswith('postgresql') else {}

    id = Column(Integer, primary_key=True, index=True)
    chama_id = Column(Integer, ForeignKey("public.chamas.id"), nullable=False)

    # Payment method details
    type = Column(String, nullable=False)  # card, bank_account, mpesa, paypal
    provider = Column(String, nullable=False)  # stripe, paypal, mpesa

    # Provider-specific IDs and data
    stripe_payment_method_id = Column(String, unique=True)
    paypal_billing_agreement_id = Column(String)

    # Masked payment details for display
    last_four = Column(String(4))  # Last 4 digits for cards
    card_brand = Column(String)  # visa, mastercard, etc.
    expiry_month = Column(Integer)
    expiry_year = Column(Integer)

    # Mobile money details (M-Pesa, etc.)
    phone_number = Column(String)

    # Status
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
