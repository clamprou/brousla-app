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

