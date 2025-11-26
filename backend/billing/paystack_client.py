"""
Paystack API client for payment processing and subscription management.
"""
import os
import logging
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class PaystackClient:
    """Paystack API client for handling payments and subscriptions."""

    BASE_URL = "https://api.paystack.co"

    def __init__(self):
        """Initialize Paystack client with API keys."""
        self.secret_key = os.getenv("PAYSTACK_SECRET_KEY", "sk_test_default_for_ci_cd")
        self.public_key = os.getenv("PAYSTACK_PUBLIC_KEY", "pk_test_default_for_ci_cd")

        # Check if we're in test mode (default keys)
        self.is_test_mode = (self.secret_key == "sk_test_default_for_ci_cd" or
                           "test" in self.secret_key.lower())

        if not self.secret_key and not self.is_test_mode:
            raise ValueError("PAYSTACK_SECRET_KEY environment variable is required")

        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

        logger.info(f"PaystackClient initialized for billing operations (test_mode: {self.is_test_mode})")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Paystack API."""
        url = f"{self.BASE_URL}{endpoint}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data,
                    params=params
                )

                response.raise_for_status()
                result = response.json()

                if result.get("status"):
                    return result
                else:
                    logger.error(f"Paystack API error: {result}")
                    raise ValueError(f"Paystack API error: {result.get('message', 'Unknown error')}")

            except httpx.HTTPError as e:
                logger.error(f"HTTP error with Paystack API: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise

    # ============ CUSTOMER MANAGEMENT ============

    async def create_customer(
        self,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a new customer in Paystack.

        Args:
            email: Customer email address
            first_name: Customer first name
            last_name: Customer last name
            phone: Customer phone number
            metadata: Additional metadata

        Returns:
            Paystack customer object
        """
        data = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
        }

        if metadata:
            data["metadata"] = json.dumps(metadata)

        logger.info(f"Creating Paystack customer for email: {email}")
        response = await self._make_request("POST", "/customer", data)
        return response["data"]

    async def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """
        Retrieve customer details from Paystack.

        Args:
            customer_id: Paystack customer ID

        Returns:
            Paystack customer object
        """
        logger.info(f"Retrieving Paystack customer: {customer_id}")
        response = await self._make_request("GET", f"/customer/{customer_id}")
        return response["data"]

    async def update_customer(
        self,
        customer_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update customer information in Paystack.

        Args:
            customer_id: Paystack customer ID
            updates: Fields to update

        Returns:
            Updated Paystack customer object
        """
        data = {}
        if "first_name" in updates:
            data["first_name"] = updates["first_name"]
        if "last_name" in updates:
            data["last_name"] = updates["last_name"]
        if "phone" in updates:
            data["phone"] = updates["phone"]
        if "metadata" in updates:
            data["metadata"] = json.dumps(updates["metadata"])

        logger.info(f"Updating Paystack customer: {customer_id}")
        response = await self._make_request("PUT", f"/customer/{customer_id}", data)
        return response["data"]

    # ============ PLAN MANAGEMENT ============

    async def create_plan(
        self,
        name: str,
        amount: int,  # Amount in kobo (KES) - e.g., 1000 = ₸10.00
        interval: str,  # "monthly", "yearly"
        description: Optional[str] = None,
        currency: str = "KES"
    ) -> Dict[str, Any]:
        """
        Create a subscription plan in Paystack.

        Args:
            name: Plan name
            amount: Amount in kobo (smallest currency unit)
            interval: "monthly" or "yearly"
            description: Plan description
            currency: Currency code

        Returns:
            Paystack plan object
        """
        data = {
            "name": name,
            "amount": amount,
            "interval": interval,
            "currency": currency,
        }

        if description:
            data["description"] = description

        logger.info(f"Creating Paystack plan: {name} ({amount} kobo {interval})")
        response = await self._make_request("POST", "/plan", data)
        return response["data"]

    async def get_plan(self, plan_id: str) -> Dict[str, Any]:
        """
        Retrieve plan details from Paystack.

        Args:
            plan_id: Paystack plan ID

        Returns:
            Paystack plan object
        """
        logger.info(f"Retrieving Paystack plan: {plan_id}")
        response = await self._make_request("GET", f"/plan/{plan_id}")
        return response["data"]

    async def list_plans(
        self,
        per_page: int = 50,
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """
        List all subscription plans.

        Args:
            per_page: Number of plans per page
            page: Page number

        Returns:
            List of Paystack plan objects
        """
        params = {"perPage": per_page, "page": page}
        response = await self._make_request("GET", "/plan", params=params)
        return response["data"]

    # ============ SUBSCRIPTION MANAGEMENT ============

    async def create_subscription(
        self,
        customer_id: str,
        plan_id: str,
        start_date: Optional[str] = None  # ISO 8601 format
    ) -> Dict[str, Any]:
        """
        Create a subscription for a customer.

        Args:
            customer_id: Paystack customer ID
            plan_id: Paystack plan ID
            start_date: When subscription should start

        Returns:
            Paystack subscription object
        """
        data = {
            "customer": customer_id,
            "plan": plan_id,
        }

        if start_date:
            data["start_date"] = start_date

        logger.info(f"Creating subscription for customer {customer_id} on plan {plan_id}")
        response = await self._make_request("POST", "/subscription", data)
        return response["data"]

    async def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Retrieve subscription details from Paystack.

        Args:
            subscription_id: Paystack subscription ID

        Returns:
            Paystack subscription object
        """
        logger.info(f"Retrieving subscription: {subscription_id}")
        response = await self._make_request("GET", f"/subscription/{subscription_id}")
        return response["data"]

    async def cancel_subscription(self, subscription_code: str, token: str) -> Dict[str, Any]:
        """
        Cancel a customer's subscription.

        Args:
            subscription_code: Paystack subscription code
            token: Subscription token from customer

        Returns:
            Paystack cancellation response
        """
        data = {"token": token}
        logger.info(f"Cancelling subscription: {subscription_code}")
        response = await self._make_request("POST", f"/subscription/{subscription_code}/cancel", data)
        return response["data"]

    async def enable_subscription(self, subscription_code: str) -> Dict[str, Any]:
        """
        Re-enable a cancelled subscription.

        Args:
            subscription_code: Paystack subscription code

        Returns:
            Paystack subscription object
        """
        logger.info(f"Re-enabling subscription: {subscription_code}")
        response = await self._make_request("POST", f"/subscription/{subscription_code}/enable")
        return response["data"]

    # ============ PAYMENT PROCESSING ============

    async def initialize_transaction(
        self,
        email: str,
        amount: int,  # Amount in kobo
        currency: str = "KES",
        callback_url: Optional[str] = None,
        reference: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Initialize a transaction for payment.

        Args:
            email: Customer email
            amount: Amount in kobo
            currency: Currency code
            callback_url: Callback URL after payment
            reference: Unique reference for transaction
            metadata: Additional data

        Returns:
            Paystack transaction initialization response
        """
        data = {
            "email": email,
            "amount": amount,
            "currency": currency,
        }

        if callback_url:
            data["callback_url"] = callback_url
        if reference:
            data["reference"] = reference
        if metadata:
            data["metadata"] = json.dumps(metadata)

        logger.info(f"Initializing transaction for {email}: {amount} kobo {currency}")
        response = await self._make_request("POST", "/transaction/initialize", data)
        return response["data"]

    async def verify_transaction(self, reference: str) -> Dict[str, Any]:
        """
        Verify a transaction status.

        Args:
            reference: Transaction reference

        Returns:
            Paystack transaction verification response
        """
        logger.info(f"Verifying transaction: {reference}")
        response = await self._make_request("GET", f"/transaction/verify/{reference}")
        return response["data"]

    async def list_transactions(
        self,
        reference: Optional[str] = None,
        per_page: int = 50,
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """
        List transactions with optional filtering.

        Args:
            reference: Transaction reference to filter by
            per_page: Number of transactions per page
            page: Page number

        Returns:
            List of Paystack transaction objects
        """
        params = {"perPage": per_page, "page": page}
        if reference:
            params["reference"] = reference

        response = await self._make_request("GET", "/transaction", params=params)
        return response["data"]

    # ============ CHARGE MANAGEMENT ============

    async def charge_customer(
        self,
        email: str,
        amount: int,  # Amount in kobo
        authorization_code: str,
        currency: str = "KES",
        reference: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Charge a customer with saved authorization.

        Args:
            email: Customer email
            amount: Amount in kobo
            authorization_code: Saved authorization code
            currency: Currency code
            reference: Transaction reference

        Returns:
            Paystack charge response
        """
        data = {
            "email": email,
            "amount": amount,
            "authorization_code": authorization_code,
            "currency": currency,
        }

        if reference:
            data["reference"] = reference

        logger.info(f"Charging customer {email}: {amount} kobo")
        response = await self._make_request("POST", "/charge", data)
        return response["data"]

    # ============ WEBHOOK HANDLING ============

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """
        Verify webhook signature (for production use).

        Args:
            payload: Raw webhook payload
            signature: X-Paystack-Signature header
            secret: Webhook secret

        Returns:
            True if signature is valid
        """
        import hmac
        import hashlib

        computed_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()

        return hmac.compare_digest(computed_signature, signature)

    async def process_webhook_event(self, event_data: Dict[str, Any]) -> str:
        """
        Process incoming webhook events.

        Args:
            event_data: Parsed webhook payload

        Returns:
            Event type that was processed
        """
        event_type = event_data.get("event")

        if event_type == "invoice.create":
            await self._handle_invoice_created(event_data["data"])
        elif event_type == "invoice.update":
            await self._handle_invoice_updated(event_data["data"])
        elif event_type == "charge.success":
            await self._handle_charge_success(event_data["data"])
        elif event_type == "subscription.create":
            await self._handle_subscription_created(event_data["data"])
        elif event_type == "subscription.disable":
            await self._handle_subscription_cancelled(event_data["data"])
        else:
            logger.warning(f"Unhandled webhook event: {event_type}")

        return event_type

    # Webhook event handlers (to be implemented)
    async def _handle_invoice_created(self, data: Dict[str, Any]):
        """Handle invoice creation webhook."""
        logger.info(f"Invoice created: {data.get('id')}")

    async def _handle_invoice_updated(self, data: Dict[str, Any]):
        """Handle invoice update webhook."""
        logger.info(f"Invoice updated: {data.get('id')} - {data.get('status')}")

    async def _handle_charge_success(self, data: Dict[str, Any]):
        """Handle successful charge webhook."""
        logger.info(f"Charge successful: {data.get('reference')} - {data.get('amount')}")

    async def _handle_subscription_created(self, data: Dict[str, Any]):
        """Handle subscription creation webhook."""
        logger.info(f"Subscription created: {data.get('id')}")

    async def _handle_subscription_cancelled(self, data: Dict[str, Any]):
        """Handle subscription cancellation webhook."""
        logger.info(f"Subscription cancelled: {data.get('id')}")


# Global client instance
paystack_client = PaystackClient()
