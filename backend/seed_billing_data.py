#!/usr/bin/env python3
"""
Seed script for billing data - creates default subscription plans.
Run this after setting up the database.
"""
import sys
import os

from backend.database import get_db
from backend.models.subscription import SubscriptionPlan, SubscriptionPlanEnum
from sqlalchemy.orm import Session

def seed_subscription_plans(db: Session):
    """Create default subscription plans"""

    # Check if plans already exist
    existing_plans = db.query(SubscriptionPlan).count()
    if existing_plans > 0:
        print("✅ Subscription plans already exist, skipping seeding")
        return

    plans = [
        {
            "name": "Basic Chama",
            "plan_type": SubscriptionPlanEnum.basic,
            "description": "Perfect for small community groups just starting out",
            "price_monthly": 9.99,
            "price_yearly": 99.99,
            "max_members": 50,
            "max_contributions": 1000,
            "max_storage_gb": 1,
            "priority_support": False
        },
        {
            "name": "Premium Chama",
            "plan_type": SubscriptionPlanEnum.premium,
            "description": "Ideal for growing communities with advanced features",
            "price_monthly": 24.99,
            "price_yearly": 249.99,
            "max_members": 500,
            "max_contributions": 10000,
            "max_storage_gb": 10,
            "priority_support": False
        },
        {
            "name": "Enterprise Chama",
            "plan_type": SubscriptionPlanEnum.enterprise,
            "description": "For large organizations with unlimited potential",
            "price_monthly": 99.99,
            "price_yearly": 999.99,
            "max_members": -1,  # Unlimited
            "max_contributions": -1,  # Unlimited
            "max_storage_gb": 100,
            "priority_support": True
        }
    ]

    created_plans = []
    for plan_data in plans:
        plan = SubscriptionPlan(**plan_data)
        db.add(plan)
        created_plans.append(plan)
        print(f"✅ Created plan: {plan.name} (${plan.price_monthly}/month)")

    db.commit()

    # Verify creation
    total_plans = db.query(SubscriptionPlan).count()
    print(f"✅ Total subscription plans in database: {total_plans}")

    return created_plans

def main():
    """Main seeding function"""
    print("🌱 Seeding billing data...")

    try:
        db = next(get_db())

        # Seed subscription plans
        plans = seed_subscription_plans(db)

        print("🎉 Billing data seeding completed successfully!")
        print(f"📋 Available plans: {[plan.name for plan in plans]}")

        db.close()

    except Exception as e:
        print(f"❌ Seeding failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
