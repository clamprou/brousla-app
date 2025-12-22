"""Stripe integration for subscription management."""
import os
import logging
from typing import Optional, Tuple
import stripe
from app.config import settings
from app.database import update_user_subscription, get_user_by_id, get_user_by_stripe_subscription_id
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.stripe_secret_key or os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = settings.stripe_webhook_secret or os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Plan price IDs - these should be set in environment variables or config
STRIPE_BASIC_PRICE_ID = settings.stripe_basic_price_id or os.getenv("STRIPE_BASIC_PRICE_ID", "")
STRIPE_PLUS_PRICE_ID = settings.stripe_plus_price_id or os.getenv("STRIPE_PLUS_PRICE_ID", "")
STRIPE_PRO_PRICE_ID = settings.stripe_pro_price_id or os.getenv("STRIPE_PRO_PRICE_ID", "")


def create_checkout_session(user_id: str, user_email: str, plan: str) -> Tuple[str, str]:
    """
    Create a Stripe checkout session for subscription.
    
    Args:
        user_id: User ID
        user_email: User email
        plan: Subscription plan ('basic', 'plus', or 'pro')
    
    Returns:
        (checkout_url, session_id)
    """
    if not stripe.api_key:
        raise ValueError("STRIPE_SECRET_KEY not configured")
    
    if plan == "basic":
        price_id = STRIPE_BASIC_PRICE_ID
    elif plan == "plus":
        price_id = STRIPE_PLUS_PRICE_ID
    elif plan == "pro":
        price_id = STRIPE_PRO_PRICE_ID
    else:
        raise ValueError(f"Invalid plan: {plan}")
    
    if not price_id:
        raise ValueError(f"Stripe price ID not configured for plan: {plan}")
    
    # Get app base URL for success/cancel URLs
    app_base_url = getattr(settings, "app_base_url", "http://localhost:5173")
    
    try:
        session = stripe.checkout.Session.create(
            customer_email=user_email,
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=f"{app_base_url}/profile?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{app_base_url}/profile?cancelled=true",
            metadata={
                "user_id": user_id,
                "plan": plan,
                "price_id": price_id
            },
            subscription_data={
                "metadata": {
                    "user_id": user_id,
                    "plan": plan,
                    "price_id": price_id
                }
            }
        )
        
        return session.url, session.id
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {e}")
        raise Exception(f"Failed to create checkout session: {str(e)}")


def handle_stripe_webhook(payload: bytes, sig_header: str) -> bool:
    """
    Handle Stripe webhook events.
    
    Args:
        payload: Raw webhook payload
        sig_header: Stripe signature header
    
    Returns:
        True if event was handled, False if ignored
    """
    if not STRIPE_WEBHOOK_SECRET:
        logger.warning("STRIPE_WEBHOOK_SECRET not configured, skipping webhook verification")
        return False
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return False
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return False
    
    # Handle the event
    event_type = event["type"]
    data = event["data"]["object"]
    
    logger.info(f"Received Stripe webhook: {event_type}")
    
    if event_type == "checkout.session.completed":
        # Subscription was created
        session = data
        metadata = session.get("metadata", {})
        user_id = metadata.get("user_id")
        plan = metadata.get("plan")
        price_id = metadata.get("price_id")  # Read price_id from session metadata
        subscription_id = session.get("subscription")
        
        if not user_id or not subscription_id:
            logger.warning(f"checkout.session.completed missing required fields: user_id={user_id}, subscription_id={subscription_id}")
            return False
        
        # Get subscription details
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            customer_id = subscription.customer
        except Exception as e:
            logger.error(f"Error retrieving subscription {subscription_id}: {e}")
            return False
        
        # Get plan from price metadata
        plan_from_metadata = plan
        
        # Use price_id from session metadata if available, otherwise get from subscription
        if not price_id and subscription.get("items") and len(subscription["items"]["data"]) > 0:
            price_id = subscription["items"]["data"][0].get("price", {}).get("id")
        
        if price_id:
            try:
                price = stripe.Price.retrieve(price_id)
                price_metadata = price.get("metadata", {})
                # Get plan from price metadata
                plan_from_metadata = price_metadata.get("plan", plan)
            except stripe.error.StripeError as e:
                logger.error(f"Error retrieving price {price_id}: {e}")
        
        # Calculate dates (optional metadata - don't block update if unavailable)
        current_period_start = None
        current_period_end = None
        cancel_at_period_end = False
        
        # Try to access current_period_start/end - Stripe Python SDK objects support attribute access
        try:
            current_period_start = datetime.fromtimestamp(subscription.current_period_start)
            current_period_end = datetime.fromtimestamp(subscription.current_period_end)
            cancel_at_period_end = subscription.cancel_at_period_end or False
        except (AttributeError, KeyError) as e:
            # Fallback: try to get from items period
            try:
                if subscription.items and len(subscription.items.data) > 0:
                    item = subscription.items.data[0]
                    if hasattr(item, 'period') and item.period:
                        current_period_start = datetime.fromtimestamp(item.period.start)
                        current_period_end = datetime.fromtimestamp(item.period.end)
            except Exception as fallback_error:
                logger.warning(f"Could not retrieve subscription dates for {subscription_id}: {e}, fallback also failed: {fallback_error}. Continuing without dates.")
        
        # Update user subscription with metadata from Stripe
        # Dates are optional - never block update if dates are unavailable
        try:
            update_user_subscription(
                user_id=user_id,
                plan=plan_from_metadata,
                status="active",
                stripe_subscription_id=subscription_id,
                stripe_price_id=price_id,
                current_period_start=current_period_start.isoformat() if current_period_start else None,
                current_period_end=current_period_end.isoformat() if current_period_end else None,
                cancel_at_period_end=cancel_at_period_end
            )
            logger.info(f"Updated subscription for user {user_id}: {plan_from_metadata}, price_id: {price_id}")
        except Exception as e:
            logger.error(f"Error updating subscription for user {user_id}: {e}")
            return False
        
        return True
    
    elif event_type == "customer.subscription.updated":
        # Subscription was updated (e.g., plan change, renewal)
        subscription = data
        subscription_id = subscription["id"]
        customer_id = subscription["customer"]
        
        # Try to find user by subscription ID first
        user = get_user_by_stripe_subscription_id(subscription_id)
        
        if not user:
            # Fall back to metadata
            metadata = subscription.get("metadata", {})
            user_id = metadata.get("user_id")
            if not user_id:
                logger.warning(f"Could not find user for subscription {subscription_id}")
                return False
        else:
            user_id = user["id"]
        
        # Get plan from price metadata
        plan = None
        price_id = None
        
        if subscription.get("items") and len(subscription["items"]["data"]) > 0:
            price_id = subscription["items"]["data"][0].get("price", {}).get("id")
            if price_id:
                try:
                    price = stripe.Price.retrieve(price_id)
                    price_metadata = price.get("metadata", {})
                    # Get plan from price metadata
                    plan = price_metadata.get("plan")
                except stripe.error.StripeError as e:
                    logger.error(f"Error retrieving price {price_id}: {e}")
        
        # Fallback to subscription metadata or existing user data if price metadata not available
        if not plan:
            metadata = subscription.get("metadata", {})
            plan = metadata.get("plan") or (user.get("subscription_plan") if user else None)
        
        status = subscription["status"]
        
        # Map Stripe status to our status
        if status in ["active", "trialing"]:
            our_status = "active"
        elif status in ["canceled", "unpaid", "past_due"]:
            our_status = "cancelled"
        else:
            our_status = "expired"
        
        # Calculate dates
        current_period_start = datetime.fromtimestamp(subscription["current_period_start"])
        current_period_end = datetime.fromtimestamp(subscription["current_period_end"])
        cancel_at_period_end = subscription.get("cancel_at_period_end", False)
        
        # Update user subscription with metadata from Stripe
        update_user_subscription(
            user_id=user_id,
            plan=plan,
            status=our_status,
            stripe_subscription_id=subscription_id,
            stripe_price_id=price_id,
            current_period_start=current_period_start.isoformat(),
            current_period_end=current_period_end.isoformat(),
            cancel_at_period_end=cancel_at_period_end
        )
        logger.info(f"Updated subscription for user {user_id}: {plan}, status: {our_status}, price_id: {price_id}")
        return True
    
    elif event_type == "customer.subscription.deleted":
        # Subscription was cancelled
        subscription = data
        subscription_id = subscription["id"]
        
        # Try to find user by subscription ID
        user = get_user_by_stripe_subscription_id(subscription_id)
        
        if not user:
            # Fall back to metadata
            metadata = subscription.get("metadata", {})
            user_id = metadata.get("user_id")
            if not user_id:
                logger.warning(f"Could not find user for cancelled subscription {subscription_id}")
                return False
        else:
            user_id = user["id"]
        
        # Set subscription to cancelled
        update_user_subscription(
            user_id=user_id,
            status="cancelled"
        )
        logger.info(f"Cancelled subscription for user {user_id}")
        return True
    
    elif event_type == "invoice.paid":
        # Recurring payment was successful
        invoice = data
        subscription_id = invoice.get("subscription")
        
        if not subscription_id:
            logger.warning("invoice.paid event missing subscription_id")
            return False
        
        # Try to find user by subscription ID
        user = get_user_by_stripe_subscription_id(subscription_id)
        
        if not user:
            logger.warning(f"Could not find user for subscription {subscription_id} in invoice.paid event")
            return False
        
        user_id = user["id"]
        
        # Retrieve subscription to get current period end
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            current_period_end = datetime.fromtimestamp(subscription.current_period_end)
            current_period_start = datetime.fromtimestamp(subscription.current_period_start)
            cancel_at_period_end = subscription.get("cancel_at_period_end", False)
            
            # Get price_id from subscription
            price_id = None
            if subscription.get("items") and len(subscription["items"]["data"]) > 0:
                price_id = subscription["items"]["data"][0].get("price", {}).get("id")
            
            # Update subscription (renewal)
            update_user_subscription(
                user_id=user_id,
                current_period_start=current_period_start.isoformat(),
                current_period_end=current_period_end.isoformat(),
                cancel_at_period_end=cancel_at_period_end,
                status="active",
                stripe_price_id=price_id
            )
            logger.info(f"Updated subscription renewal for user {user_id}, new period end: {current_period_end.isoformat()}")
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Error retrieving subscription {subscription_id} in invoice.paid handler: {e}")
            return False
    
    # Event not handled
    return False

