"""
Unit tests for billing and subscription functionality.
Tests Paystack client, billing models, and business logic.
"""
import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal

from backend.billing.paystack_client import PaystackClient


class TestPaystackClient:
    """Test Paystack API client functionality."""

    @pytest.fixture
    def paystack_client(self):
        """Create PaystackClient instance with test mode enabled."""
        with patch.dict('os.environ', {
            'PAYSTACK_SECRET_KEY': 'sk_test_default_for_ci_cd',
            'PAYSTACK_PUBLIC_KEY': 'pk_test_default_for_ci_cd'
        }):
            client = PaystackClient()
            assert client.is_test_mode is True
            return client

    def test_client_initialization_test_mode(self, paystack_client):
        """Test client initializes properly in test mode."""
        assert paystack_client.is_test_mode is True
        assert paystack_client.secret_key == 'sk_test_default_for_ci_cd'
        assert paystack_client.public_key == 'pk_test_default_for_ci_cd'

    def test_client_initialization_production_mode(self):
        """Test client initializes properly in production mode."""
        with patch.dict('os.environ', {
            'PAYSTACK_SECRET_KEY': 'sk_live_1234567890',
            'PAYSTACK_PUBLIC_KEY': 'pk_live_abcd1234'
        }):
            client = PaystackClient()
            assert client.is_test_mode is False  # Live keys should not be test mode

    @pytest.mark.asyncio
    @patch('backend.billing.paystack_client.PaystackClient._make_request')
    async def test_create_customer(self, mock_request, paystack_client):
        """Test creating a Paystack customer."""
        mock_request.return_value = {
            "status": True,
            "data": {
                "id": "customer_test_123",
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User"
            }
        }

        result = await paystack_client.create_customer(
            email="test@example.com",
            first_name="Test",
            last_name="User"
        )

        assert result["id"] == "customer_test_123"
        assert result["email"] == "test@example.com"
        mock_request.assert_called_once()

    @pytest.mark.asyncio
    @patch('backend.billing.paystack_client.PaystackClient._make_request')
    async def test_create_plan_kes_currency(self, mock_request, paystack_client):
        """Test creating a subscription plan in KES."""
        mock_request.return_value = {
            "status": True,
            "data": {
                "id": "plan_test_123",
                "name": "Basic Plan",
                "amount": 100000,  # ₸100.00
                "currency": "KES",
                "interval": "monthly"
            }
        }

        result = await paystack_client.create_plan(
            name="Basic Plan",
            amount=100000,  # ₸100.00 = 1000 kobo
            interval="monthly",
            currency="KES"
        )

        assert result["currency"] == "KES"
        assert result["amount"] == 100000
        mock_request.assert_called_once()

    @pytest.mark.asyncio
    @patch('backend.billing.paystack_client.PaystackClient._make_request')
    async def test_initialize_transaction_kes(self, mock_request, paystack_client):
        """Test initializing payment transaction in KES."""
        mock_request.return_value = {
            "status": True,
            "data": {
                "reference": "ref_test_123",
                "url": "https://paystack.com/pay/ref_test_123",
                "amount": 50000,  # ₸50.00
                "currency": "KES"
            }
        }

        result = await paystack_client.initialize_transaction(
            email="user@example.com",
            amount=50000,  # ₸50.00
            currency="KES",
            callback_url="https://app.example.com/callback"
        )

        assert result["currency"] == "KES"
        assert result["amount"] == 50000
        assert "callback_url" in result  # Should be included in URL
        mock_request.assert_called_once()

    @pytest.mark.asyncio
    @patch('backend.billing.paystack_client.PaystackClient._make_request')
    async def test_verify_transaction(self, mock_request, paystack_client):
        """Test verifying transaction status."""
        mock_request.return_value = {
            "status": True,
            "data": {
                "reference": "ref_test_123",
                "status": "success",
                "amount": 50000,
                "currency": "KES"
            }
        }

        result = await paystack_client.verify_transaction("ref_test_123")

        assert result["status"] == "success"
        assert result["reference"] == "ref_test_123"
        mock_request.assert_called_once_with("GET", "/transaction/verify/ref_test_123")

    def test_webhook_signature_verification_valid(self, paystack_client):
        """Test webhook signature verification with valid signature."""
        payload = b'{"event": "charge.success"}'
        secret = "webhook_secret_123"

        # Generate a mock signature (simplified)
        import hmac
        import hashlib
        signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()

        is_valid = paystack_client.verify_webhook_signature(payload, signature, secret)
        assert is_valid is True

    def test_webhook_signature_verification_invalid(self, paystack_client):
        """Test webhook signature verification with invalid signature."""
        payload = b'{"event": "charge.success"}'
        secret = "webhook_secret_123"
        invalid_signature = "invalid_signature"

        is_valid = paystack_client.verify_webhook_signature(payload, invalid_signature, secret)
        assert is_valid is False

    @pytest.mark.asyncio
    @patch('backend.billing.paystack_client.PaystackClient._handle_invoice_created')
    async def test_process_webhook_invoice_create(self, mock_handler, paystack_client):
        """Test processing invoice.create webhook event."""
        event_data = {
            "event": "invoice.create",
            "data": {"id": "invoice_123", "status": "pending"}
        }

        result = await paystack_client.process_webhook_event(event_data)

        assert result == "invoice.create"
        mock_handler.assert_called_once_with(event_data["data"])

    @pytest.mark.asyncio
    async def test_process_webhook_unknown_event(self, paystack_client):
        """Test processing unknown webhook event."""
        event_data = {
            "event": "unknown.event",
            "data": {"id": "unknown_123"}
        }

        result = await paystack_client.process_webhook_event(event_data)

        assert result == "unknown.event"


class TestBillingModels:
    """Test billing data models and relationships."""

    def test_subscription_plan_creation(self):
        """Test creating a subscription plan with proper validations."""
        from backend.models.subscription import SubscriptionPlan
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        # Create in-memory SQLite DB for testing
        engine = create_engine("sqlite:///:memory:")
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        # Create tables
        SubscriptionPlan.__table__.create(bind=engine)

        # Test creating a plan
        plan = SubscriptionPlan(
            name="Basic Plan",
            plan_type="basic",
            description="Basic chama plan",
            price_monthly=9.99,
            price_yearly=99.99,
            max_members=50,
            max_contributions=1000,
            max_storage_gb=1,
            priority_support=False,
            is_active=True
        )

        session.add(plan)
        session.commit()

        # Verify plan was created
        db_plan = session.query(SubscriptionPlan).filter_by(name="Basic Plan").first()
        assert db_plan is not None
        assert db_plan.plan_type.value == "basic"
        assert db_plan.price_monthly == 9.99
        assert db_plan.max_members == 50

        session.close()

    def test_subscription_creation(self):
        """Test creating a subscription with proper relationships."""
        from backend.models.subscription import Subscription, SubscriptionPlan
        from backend.models.chama import Chama
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        # Create in-memory SQLite DB
        engine = create_engine("sqlite:///:memory:")
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        # Create tables (simplified, without cross-schema complexity)
        SubscriptionPlan.__table__.create(bind=engine)
        Subscription.__table__.create(bind=engine)
        Chama.__table__.create(bind=engine)

        # Create test data
        chama = Chama(id=1, name="Test Chama", owner_id=1)
        plan = SubscriptionPlan(
            id=1, name="Basic Plan", plan_type="basic",
            price_monthly=9.99, price_yearly=99.99,
            max_members=50, max_contributions=1000, max_storage_gb=1
        )

        session.add(chama)
        session.add(plan)
        session.commit()

        # Create subscription
        subscription = Subscription(
            chama_id=chama.id,
            plan_id=plan.id,
            status="trial",
            billing_cycle="monthly",
            stripe_customer_id="cus_test_123"
        )

        session.add(subscription)
        session.commit()

        # Verify subscription
        db_subscription = session.query(Subscription).first()
        assert db_subscription is not None
        assert db_subscription.status.value == "trial"
        assert db_subscription.billing_cycle.value == "monthly"

        # Verify relationship
        assert db_subscription.chama_id == chama.id
        assert db_subscription.plan_id == plan.id

        session.close()
