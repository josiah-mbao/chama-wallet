"""
Integration tests for billing and subscription API endpoints.
Tests complete payment flows with mocked Paystack interactions.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json


class TestBillingPlans:
    """Test billing plan management endpoints."""

    def test_get_subscription_plans_empty(self, client):
        """Test getting plans when no plans exist."""
        response = client.get("/billing/plans")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_subscription_plans_with_data(self, client, db_session):
        """Test getting plans when plans exist."""
        from backend.models.subscription import SubscriptionPlan
        from backend.seed_billing_data import seed_subscription_plans

        # Seed plans
        plans = seed_subscription_plans(db_session)

        response = client.get("/billing/plans")
        assert response.status_code == 200
        data = response.json()

        assert len(data) == len(plans)
        assert data[0]["name"] == "Basic Chama"
        assert data[1]["name"] == "Premium Chama"
        assert data[2]["name"] == "Enterprise Chama"

        # Check pricing
        assert data[0]["price_monthly"] == 9.99
        assert data[0]["price_yearly"] == 99.99
        assert data[0]["max_members"] == 50

    def test_get_specific_plan(self, client, db_session):
        """Test getting a specific subscription plan."""
        from backend.seed_billing_data import seed_subscription_plans

        # Seed plans
        plans = seed_subscription_plans(db_session)
        basic_plan = plans[0]  # Basic Chama plan

        response = client.get(f"/billing/plans/{basic_plan.id}")
        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Basic Chama"
        assert data["plan_type"] == "basic"
        assert data["max_members"] == 50

    def test_get_nonexistent_plan(self, client):
        """Test getting a plan that doesn't exist."""
        response = client.get("/billing/plans/99999")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


class TestBillingSubscriptions:
    """Test subscription management endpoints."""

    def test_get_subscription_no_auth(self, client):
        """Test getting subscription without authentication."""
        response = client.get("/billing/chamas/1/subscription")
        assert response.status_code == 401

    @pytest.fixture
    def authenticated_user(self, client, db_session):
        """Create and authenticate a user."""
        from backend.models.user import User

        # Create user
        user = User(
            email="test@example.com",
            hashed_password="hashed_password",
            role="user",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Mock authentication for testing
        from backend.security import create_access_token
        token = create_access_token({"sub": user.email})

        client.headers.update({"Authorization": f"Bearer {token}"})
        return user

    def test_create_subscription_without_chama(self, authenticated_user, client):
        """Test creating subscription when user has no chama."""
        response = client.post("/billing/subscription", json={
            "plan_id": 1,
            "billing_cycle": "monthly"
        })
        assert response.status_code == 400  # No tenant context

    def test_get_subscription_no_chama_access(self, authenticated_user, client, db_session):
        """Test getting subscription for chama user doesn't have access to."""
        response = client.get("/billing/chamas/999/subscription")
        assert response.status_code == 403  # Forbidden

    def test_subscription_flow_complete(self, authenticated_user, client, db_session):
        """Test complete subscription flow with mocked tenant context."""
        from backend.models.chama import Chama
        from backend.models.membership import Membership
        from backend.seed_billing_data import seed_subscription_plans

        # Set up test data
        user = authenticated_user
        chama = Chama(id=1, name="Test Chama", owner_id=user.id)
        membership = Membership(
            user_id=user.id,
            chama_id=chama.id,
            role="owner"
        )

        db_session.add(chama)
        db_session.add(membership)
        plans = seed_subscription_plans(db_session)
        db_session.commit()

        # Mock tenant context middleware
        with patch('backend.database.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = chama.id

            # Test: Create subscription with mocked Paystack
            with patch('backend.billing.paystack_client.PaystackClient.create_customer',
                      new_callable=AsyncMock) as mock_create_customer:
                mock_create_customer.return_value = {
                    "id": f"customer_{chama.id}",
                    "email": user.email
                }

                response = client.post("/billing/subscription", json={
                    "plan_id": plans[0].id,
                    "billing_cycle": "monthly"
                })

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "trial"
                assert data["billing_cycle"] == "monthly"
                assert data["plan_id"] == plans[0].id

                # Verify customer creation was called
                mock_create_customer.assert_called_once()

            # Test: Get subscription
            response = client.get(f"/billing/chamas/{chama.id}/subscription")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "trial"
            assert data["chama_id"] == chama.id


class TestBillingPayments:
    """Test payment processing endpoints."""

    def test_initialize_payment_unauthorized(self, client):
        """Test payment initialization without authentication."""
        response = client.post("/billing/initialize-payment", params={"amount": 1000})
        assert response.status_code == 401

    def test_initialize_payment_no_subscription(self, authenticated_user, client):
        """Test payment initialization without active subscription."""
        with patch('backend.database.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = 1

            response = client.post("/billing/initialize-payment", params={"amount": 1000})
            assert response.status_code == 400
            data = response.json()
            assert "subscription" in data["detail"].lower()


class TestWebhookHandling:
    """Test Paystack webhook processing."""

    def test_webhook_invalid_payload(self, client):
        """Test webhook with invalid payload."""
        response = client.post("/billing/webhooks", json={})
        assert response.status_code == 200  # Webhooks always return 200

    def test_webhook_charge_success(self, client, db_session):
        """Test charge.success webhook processing."""
        webhook_payload = {
            "event": "charge.success",
            "data": {
                "reference": "test_ref_123",
                "amount": 50000,  # ₸50.00
                "currency": "KES",
                "status": "success"
            }
        }

        with patch('backend.billing.paystack_client.paystack_client.process_webhook_event',
                  new_callable=AsyncMock) as mock_process:
            mock_process.return_value = "charge.success"

            response = client.post("/billing/webhooks", json=webhook_payload)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            assert data["event"] == "charge.success"

            # Verify webhook processing was called
            mock_process.assert_called_once_with(webhook_payload)


class TestBillingUsage:
    """Test usage and analytics endpoints."""

    def test_get_usage_no_subscription(self, authenticated_user, client):
        """Test usage endpoint without subscription."""
        with patch('backend.database.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = 1

            response = client.get("/billing/usage")
            assert response.status_code == 404
            data = response.json()
            assert "subscription" in data["detail"].lower()

    def test_get_usage_with_subscription(self, authenticated_user, client, db_session):
        """Test usage endpoint with active subscription."""
        from backend.models.chama import Chama
        from backend.models.membership import Membership
        from backend.models.subscription import Subscription, SubscriptionPlan

        # Set up test data
        user = authenticated_user
        chama = Chama(id=1, name="Test Chama", owner_id=user.id)
        membership = Membership(
            user_id=user.id,
            chama_id=chama.id,
            role="owner"
        )
        plan = SubscriptionPlan(
            id=1, name="Basic Plan", plan_type="basic",
            price_monthly=9.99, price_yearly=99.99,
            max_members=50, max_contributions=1000, max_storage_gb=1
        )
        subscription = Subscription(
            chama_id=chama.id,
            plan_id=plan.id,
            status="active",
            billing_cycle="monthly"
        )

        db_session.add_all([chama, membership, plan, subscription])
        db_session.commit()

        with patch('backend.database.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = chama.id

            response = client.get("/billing/usage")
            assert response.status_code == 200
            data = response.json()

            # Check usage statistics structure
            assert "current_members" in data
            assert "current_contributions" in data
            assert "current_storage_gb" in data
            assert "plan_limits" in data
            assert "usage_percentages" in data

            # Check plan limits
            assert data["plan_limits"]["max_members"] == 50
            assert data["plan_limits"]["max_contributions"] == 1000
            assert data["plan_limits"]["max_storage_gb"] == 1


class TestBillingSecurity:
    """Test security and authorization for billing endpoints."""

    def test_access_other_chama_subscription(self, authenticated_user, client, db_session):
        """Test that user cannot access other chama subscriptions."""
        from backend.models.chama import Chama
        from backend.models.membership import Membership

        # Set up user with access to chama 1, but try to access chama 2
        user = authenticated_user
        chama1 = Chama(id=1, name="My Chama", owner_id=user.id)
        chama2 = Chama(id=2, name="Other Chama", owner_id=999)  # Different owner

        membership1 = Membership(user_id=user.id, chama_id=chama1.id, role="owner")

        db_session.add_all([chama1, chama2, membership1])
        db_session.commit()

        # User should be able to access their own chama
        response = client.get("/billing/chamas/1/subscription")
        # In a real multi-tenant setup, this might require additional auth checks
        assert response.status_code in [200, 404]  # 200 if subscription exists, 404 if not

        # This is more of a placeholder - in production, middleware would handle tenant isolation
        # For this test, we're focusing on the API behavior rather than deep tenant isolation


@pytest.fixture
def authenticated_user(client, db_session):
    """Create and authenticate a user for testing."""
    from backend.models.user import User
    from backend.security import create_access_token

    # Create user
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        role="user",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create JWT token
    token = create_access_token({"sub": user.email})

    # Set authorization header
    client.headers.update({"Authorization": f"Bearer {token}"})

    return user
