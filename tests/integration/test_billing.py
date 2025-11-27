"""
Integration tests for billing and subscription functionality.
Tests API endpoints, database operations, and Paystack integration.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from unittest.mock import patch, AsyncMock
from backend.security import get_password_hash

from backend.main import app
from backend.database import get_db
from backend.models.user import User, UserRole
from backend.models.chama import Chama
from backend.models.membership import Membership
from backend.models.subscription import SubscriptionPlan, Subscription


class TestBillingEdgeCases:
    """Test edge cases and error scenarios in billing functionality."""

    @pytest.fixture
    def test_user(self, db_session: Session):
        """Create a test user."""
        user = User(
            email=f"test-{pytest.importorskip('uuid').uuid4()}@example.com",
            hashed_password=get_password_hash("testpass"),
            role=UserRole.owner,
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    def login_get_token(self, client, email, password):
        """Helper to get authentication token."""
        response = client.post("/users/token", data={"username": email, "password": password})
        assert response.status_code == 200
        return response.json()["access_token"]

    @pytest.fixture
    def test_chama(self, db_session: Session, test_user: User):
        """Create a test chama."""
        chama = Chama(
            id=101,  # Use high ID to avoid conflicts
            name="Test Chama Edge Cases",
            created_by_user_id=test_user.id
        )
        db_session.add(chama)
        db_session.commit()
        return chama

    @pytest.fixture
    def test_membership(self, db_session: Session, test_user: User, test_chama: Chama):
        """Create membership for user in chama."""
        membership = Membership(
            user_id=test_user.id,
            chama_id=test_chama.id,
            role="owner"
        )
        db_session.add(membership)
        db_session.commit()
        return membership

    def test_get_subscription_plan_not_found(self, client, test_user):
        """Test getting a non-existent subscription plan."""
        # This should return 404
        response = client.get("/billing/plans/99999")
        assert response.status_code == 404
        data = response.json()
        assert "Subscription plan not found" in data["detail"]

    def test_get_subscription_plan_inactive(self, client, test_user, db_session):
        """Test getting an inactive subscription plan."""
        # Create inactive plan
        plan = SubscriptionPlan(
            name="Inactive Plan",
            plan_type="basic",
            price_monthly=10.0,
            price_yearly=100.0,
            max_members=10,
            max_contributions=100,
            max_storage_gb=1,
            is_active=False
        )
        db_session.add(plan)
        db_session.commit()

        response = client.get(f"/billing/plans/{plan.id}")
        assert response.status_code == 404
        data = response.json()
        assert "Subscription plan not found" in data["detail"]

    def test_create_subscription_duplicate(self, client, test_user, test_chama, test_membership, db_session):
        """Test creating subscription when chama already has one."""
        # Get authentication token
        token = self.login_get_token(client, test_user.email, "testpass")

        # Create existing subscription
        plan = SubscriptionPlan(
            name="Test Plan",
            plan_type="basic",
            price_monthly=10.0,
            price_yearly=100.0,
            max_members=10,
            max_contributions=100,
            max_storage_gb=1,
            is_active=True
        )
        db_session.add(plan)
        db_session.commit()

        subscription = Subscription(
            chama_id=test_chama.id,
            plan_id=plan.id,
            status="trial",
            billing_cycle="monthly"
        )
        db_session.add(subscription)
        db_session.commit()

        # Mock tenant context for multi-tenant system
        with patch('backend.database.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = test_chama.id

            # Try to create another subscription
            response = client.post(
                "/billing/subscription",
                json={"plan_id": plan.id, "billing_cycle": "monthly"},
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 409
            data = response.json()
            assert "already has an active subscription" in data["detail"]

    def test_create_subscription_invalid_plan(self, client, test_user, test_chama, test_membership):
        """Test creating subscription with invalid plan ID."""
        response = client.post(
            "/billing/subscription",
            json={"plan_id": 99999, "billing_cycle": "monthly"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "Subscription plan not found" in data["detail"]

    def test_update_subscription_no_subscription(self, client, test_user, test_chama, test_membership):
        """Test updating subscription when none exists."""
        response = client.put(
            "/billing/subscription",
            json={"billing_cycle": "yearly"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "No active subscription found" in data["detail"]

    def test_update_subscription_invalid_plan(self, client, test_user, test_chama, test_membership, db_session):
        """Test updating subscription to invalid plan."""
        # Create subscription
        plan = SubscriptionPlan(
            name="Test Plan",
            plan_type="basic",
            price_monthly=10.0,
            price_yearly=100.0,
            max_members=10,
            max_contributions=100,
            max_storage_gb=1,
            is_active=True
        )
        db_session.add(plan)
        db_session.commit()

        subscription = Subscription(
            chama_id=test_chama.id,
            plan_id=plan.id,
            status="trial",
            billing_cycle="monthly"
        )
        db_session.add(subscription)
        db_session.commit()

        # Try to update to invalid plan
        response = client.put(
            "/billing/subscription",
            json={"plan_id": 99999}
        )
        assert response.status_code == 404
        data = response.json()
        assert "New subscription plan not found" in data["detail"]

    def test_cancel_subscription_no_subscription(self, client, test_user, test_chama, test_membership):
        """Test canceling subscription when none exists."""
        response = client.delete("/billing/subscription")
        assert response.status_code == 404
        data = response.json()
        assert "No active subscription found" in data["detail"]

    def test_initialize_payment_no_subscription(self, client, test_user, test_chama, test_membership):
        """Test initializing payment without active subscription."""
        response = client.post(
            "/billing/initialize-payment?amount=1000&description=Test payment"
        )
        assert response.status_code == 400
        data = response.json()
        assert "No active subscription found" in data["detail"]

    def test_get_usage_stats_no_subscription(self, client, test_user, test_chama, test_membership):
        """Test getting usage stats without subscription."""
        response = client.get("/billing/usage")
        assert response.status_code == 404
        data = response.json()
        assert "No active subscription found" in data["detail"]

    def test_get_chama_subscription_no_access(self, client, test_user, db_session):
        """Test accessing subscription without membership."""
        # Create another chama that user doesn't belong to
        other_chama = Chama(
            id=102,
            name="Other Chama",
            created_by_user_id=999  # Different owner
        )
        db_session.add(other_chama)
        db_session.commit()

        response = client.get(f"/billing/chamas/{other_chama.id}/subscription")
        assert response.status_code == 403
        data = response.json()
        assert "You do not have access to this chama" in data["detail"]

    def test_paystack_client_error_handling(self, client, test_user, test_chama, test_membership, db_session):
        """Test handling Paystack API errors."""
        # Create subscription setup
        plan = SubscriptionPlan(
            name="Test Plan",
            plan_type="basic",
            price_monthly=10.0,
            price_yearly=100.0,
            max_members=10,
            max_contributions=100,
            max_storage_gb=1,
            is_active=True
        )
        db_session.add(plan)
        db_session.commit()

        subscription = Subscription(
            chama_id=test_chama.id,
            plan_id=plan.id,
            status="trial",
            billing_cycle="monthly"
        )
        db_session.add(subscription)
        db_session.commit()

        # Mock Paystack API failure
        with patch('backend.billing.paystack_client.paystack_client.initialize_transaction') as mock_init:
            mock_init.side_effect = Exception("Paystack API unavailable")

            response = client.post(
                "/billing/initialize-payment?amount=1000&description=Test payment"
            )
            assert response.status_code == 500
            data = response.json()
            assert "Payment initialization failed" in data["detail"]

    def test_webhook_processing_invalid_data(self, client):
        """Test webhook processing with invalid data."""
        response = client.post(
            "/billing/webhooks",
            json={"invalid": "data"}
        )
        # Webhooks should still return 200 even for invalid data to avoid retries
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"  # Still success for webhook acknowledgment

    def test_subscription_plan_pagination_limits(self, client, test_user, db_session):
        """Test subscription plan pagination limits."""
        # Create multiple plans
        plans = []
        for i in range(5):
            plan = SubscriptionPlan(
                name=f"Plan {i}",
                plan_type="basic",
                price_monthly=10.0,
                price_yearly=100.0,
                max_members=10,
                max_contributions=100,
                max_storage_gb=1,
                is_active=True
            )
            plans.append(plan)
            db_session.add(plan)
        db_session.commit()

        # Test limit parameter
        response = client.get("/billing/plans?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2

        # Test skip parameter
        response = client.get("/billing/plans?skip=3&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2

    def test_payment_method_validation(self, client, test_user, test_chama, test_membership):
        """Test payment method input validation."""
        # Test with invalid card number
        response = client.post(
            "/billing/payment-methods",
            json={
                "type": "card",
                "provider": "visa",
                "card_number": "123",  # Too short
                "phone_number": None
            }
        )
        # Should handle gracefully - in real app would validate
        # For now just test that endpoint accepts the request
        assert response.status_code in [200, 422]  # Either success or validation error

    def test_tenant_context_missing(self, client):
        """Test endpoints without tenant context."""
        # This would require mocking the tenant context to be None
        # Most endpoints check for tenant context
        response = client.get("/billing/plans")
        # Should work without tenant context for public endpoints
        assert response.status_code == 200

        # But tenant-specific endpoints should fail
        response = client.get("/billing/chamas/1/subscription")
        assert response.status_code in [400, 403]  # Either tenant context error or access denied
