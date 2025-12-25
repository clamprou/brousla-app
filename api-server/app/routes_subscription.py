"""Subscription management routes."""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from app.auth import get_current_user
from app.database import (
    get_user_subscription,
    increment_user_execution_count,
    check_user_can_execute,
    update_user_subscription
)
import os
from app.subscription import get_subscription_status
from app.stripe_service import create_checkout_session, handle_stripe_webhook
import stripe
from app.models import MessageResponse
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/subscription", tags=["subscription"])


@router.get("/status")
async def get_status(current_user: dict = Depends(get_current_user)):
    """Get current subscription status for the authenticated user."""
    user_id = current_user["id"]
    status_info = get_subscription_status(user_id)
    return status_info


@router.post("/check-execution")
async def check_execution(current_user: dict = Depends(get_current_user)):
    """
    Check if user can execute a workflow.
    Called before workflow execution.
    
    Returns:
        { "can_execute": bool, "message": str }
    """
    user_id = current_user["id"]
    can_execute, message = check_user_can_execute(user_id)
    
    return {
        "can_execute": can_execute,
        "message": message
    }


@router.post("/increment-execution")
async def increment_execution(current_user: dict = Depends(get_current_user)):
    """
    Increment execution count for user.
    Called after successful workflow execution.
    
    Returns:
        { "success": bool, "message": str }
    """
    user_id = current_user["id"]
    
    # Check if user can execute before incrementing
    can_execute, message = check_user_can_execute(user_id)
    if not can_execute:
        return {
            "success": False,
            "message": message
        }
    
    # Increment execution count
    increment_user_execution_count(user_id)
    
    # Get updated status
    status_info = get_subscription_status(user_id)
    
    return {
        "success": True,
        "message": "Execution count incremented",
        "subscription_status": status_info
    }


@router.post("/create-checkout")
async def create_checkout(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Create Stripe checkout session for subscription.
    If user has an existing subscription, it will be completely cancelled first.
    
    Request body: { "plan": "basic" | "plus" | "pro" }
    
    Returns:
        { "checkout_url": str, "session_id": str }
    """
    body = await request.json()
    plan = body.get("plan")
    
    if plan not in ["basic", "plus", "pro"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid plan. Must be 'basic', 'plus', or 'pro'"
        )
    
    user_id = current_user["id"]
    user_email = current_user["email"]
    
    try:
        checkout_url, session_id = create_checkout_session(
            user_id=user_id,
            user_email=user_email,
            plan=plan
        )
        
        return {
            "checkout_url": checkout_url,
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout session: {str(e)}"
        )


@router.post("/check-execution-internal")
async def check_execution_internal(request: Request, user_id: str = Body(..., embed=True)):
    """
    Internal endpoint to check if user can execute a workflow.
    Called by workflow server. Accepts user_id directly.
    Only accessible from localhost.
    """
    # Check if request is from localhost (for security)
    client_host = request.client.host if request.client else None
    if client_host not in ["127.0.0.1", "localhost", "::1"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only accessible from localhost"
        )
    
    can_execute, message = check_user_can_execute(user_id)
    
    return {
        "can_execute": can_execute,
        "message": message
    }


@router.post("/increment-execution-internal")
async def increment_execution_internal(request: Request, user_id: str = Body(..., embed=True)):
    """
    Internal endpoint to increment execution count.
    Called by workflow server after successful execution.
    Only accessible from localhost.
    """
    # Check if request is from localhost (for security)
    client_host = request.client.host if request.client else None
    if client_host not in ["127.0.0.1", "localhost", "::1"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only accessible from localhost"
        )
    
    # Check if user can execute before incrementing
    can_execute, message = check_user_can_execute(user_id)
    if not can_execute:
        return {
            "success": False,
            "message": message
        }
    
    # Increment execution count
    increment_user_execution_count(user_id)
    
    # Get updated status
    status_info = get_subscription_status(user_id)
    
    return {
        "success": True,
        "message": "Execution count incremented",
        "subscription_status": status_info
    }


@router.post("/cancel")
async def cancel_subscription(current_user: dict = Depends(get_current_user)):
    """
    Cancel the current user's subscription.
    Cancels the subscription in Stripe, which will trigger a webhook to update the database.
    
    Returns:
        { "success": bool, "message": str }
    """
    user_id = current_user["id"]
    
    # Get user's subscription to find Stripe subscription ID
    subscription_data = get_user_subscription(user_id)
    
    if not subscription_data or not subscription_data.get("stripe_subscription_id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    stripe_subscription_id = subscription_data["stripe_subscription_id"]
    
    try:
        from app.config import settings
        import os
        
        stripe.api_key = settings.stripe_secret_key or os.getenv("STRIPE_SECRET_KEY", "")
        
        if not stripe.api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stripe not configured"
            )
        
        # Cancel the subscription at period end (don't cancel immediately)
        subscription = stripe.Subscription.modify(
            stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        # Update database immediately (don't wait for webhook)
        update_user_subscription(
            user_id=user_id,
            cancel_at_period_end=True
        )
        
        logger.info(f"Cancelled subscription {stripe_subscription_id} for user {user_id} (at period end)")
        
        return {
            "success": True,
            "message": "Subscription will be cancelled at the end of the current billing period"
        }
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error cancelling subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel subscription: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel subscription: {str(e)}"
        )


@router.post("/cancel-completely")
async def cancel_subscription_completely(current_user: dict = Depends(get_current_user)):
    """
    Completely cancel the current user's subscription and restore trial status.
    This immediately cancels the subscription in Stripe, removes it from the database,
    and restores the user to trial status while preserving their trial usage count.
    
    Returns:
        { "success": bool, "message": str }
    """
    user_id = current_user["id"]
    
    # Get user's subscription to find Stripe subscription ID
    subscription_data = get_user_subscription(user_id)
    
    if not subscription_data or not subscription_data.get("stripe_subscription_id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    stripe_subscription_id = subscription_data["stripe_subscription_id"]
    
    try:
        from app.config import settings
        import os
        
        stripe.api_key = settings.stripe_secret_key or os.getenv("STRIPE_SECRET_KEY", "")
        
        if not stripe.api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stripe not configured"
            )
        
        # Cancel the subscription immediately (not at period end)
        try:
            subscription = stripe.Subscription.delete(stripe_subscription_id)
            logger.info(f"Immediately cancelled subscription {stripe_subscription_id} for user {user_id}")
        except stripe.error.StripeError as e:
            # If subscription is already cancelled, try to modify it first
            if "No such subscription" in str(e) or "already been deleted" in str(e):
                logger.info(f"Subscription {stripe_subscription_id} already deleted in Stripe")
            else:
                # Try to cancel at period end first, then delete
                try:
                    stripe.Subscription.modify(
                        stripe_subscription_id,
                        cancel_at_period_end=True
                    )
                    subscription = stripe.Subscription.delete(stripe_subscription_id)
                except Exception as e2:
                    logger.warning(f"Could not delete subscription {stripe_subscription_id}: {e2}")
                    # Continue anyway - we'll delete from our database
        
        # Delete subscription from database and reset monthly workflows
        from app.database import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Delete subscription
            cursor.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
            # Reset monthly workflows used (preserve trial workflows used)
            cursor.execute("""
                UPDATE usage 
                SET monthly_workflows_used = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()
        
        logger.info(f"Completely cancelled subscription for user {user_id}, restored to trial status")
        
        return {
            "success": True,
            "message": "Subscription cancelled completely. You have been restored to trial status."
        }
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error cancelling subscription completely: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel subscription: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error cancelling subscription completely: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel subscription: {str(e)}"
        )


@router.post("/webhook")
async def webhook(request: Request):
    """
    Handle Stripe webhook events.
    This endpoint receives events from Stripe about subscription changes.
    """
    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")
        
        if not sig_header:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing stripe-signature header"
            )
        
        # Handle webhook
        event_handled = handle_stripe_webhook(payload, sig_header)
        
        if event_handled:
            return {"status": "success"}
        else:
            return {"status": "ignored"}
            
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )

