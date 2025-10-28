import pytest
from unittest.mock import patch, MagicMock
from app.models import User, Subscription, Plan


def test_webhook_subscription_created(client, db):
    """Test webhook handling for subscription.created event"""
    # Create user with Stripe customer ID
    user = User(
        email="test@example.com",
        hashed_password="hashed",
        stripe_customer_id="cus_test123"
    )
    db.add(user)
    db.commit()
    
    # Mock Stripe webhook verification
    with patch('stripe.Webhook.construct_event') as mock_webhook:
        mock_webhook.return_value = {
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "customer": "cus_test123",
                    "status": "active",
                    "items": {
                        "data": [{
                            "price": {"id": "price_pro"}
                        }]
                    },
                    "current_period_start": 1234567890,
                    "current_period_end": 1234567899,
                    "cancel_at_period_end": False
                }
            }
        }
        
        response = client.post(
            "/stripe/webhook",
            content=b"test payload",
            headers={"stripe-signature": "test_sig"}
        )
        
        assert response.status_code == 200
        
        # Verify subscription was created
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == "sub_test123"
        ).first()
        assert subscription is not None
        assert subscription.user_id == user.id
        assert subscription.status == "active"


def test_webhook_subscription_deleted(client, db):
    """Test webhook handling for subscription.deleted event"""
    # Create user and subscription
    user = User(
        email="test@example.com",
        hashed_password="hashed",
        stripe_customer_id="cus_test123"
    )
    db.add(user)
    db.commit()
    
    pro_plan = db.query(Plan).filter(Plan.name == "PRO").first()
    subscription = Subscription(
        user_id=user.id,
        plan_id=pro_plan.id,
        stripe_subscription_id="sub_test123",
        status="active"
    )
    db.add(subscription)
    db.commit()
    
    # Mock Stripe webhook verification
    with patch('stripe.Webhook.construct_event') as mock_webhook:
        mock_webhook.return_value = {
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "customer": "cus_test123",
                    "status": "canceled"
                }
            }
        }
        
        response = client.post(
            "/stripe/webhook",
            content=b"test payload",
            headers={"stripe-signature": "test_sig"}
        )
        
        assert response.status_code == 200
        
        # Verify subscription was canceled
        db.refresh(subscription)
        assert subscription.status == "canceled"
        
        # Verify free plan subscription was created
        free_subscription = db.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.status == "active"
        ).first()
        assert free_subscription is not None
        free_plan = db.query(Plan).filter(Plan.id == free_subscription.plan_id).first()
        assert free_plan.name == "FREE"


def test_webhook_invalid_signature(client):
    """Test webhook with invalid signature"""
    with patch('stripe.Webhook.construct_event') as mock_webhook:
        import stripe
        mock_webhook.side_effect = stripe.error.SignatureVerificationError(
            "Invalid signature", "sig_header"
        )
        
        response = client.post(
            "/stripe/webhook",
            content=b"test payload",
            headers={"stripe-signature": "invalid_sig"}
        )
        
        assert response.status_code == 400
        assert "signature" in response.json()["detail"].lower()
