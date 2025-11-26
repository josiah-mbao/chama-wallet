"""
Billing module for Paystack payment processing integration.
Handles subscription management, payment processing, and webhooks.
"""
from .paystack_client import PaystackClient

__all__ = ['PaystackClient']
