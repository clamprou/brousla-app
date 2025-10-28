from fastapi import FastAPI, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import stripe
import json
from jose import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64

from app.database import get_db, engine, Base
from app.models import User, Device, Subscription, Plan, Entitlement, Usage
from app.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_license_token,
    get_current_user
)
from app.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    EntitlementsResponse,
    UsageReportRequest,
    UsageReportResponse,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    PortalSessionResponse,
    JWKResponse
)
from app.config import settings

# Initialize Stripe
stripe.api_key = settings.stripe_secret

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Brousla Cloud API", version="1.0.0")


@app.on_event("startup")
async def startup_event():
    """Initialize default plans on startup"""
    db = next(get_db())
    try:
        # Check if plans already exist
        existing_plans = db.query(Plan).count()
        if existing_plans == 0:
            # Seed default plans
            plans = [
                Plan(
                    name="FREE",
                    stripe_price_id=None,
                    limits_json={
                        "max_renders_per_day": 10,
                        "max_seats": 1,
                        "max_projects": 3,
                        "max_export_quality": "720p"
                    }
                ),
                Plan(
                    name="PRO",
                    stripe_price_id=settings.stripe_price_id_pro,
                    limits_json={
                        "max_renders_per_day": 100,
                        "max_seats": 1,
                        "max_projects": -1,  # unlimited
                        "max_export_quality": "4k"
                    }
                ),
                Plan(
                    name="TEAM",
                    stripe_price_id=settings.stripe_price_id_team,
                    limits_json={
                        "max_renders_per_day": 500,
                        "max_seats": 5,
                        "max_projects": -1,
                        "max_export_quality": "4k",
                        "team_collaboration": True
                    }
                )
            ]
            db.add_all(plans)
            db.commit()
            print("✓ Seeded default plans: FREE, PRO, TEAM")
    finally:
        db.close()


# Auth Endpoints

@app.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user and create a free plan subscription"""
    # Check if user exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = User(
        email=request.email,
        hashed_password=get_password_hash(request.pwd)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create free plan subscription
    free_plan = db.query(Plan).filter(Plan.name == "FREE").first()
    if free_plan:
        subscription = Subscription(
            user_id=user.id,
            plan_id=free_plan.id,
            status="active"
        )
        db.add(subscription)
        db.commit()
    
    # Generate access token
    access_token = create_access_token({"sub": str(user.id)})
    
    return TokenResponse(access_token=access_token)


@app.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login and receive access JWT"""
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.pwd, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=access_token)


# Device Management

@app.post("/devices/register", response_model=DeviceRegisterResponse)
async def register_device(
    request: DeviceRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register or update a device for the authenticated user"""
    device = db.query(Device).filter(Device.device_id == request.device_id).first()
    
    if device:
        # Update existing device
        device.app_version = request.app_version
        device.last_seen = datetime.utcnow()
        device.user_id = current_user.id  # Re-assign if needed
    else:
        # Create new device
        device = Device(
            device_id=request.device_id,
            user_id=current_user.id,
            app_version=request.app_version
        )
        db.add(device)
    
    db.commit()
    
    return DeviceRegisterResponse(
        device_id=request.device_id,
        message="Device registered successfully"
    )


# Entitlements

@app.get("/entitlements", response_model=EntitlementsResponse)
async def get_entitlements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get license JWT based on active subscription"""
    # Get active subscription
    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == current_user.id,
            Subscription.status == "active"
        )
        .order_by(Subscription.created_at.desc())
        .first()
    )
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    # Get plan details
    plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    # Count user devices for device_max
    device_count = db.query(Device).filter(Device.user_id == current_user.id).count()
    device_max = plan.limits_json.get("max_seats", 1) * 3  # Allow 3 devices per seat
    
    # Generate license JWT
    license_jwt = create_license_token(
        user_id=current_user.id,
        plan_name=plan.name,
        limits=plan.limits_json,
        device_max=device_max
    )
    
    # Store entitlement
    expires_at = datetime.utcnow() + timedelta(days=settings.jwt_license_token_expire_days)
    entitlement = Entitlement(
        user_id=current_user.id,
        subscription_id=subscription.id,
        license_jwt=license_jwt,
        expires_at=expires_at
    )
    db.add(entitlement)
    db.commit()
    
    return EntitlementsResponse(license_jwt=license_jwt)


# Public Key (JWKs)

@app.get("/pubkey", response_model=JWKResponse)
async def get_public_key():
    """Get public key in JWK format for RS256 verification"""
    try:
        # Load public key
        public_key = serialization.load_pem_public_key(
            settings.jwt_public_key_pem.encode(),
            backend=default_backend()
        )
        
        # Get public numbers
        public_numbers = public_key.public_numbers()
        
        # Convert to JWK format
        def int_to_base64(n):
            """Convert integer to base64url-encoded string"""
            byte_length = (n.bit_length() + 7) // 8
            n_bytes = n.to_bytes(byte_length, byteorder='big')
            return base64.urlsafe_b64encode(n_bytes).rstrip(b'=').decode('ascii')
        
        jwk = {
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "n": int_to_base64(public_numbers.n),
            "e": int_to_base64(public_numbers.e)
        }
        
        return JWKResponse(keys=[jwk])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating JWK: {str(e)}"
        )


# Stripe Webhooks

@app.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events"""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_wh_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle different event types
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await handle_checkout_completed(session, db)
    
    elif event["type"] == "customer.subscription.created":
        subscription_data = event["data"]["object"]
        await handle_subscription_created(subscription_data, db)
    
    elif event["type"] == "customer.subscription.updated":
        subscription_data = event["data"]["object"]
        await handle_subscription_updated(subscription_data, db)
    
    elif event["type"] == "customer.subscription.deleted":
        subscription_data = event["data"]["object"]
        await handle_subscription_deleted(subscription_data, db)
    
    return {"status": "success"}


async def handle_checkout_completed(session, db: Session):
    """Handle successful checkout"""
    customer_id = session.get("customer")
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    
    if user:
        # The subscription will be created by the subscription.created event
        pass


async def handle_subscription_created(subscription_data, db: Session):
    """Handle subscription creation"""
    customer_id = subscription_data["customer"]
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    
    if not user:
        return
    
    # Get plan from price ID
    price_id = subscription_data["items"]["data"][0]["price"]["id"]
    plan = db.query(Plan).filter(Plan.stripe_price_id == price_id).first()
    
    if not plan:
        return
    
    # Create or update subscription
    subscription = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        stripe_subscription_id=subscription_data["id"],
        status=subscription_data["status"],
        current_period_start=datetime.fromtimestamp(subscription_data["current_period_start"]),
        current_period_end=datetime.fromtimestamp(subscription_data["current_period_end"]),
        cancel_at_period_end=subscription_data["cancel_at_period_end"]
    )
    db.add(subscription)
    db.commit()


async def handle_subscription_updated(subscription_data, db: Session):
    """Handle subscription updates"""
    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription_data["id"]
    ).first()
    
    if subscription:
        subscription.status = subscription_data["status"]
        subscription.current_period_start = datetime.fromtimestamp(subscription_data["current_period_start"])
        subscription.current_period_end = datetime.fromtimestamp(subscription_data["current_period_end"])
        subscription.cancel_at_period_end = subscription_data["cancel_at_period_end"]
        subscription.updated_at = datetime.utcnow()
        db.commit()


async def handle_subscription_deleted(subscription_data, db: Session):
    """Handle subscription cancellation"""
    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription_data["id"]
    ).first()
    
    if subscription:
        subscription.status = "canceled"
        subscription.updated_at = datetime.utcnow()
        
        # Revert to free plan
        free_plan = db.query(Plan).filter(Plan.name == "FREE").first()
        if free_plan:
            new_subscription = Subscription(
                user_id=subscription.user_id,
                plan_id=free_plan.id,
                status="active"
            )
            db.add(new_subscription)
        
        db.commit()


# Billing

@app.post("/billing/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CheckoutSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Stripe checkout session for plan upgrade"""
    # Get plan
    plan = db.query(Plan).filter(Plan.name == request.plan.upper()).first()
    if not plan or not plan.stripe_price_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid plan"
        )
    
    # Create or get Stripe customer
    if not current_user.stripe_customer_id:
        customer = stripe.Customer.create(email=current_user.email)
        current_user.stripe_customer_id = customer.id
        db.commit()
    
    # Create checkout session
    session = stripe.checkout.Session.create(
        customer=current_user.stripe_customer_id,
        payment_method_types=["card"],
        line_items=[{
            "price": plan.stripe_price_id,
            "quantity": 1,
        }],
        mode="subscription",
        success_url=f"{settings.base_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.base_url}/billing/cancel",
    )
    
    return CheckoutSessionResponse(url=session.url)


@app.post("/billing/create-portal-session", response_model=PortalSessionResponse)
async def create_portal_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Stripe customer portal session"""
    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Stripe customer found"
        )
    
    session = stripe.billing_portal.Session.create(
        customer=current_user.stripe_customer_id,
        return_url=f"{settings.base_url}/account",
    )
    
    return PortalSessionResponse(url=session.url)


# Usage Reporting

@app.post("/usage/report", response_model=UsageReportResponse)
async def report_usage(
    request: UsageReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Report usage metrics (stub for metering)"""
    usage = Usage(
        user_id=current_user.id,
        type=request.type,
        quantity=request.qty
    )
    db.add(usage)
    db.commit()
    
    # Calculate today's total
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total_today = (
        db.query(Usage)
        .filter(
            Usage.user_id == current_user.id,
            Usage.type == request.type,
            Usage.reported_at >= today_start
        )
        .count()
    )
    
    return UsageReportResponse(
        message="Usage recorded",
        total_today=float(total_today)
    )


# Health Check

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
