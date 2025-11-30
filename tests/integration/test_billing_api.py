"""
Integration tests for billing API endpoints.
Tests subscription management, payment processing, and billing operations.
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models.user import User, UserRole
from backend.models.chama import Chama
from backend.models.membership import Membership, MembershipRole
from backend.models.subscription import SubscriptionPlan, Subscription
from backend.security import get_password_hash
from backend.database import get_db


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def init_billing_data(db_session):
    """Initialize test data for billing tests."""
    # Clear existing data
    from sqlalchemy import text
    db_session.execute(text("DELETE FROM subscriptions"))
    db_session.execute(text("DELETE FROM subscription_plans"))
    db_session.execute(text("DELETE FROM memberships"))
    db_session.execute(text("DELETE FROM contributions"))
    db_session.execute(text("DELETE FROM chamas"))
    db_session.execute(text("DELETE FROM users"))
    db_session.commit()

    # Create users
    owner = User(
        email="billing_owner@test.com",
        first_name="Billing",
        last_name="Owner",
        hashed_password=get_password_hash("billingpass"),
        role=UserRole.owner,
        is_active=True
    )
    db_session.add(owner)
    db_session.commit()

    # Create chama
    chama = Chama(
        name="Billing Test Chama",
        description="Test chama for billing",
        created_by_user_id=owner.id
    )
    db_session.add(chama)
    db_session.commit()

    # Create membership
    membership = Membership(
        user_id=owner.id,
        chama_id=chama.id,
        role=MembershipRole.owner
    )
    db_session.add(membership)
    db_session.commit()

    # Create subscription plans
    basic_plan = SubscriptionPlan(
        name="Basic Plan",
        plan_type="basic",
        description="Basic subscription plan",
        price_monthly=50.0,
        price_yearly=500.0,
        max_members=10,
        max_contributions=100,
        max_storage_gb=1,
        is_active=True
    )

    premium_plan = SubscriptionPlan(
        name="Premium Plan",
        plan_type="premium",
        description="Premium subscription plan",
        price_monthly=100.0,
        price_yearly=1000.0,
        max_members=50,
        max_contributions=1000,
        max_storage_gb=10,
        is_active=True
    )
    db_session.add_all([basic_plan, premium_plan])
    db_session.commit()

    return {
        "owner": owner,
        "chama": chama,
        "membership": membership,
        "basic_plan": basic_plan,
        "premium_plan": premium_plan
    }


def login_get_token(client, email, password):
    """Helper to login and get access token."""
    # Use versioned API endpoints since CI uses main app, not test app
    register_response = client.post(
        "/api/v1/users/",
        json={
            "email": email,
            "first_name": email.split('@')[0],
            "last_name": "Test",
            "password": password
        }
    )
    # Registration might fail if user exists, that's ok

    # Now try to login
    response = client.post("/api/v1/users/token", data={"username": email, "password": password})
    assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"
    return response.json()["access_token"]


class TestSubscriptionPlans:
    """Test subscription plan endpoints."""

    def test_get_subscription_plans(self, client, init_billing_data):
        """Test getting all subscription plans."""
        response = client.get("/billing/plans")
        assert response.status_code == 200

        plans = response.json()
        assert len(plans) == 2

        # Check plan structure
        plan = plans[0]
        assert "id" in plan
        assert "name" in plan
        assert "description" in plan
        assert "price_monthly" in plan
        assert "price_yearly" in plan
        assert "max_members" in plan
        assert "max_contributions" in plan
        assert "max_storage_gb" in plan

    def test_get_subscription_plan_by_id(self, client, init_billing_data):
        """Test getting a specific subscription plan."""
        plan_id = init_billing_data["basic_plan"].id

        response = client.get(f"/billing/plans/{plan_id}")
        assert response.status_code == 200

        plan = response.json()
        assert plan["id"] == plan_id
        assert plan["name"] == "Basic Plan"
        assert plan["price_monthly"] == 50.0

    def test_get_subscription_plan_not_found(self, client, init_billing_data):
        """Test getting a non-existent subscription plan."""
        response = client.get("/billing/plans/99999")
        assert response.status_code == 404
        assert "Subscription plan not found" in response.json()["detail"]


class TestSubscriptionManagement:
    """Test subscription creation and management."""

    @patch('backend.routers.billing.paystack_client.create_customer', new_callable=AsyncMock)
    def test_create_subscription_success(self, mock_create_customer, client, init_billing_data):
        """Test successful subscription creation."""
        # Mock Paystack customer creation
        mock_create_customer.return_value = {
            "id": "test_customer_123",
            "email": "billing_owner@test.com"
        }

        token = login_get_token(client, "billing_owner@test.com", "billingpass")

        chama_id = init_billing_data["chama"].id
        plan_id = init_billing_data["basic_plan"].id

        # Set tenant context by accessing a tenant-specific endpoint first
        # This simulates the middleware setting the tenant context
        with patch('backend.database.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = chama_id

            response = client.post(
                "/billing/subscription",
                json={
                    "plan_id": plan_id,
                    "billing_cycle": "monthly"
                },
                headers={"Authorization": f"Bearer {token}"}
            )

            # Should succeed in test mode
            assert response.status_code in [200, 201]

    def test_create_subscription_duplicate(self, client, init_billing_data):
        """Test creating subscription when chama already has one."""
        token = login_get_token(client, "billing_owner@test.com", "billingpass")

        chama_id = init_billing_data["chama"].id
        plan_id = init_billing_data["basic_plan"].id

        # Create a subscription directly in the database first
        subscription = Subscription(
            chama_id=chama_id,
            plan_id=plan_id,
            status="active",
            billing_cycle="monthly",
            stripe_customer_id="test_customer_123"
        )
        db = next(get_db())
        db.add(subscription)
        db.commit()

        # Now try to create another subscription
        with patch('backend.database.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = chama_id

            response = client.post(
                "/billing/subscription",
                json={
                    "plan_id": plan_id,
                    "billing_cycle": "monthly"
                },
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 409
            assert "already has an active subscription" in response.json()["detail"]

    def test_create_subscription_invalid_plan(self, client, init_billing_data):
        """Test creating subscription with invalid plan ID."""
        token = login_get_token(client, "billing_owner@test.com", "billingpass")

        chama_id = init_billing_data["chama"].id

        with patch('backend.database.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = chama_id

            response = client.post(
                "/billing/subscription",
                json={
                    "plan_id": 99999,  # Non-existent plan
                    "billing_cycle": "monthly"
                },
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 404
            assert "Subscription plan not found" in response.json()["detail"]

    def test_get_chama_subscription(self, client, init_billing_data):
        """Test getting a chama's subscription."""
        # Create a subscription first
        chama_id = init_billing_data["chama"].id
        plan_id = init_billing_data["basic_plan"].id

        subscription = Subscription(
            chama_id=chama_id,
            plan_id=plan_id,
            status="active",
            billing_cycle="monthly",
            stripe_customer_id="test_customer_123"
        )
        db = next(get_db())
        db.add(subscription)
        db.commit()

        token = login_get_token(client, "billing_owner@test.com", "billingpass")

        response = client.get(f"/billing/chamas/{chama_id}/subscription",
                            headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        data = response.json()
        assert data["chama_id"] == chama_id
        assert data["plan_id"] == plan_id
        assert data["status"] == "active"

    def test_get_chama_subscription_no_access(self, client, init_billing_data):
        """Test getting subscription without membership access."""
        # Create another user who doesn't have access
        db = next(get_db())
        other_user = User(
            email="other@test.com",
            first_name="Other",
            last_name="User",
            hashed_password=get_password_hash("otherpass"),
            role=UserRole.member,
            is_active=True
        )
        db.add(other_user)
        db.commit()

        chama_id = init_billing_data["chama"].id
        token = login_get_token(client, "other@test.com", "otherpass")

        response = client.get(f"/billing/chamas/{chama_id}/subscription",
                            headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 403
        assert "You do not have access to this chama" in response.json()["detail"]


class TestPaymentMethods:
    """Test payment method management."""

    def test_get_payment_methods_empty(self, client, init_billing_data):
        """Test getting payment methods when none exist."""
        token = login_get_token(client, "billing_owner@test.com", "billingpass")

        chama_id = init_billing_data["chama"].id

        with patch('backend.database.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = chama_id

            response = client.get("/billing/payment-methods",
                                headers={"Authorization": f"Bearer {token}"})

            assert response.status_code == 200
            assert response.json() == []

    def test_add_payment_method(self, client, init_billing_data):
        """Test adding a payment method."""
        token = login_get_token(client, "billing_owner@test.com", "billingpass")

        chama_id = init_billing_data["chama"].id

        with patch('backend.database.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = chama_id

            response = client.post(
                "/billing/payment-methods",
                json={
                    "type": "card",
                    "provider": "visa",
                    "card_number": "4111111111111111",
                    "expiry_month": 12,
                    "expiry_year": 2025
                },
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["type"] == "card"
            assert data["provider"] == "visa"
            assert data["last_four"] == "1111"
            assert data["is_default"] is True  # First method should be default


class TestPaymentProcessing:
    """Test payment processing endpoints."""

    @patch('backend.routers.billing.paystack_client.initialize_transaction', new_callable=AsyncMock)
    def test_initialize_payment_success(self, mock_init_transaction, client, init_billing_data):
        """Test successful payment initialization."""
        # Mock Paystack transaction initialization
        mock_init_transaction.return_value = {
            "url": "https://paystack.com/pay/test123",
            "reference": "test_ref_123"
        }

        # Create a subscription first
        chama_id = init_billing_data["chama"].id
        plan_id = init_billing_data["basic_plan"].id

        subscription = Subscription(
            chama_id=chama_id,
            plan_id=plan_id,
            status="active",
            billing_cycle="monthly",
            stripe_customer_id="test_customer_123"
        )
        db = next(get_db())
        db.add(subscription)
        db.commit()

        token = login_get_token(client, "billing_owner@test.com", "billingpass")

        with patch('backend.database.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = chama_id

            response = client.post(
                "/billing/initialize-payment?amount=100&description=Test%20Payment",
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "payment_url" in data
            assert "reference" in data
            assert data["amount"] == 100
            assert data["currency"] == "KES"

    def test_initialize_payment_no_subscription(self, client, init_billing_data):
        """Test payment initialization without active subscription."""
        token = login_get_token(client, "billing_owner@test.com", "billingpass")

        chama_id = init_billing_data["chama"].id

        with patch('backend.database.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = chama_id

            response = client.post(
                "/billing/initialize-payment?amount=100",
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 400
            assert "No active subscription found" in response.json()["detail"]


class TestUsageStats:
    """Test usage statistics endpoints."""

    def test_get_usage_stats_no_subscription(self, client, init_billing_data):
        """Test getting usage stats without subscription."""
        token = login_get_token(client, "billing_owner@test.com", "billingpass")

        chama_id = init_billing_data["chama"].id

        with patch('backend.database.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = chama_id

            response = client.get("/billing/usage",
                                headers={"Authorization": f"Bearer {token}"})

            assert response.status_code == 404
            assert "No active subscription found" in response.json()["detail"]

    def test_get_usage_stats_with_subscription(self, client, init_billing_data):
        """Test getting usage stats with active subscription."""
        # Create a subscription
        chama_id = init_billing_data["chama"].id
        plan_id = init_billing_data["basic_plan"].id

        subscription = Subscription(
            chama_id=chama_id,
            plan_id=plan_id,
            status="active",
            billing_cycle="monthly",
            stripe_customer_id="test_customer_123"
        )
        db = next(get_db())
        db.add(subscription)
        db.commit()

        token = login_get_token(client, "billing_owner@test.com", "billingpass")

        with patch('backend.database.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = chama_id

            response = client.get("/billing/usage",
                                headers={"Authorization": f"Bearer {token}"})

            assert response.status_code == 200
            data = response.json()

            assert "current_members" in data
            assert "current_contributions" in data
            assert "plan_limits" in data
            assert "usage_percentages" in data

            # Check plan limits
            assert data["plan_limits"]["max_members"] == 10
            assert data["plan_limits"]["max_contributions"] == 100


class TestWebhooks:
    """Test webhook processing."""

    def test_paystack_webhook_processing(self, client):
        """Test Paystack webhook processing."""
        webhook_data = {
            "event": "charge.success",
            "data": {
                "id": 123,
                "reference": "test_ref",
                "amount": 5000,
                "status": "success"
            }
        }

        response = client.post("/billing/webhooks", json=webhook_data)

        # Webhooks should always return 200 to acknowledge receipt
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["event"] == "charge.success"

    def test_paystack_webhook_invalid_data(self, client):
        """Test webhook processing with invalid data."""
        response = client.post("/billing/webhooks", json={})

        # Should still return 200 but with error status
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"


class TestSubscriptionUpdates:
    """Test subscription update operations."""

    def test_update_subscription_success(self, client, init_billing_data):
        """Test successful subscription update."""
        # Create a subscription first
        chama_id = init_billing_data["chama"].id
        plan_id = init_billing_data["basic_plan"].id
        premium_plan_id = init_billing_data["premium_plan"].id

        subscription = Subscription(
            chama_id=chama_id,
            plan_id=plan_id,
            status="active",
            billing_cycle="monthly",
            stripe_customer_id="test_customer_123"
        )
        db = next(get_db())
        db.add(subscription)
        db.commit()

        token = login_get_token(client, "billing_owner@test.com", "billingpass")

        with patch('backend.database.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = chama_id

            response = client.put(
                "/billing/subscription",
                json={
                    "plan_id": premium_plan_id,
                    "billing_cycle": "yearly"
                },
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["plan_id"] == premium_plan_id
            assert data["billing_cycle"] == "yearly"

    def test_cancel_subscription_success(self, client, init_billing_data):
        """Test successful subscription cancellation."""
        # Create a subscription first
        chama_id = init_billing_data["chama"].id
        plan_id = init_billing_data["basic_plan"].id

        subscription = Subscription(
            chama_id=chama_id,
            plan_id=plan_id,
            status="active",
            billing_cycle="monthly",
            stripe_customer_id="test_customer_123"
        )
        db = next(get_db())
        db.add(subscription)
        db.commit()

        token = login_get_token(client, "billing_owner@test.com", "billingpass")

        with patch('backend.database.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = chama_id

            response = client.delete("/billing/subscription",
                                   headers={"Authorization": f"Bearer {token}"})

            assert response.status_code == 200
            data = response.json()
            assert "cancel_at_period_end" in data
            assert data["cancel_at_period_end"] is True

    def test_cancel_subscription_no_subscription(self, client, init_billing_data):
        """Test cancelling subscription when none exists."""
        token = login_get_token(client, "billing_owner@test.com", "billingpass")

        chama_id = init_billing_data["chama"].id

        with patch('backend.database.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = chama_id

            response = client.delete("/billing/subscription",
                                   headers={"Authorization": f"Bearer {token}"})

            assert response.status_code == 404
            assert "No active subscription found" in response.json()["detail"]
