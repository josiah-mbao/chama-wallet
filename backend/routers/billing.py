"""
Billing and subscription management router for Paystack integration.
"""
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.security import get_current_tenant_user
from backend.schemas import (
    SubscriptionPlan,
    Subscription,
    SubscriptionCreate,
    SubscriptionUpdate,
    Invoice,
    PaymentMethod,
    PaymentMethodCreate,
    UsageStats,
    BillingSummary
)
from backend.models.subscription import (
    SubscriptionPlan as SubscriptionPlanModel,
    Subscription as SubscriptionModel,
    Invoice as InvoiceModel,
    PaymentMethod as PaymentMethodModel
)
from backend.models.user import User
from backend.models.chama import Chama
from backend.billing.paystack_client import paystack_client
from backend.crud import create_chama_member

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/billing",
    tags=["billing"],
    responses={404: {"description": "Not found"}},
)

# ============ SUBSCRIPTION PLAN ENDPOINTS ============

@router.get("/plans", response_model=List[SubscriptionPlan])
async def get_subscription_plans(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Get all available subscription plans."""
    plans = db.query(SubscriptionPlanModel)\
        .filter(SubscriptionPlanModel.is_active == True)\
        .offset(skip)\
        .limit(limit)\
        .all()

    logger.info(f"Retrieved {len(plans)} subscription plans")
    return plans

@router.get("/plans/{plan_id}", response_model=SubscriptionPlan)
async def get_subscription_plan(
    plan_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific subscription plan."""
    plan = db.query(SubscriptionPlanModel).filter(
        SubscriptionPlanModel.id == plan_id,
        SubscriptionPlanModel.is_active == True
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found"
        )

    return plan

# ============ SUBSCRIPTION MANAGEMENT ============

@router.get("/subscription", response_model=Optional[Subscription])
async def get_chama_subscription(
    current_user: User = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """Get the current chama's subscription status."""
    # Get chama ID from the URL path (set by tenant middleware)
    from backend.database import current_tenant

    tenant_id = current_tenant.get()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context not available"
        )

    subscription = db.query(SubscriptionModel).filter(
        SubscriptionModel.chama_id == tenant_id
    ).first()

    if not subscription:
        return None

    return subscription

@router.post("/subscription", response_model=Subscription)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user: User = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """Create a new subscription for the chama."""
    from backend.database import current_tenant

    tenant_id = current_tenant.get()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context not available"
        )

    # Check if chama already has a subscription
    existing_sub = db.query(SubscriptionModel).filter(
        SubscriptionModel.chama_id == tenant_id
    ).first()

    if existing_sub:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chama already has an active subscription"
        )

    # Get the plan
    plan = db.query(SubscriptionPlanModel).filter(
        SubscriptionPlanModel.id == subscription_data.plan_id,
        SubscriptionPlanModel.is_active == True
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found"
        )

    # Create Paystack customer (this would normally be done earlier)
    chama = db.query(Chama).filter(Chama.id == tenant_id).first()
    if not chama:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chama not found"
        )

    # For demo purposes, create a customer with basic info
    # In production, you'd collect more customer info
    try:
        if paystack_client.is_test_mode:
            # Return mock customer data for tests
            paystack_customer = {
                "id": f"test_customer_{tenant_id}",
                "email": current_user.email,
                "createdAt": datetime.utcnow().isoformat()
            }
            logger.info("PaystackClient in test mode - using mock customer data")
        else:
            paystack_customer = await paystack_client.create_customer(
                email=current_user.email,
                first_name=current_user.email.split('@')[0],  # Simple name extraction
                metadata={"chama_id": tenant_id, "user_id": current_user.id}
            )

        # Create local subscription record
        subscription = SubscriptionModel(
            chama_id=tenant_id,
            plan_id=subscription_data.plan_id,
            status="trial",
            billing_cycle=subscription_data.billing_cycle,
            stripe_customer_id=paystack_customer.get("id")
        )

        db.add(subscription)
        db.commit()
        db.refresh(subscription)

        logger.info(f"Created subscription for chama {tenant_id}: plan {subscription_data.plan_id}")

        return subscription

    except Exception as e:
        logger.error(f"Failed to create subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subscription: {str(e)}"
        )

@router.put("/subscription", response_model=Subscription)
async def update_subscription(
    subscription_update: SubscriptionUpdate,
    current_user: User = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """Update the current chama's subscription."""
    from backend.database import current_tenant

    tenant_id = current_tenant.get()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context not available"
        )

    subscription = db.query(SubscriptionModel).filter(
        SubscriptionModel.chama_id == tenant_id
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )

    # Update fields
    if subscription_update.plan_id is not None:
        # Validate new plan
        plan = db.query(SubscriptionPlanModel).filter(
            SubscriptionPlanModel.id == subscription_update.plan_id,
            SubscriptionPlanModel.is_active == True
        ).first()

        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="New subscription plan not found"
            )

        subscription.plan_id = subscription_update.plan_id

    if subscription_update.billing_cycle is not None:
        subscription.billing_cycle = subscription_update.billing_cycle

    if subscription_update.cancel_at_period_end is not None:
        subscription.cancel_at_period_end = subscription_update.cancel_at_period_end

    subscription.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(subscription)

    logger.info(f"Updated subscription for chama {tenant_id}")
    return subscription

@router.delete("/subscription")
async def cancel_subscription(
    current_user: User = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """Cancel the current chama's subscription."""
    from backend.database import current_tenant

    tenant_id = current_tenant.get()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context not available"
        )

    subscription = db.query(SubscriptionModel).filter(
        SubscriptionModel.chama_id == tenant_id
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )

    # Mark for cancellation at period end
    subscription.cancel_at_period_end = True
    subscription.updated_at = datetime.utcnow()

    db.commit()

    logger.info(f"Marked subscription for cancellation: chama {tenant_id}")

    return {
        "message": "Subscription will be cancelled at the end of the current billing period",
        "cancel_at_period_end": subscription.cancel_at_period_end
    }

# ============ PAYMENT METHODS ============

@router.get("/payment-methods", response_model=List[PaymentMethod])
async def get_payment_methods(
    current_user: User = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """Get payment methods for the current chama."""
    from backend.database import current_tenant

    tenant_id = current_tenant.get()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context not available"
        )

    methods = db.query(PaymentMethodModel).filter(
        PaymentMethodModel.chama_id == tenant_id,
        PaymentMethodModel.is_active == True
    ).all()

    return methods

@router.post("/payment-methods", response_model=PaymentMethod)
async def add_payment_method(
    payment_method_data: PaymentMethodCreate,
    current_user: User = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """Add a payment method for the chama."""
    from backend.database import current_tenant

    tenant_id = current_tenant.get()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context not available"
        )

    # In a real implementation, you'd process this through Paystack
    # For now, create a local record
    payment_method = PaymentMethodModel(
        chama_id=tenant_id,
        type=payment_method_data.type,
        provider=payment_method_data.provider,
        is_default=False,
        is_active=True,
        # Mask the card number if provided
        last_four=payment_method_data.card_number[-4:] if payment_method_data.card_number else None,
        phone_number=payment_method_data.phone_number
    )

    # Set as default if no other methods exist
    existing_methods = db.query(PaymentMethodModel).filter(
        PaymentMethodModel.chama_id == tenant_id,
        PaymentMethodModel.is_active == True
    ).count()

    if existing_methods == 0:
        payment_method.is_default = True

    db.add(payment_method)
    db.commit()
    db.refresh(payment_method)

    logger.info(f"Added payment method for chama {tenant_id}: {payment_method_data.type}")

    return payment_method

# ============ PAYMENT PROCESSING ============

@router.post("/initialize-payment")
async def initialize_payment(
    amount: int,  # Amount in KES (converted to kobo)
    description: str = "Chama subscription payment",
    current_user: User = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """Initialize a payment transaction."""
    from backend.database import current_tenant

    tenant_id = current_tenant.get()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context not available"
        )

    try:
        # Verify chama has active subscription
        subscription = db.query(SubscriptionModel).filter(
            SubscriptionModel.chama_id == tenant_id
        ).first()

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active subscription found"
            )

        # Initialize transaction with Paystack (amount needs to be in kobo)
        amount_kobo = amount * 100  # Convert KES to kobo

        transaction = await paystack_client.initialize_transaction(
            email=current_user.email,
            amount=amount_kobo,
            currency="KES",
            reference=f"sub-{tenant_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            metadata={
                "chama_id": tenant_id,
                "user_id": current_user.id,
                "description": description
            }
        )

        logger.info(f"Initialized payment for chama {tenant_id}: {amount} KES")

        return {
            "payment_url": transaction["url"],
            "reference": transaction["reference"],
            "amount": amount,
            "currency": "KES"
        }

    except Exception as e:
        logger.error(f"Failed to initialize payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment initialization failed: {str(e)}"
        )

# ============ USAGE & ANALYTICS ============

@router.get("/usage", response_model=UsageStats)
async def get_usage_stats(
    current_user: User = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """Get current usage statistics for the chama."""
    from backend.database import current_tenant

    tenant_id = current_tenant.get()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context not available"
        )

    # Get subscription and plan limits
    subscription = db.query(SubscriptionModel).filter(
        SubscriptionModel.chama_id == tenant_id
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )

    plan = db.query(SubscriptionPlanModel).filter(
        SubscriptionPlanModel.id == subscription.plan_id
    ).first()

    # Calculate current usage (simplified)
    member_count = db.query(db.func.count()).select_from(db.query(Chama).filter(Chama.id == tenant_id).subquery()).scalar() or 0

    # In a real implementation, you'd count contributions from tenant schema
    contribution_count = 0  # Placeholder

    usage_stats = UsageStats(
        current_members=member_count,
        current_contributions=contribution_count,
        current_storage_gb=0,  # Placeholder
        plan_limits={
            "max_members": plan.max_members,
            "max_contributions": plan.max_contributions,
            "max_storage_gb": plan.max_storage_gb
        },
        usage_percentages={
            "members": (member_count / plan.max_members * 100) if plan.max_members > 0 else 0,
            "contributions": (contribution_count / plan.max_contributions * 100) if plan.max_contributions > 0 else 0,
            "storage": 0  # Placeholder calculation
        }
    )

    return usage_stats

# ============ WEBHOOK ENDPOINT ============

@router.post("/webhooks", status_code=status.HTTP_200_OK)
async def paystack_webhook(request: dict):
    """Handle Paystack webhook events."""
    try:
        # Process webhook (signature verification would happen here)
        event_type = await paystack_client.process_webhook_event(request)

        logger.info(f"Processed webhook event: {event_type}")

        # Return 200 to acknowledge receipt
        return {"status": "success", "event": event_type}

    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        # Still return 200 to avoid retries for bad data
        return {"status": "error", "message": str(e)}
